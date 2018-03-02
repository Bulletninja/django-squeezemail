import json
import sys
import logging

import html2text
from django.utils.safestring import mark_safe



PY3 = sys.version_info > (3, 0)
import re
if PY3:
    from urllib.parse import urlparse, urlencode, urlunparse, parse_qsl
else:
    from urlparse import urlparse, urlunparse, parse_qsl
    from urllib import urlencode
from django.conf import settings

from django.template import Context, Template
from django.template.loader import render_to_string
from django.utils.functional import cached_property
from django.core.mail import EmailMultiAlternatives
from django.contrib.sites.models import Site
try:
    # Django >= 1.9
    from django.utils.module_loading import import_module
except ImportError:
    from django.utils.importlib import import_module
try:
    from django.core.urlresolvers import reverse
except ImportError:
    from django.urls import reverse

from content_editor.contents import contents_for_item
from . import SQUEEZE_CELERY_EMAIL_CHUNK_SIZE, SQUEEZE_DEFAULT_HTTP_PROTOCOL, SQUEEZE_DEFAULT_FROM_EMAIL
from .tasks import queue_email_messages_task
from .models import SentEmailMessage, Subscriber
from .utils import chunked
from .renderer import renderer


logger = logging.getLogger(__name__)

HREF_RE = re.compile(r'href\="((\{\{[^}]+\}\}|[^"><])+)"')


def configured_message_classes():
    conf_dict = getattr(settings, 'SQUEEZE_DRIP_MESSAGE_CLASSES', {})
    if 'default' not in conf_dict:
        conf_dict['default'] = 'squeezemail.handlers.RenderEmailMessage'
    return conf_dict


def message_class_for(name):
    path = configured_message_classes()[name]
    mod_name, klass_name = path.rsplit('.', 1)
    mod = import_module(mod_name)
    klass = getattr(mod, klass_name)
    return klass


class RenderEmailMessage(object):

    def __init__(self, email_message, subscriber):
        self.email_message = email_message
        self.subscriber = subscriber
        self._context = None
        self._subject = None
        self._body = None
        self._plain = None
        self._message = None
        self._token = None

    @cached_property
    def from_email(self):
        if self.email_message.from_email_name and self.email_message.from_email:
            from_ = "%s <%s>" % (self.email_message.from_email_name, self.email_message.from_email)
        elif self.email_message.from_email and not self.email_message.from_email_name:
            from_ = self.email_message.from_email
        else:
            from_ = SQUEEZE_DEFAULT_FROM_EMAIL
        return from_

    @property
    def from_email_name(self):
        return self.email_message.from_email_name

    def render_body(self):
        contents = contents_for_item(self.email_message, plugins=renderer.plugins())
        body = renderer.regions(self.email_message).render('body') #TODO: split test content here
        return body

    @property
    def context(self):
        if not self._context:
            token = self.get_email_token()
            context = Context({
                'subscriber': self.subscriber,
                'user': self.subscriber.user,
                'email_message': self.email_message,
                'token': token,
                'tracking_pixel': self.tracking_pixel,
                'unsubscribe_link': self.unsubscribe_link
                })
            context['content'] = mark_safe(self.replace_urls(Template(self.render_body()).render(context)))
            self._context = context
        return self._context

    @cached_property
    def subject_model(self):
        return self.email_message.choose_split_test_subject

    @property
    def subject(self):
        if not self._subject:
            self._subject = Template(self.subject_model.text).render(self.context)
        return self._subject

    @property
    def body(self):
        if not self._body:
            self._body = render_to_string('squeezemail/email/body.html', self.context)
        return self._body

    @property
    def plain(self):
        if not self._plain:
            h = html2text.HTML2Text()
            h.ignore_images = True
            self._plain = h.handle(render_to_string('squeezemail/email/plain.txt', self.context))
        return self._plain

    @property
    def message(self):
        if not self._message:
            self._message = EmailMultiAlternatives(self.subject, self.plain, self.from_email, [self.subscriber.email],
                headers={
                    "X-SMTPAPI": json.dumps({
                        "unique_args": {
                            "msg_pk": self.email_message.pk,
                            "sub_pk": self.subscriber.pk,
                        }
                    })
                })
            self._message.attach_alternative(self.body, 'text/html')
        return self._message

    def replace_urls(self, content):
        offset = 0
        for match in HREF_RE.finditer(content):
            link = match.group(1)
            replacelink = self.encode_url(link)
            content = ''.join((content[:match.start(1)+offset], replacelink, content[match.end(1)+offset:]))
            offset += len(replacelink) - len(match.group(1))
        return content

    def encode_url(self, raw_url):
        """
        Returns a replacement link

        Example of how this works:
        Here's an ordinary link in your email. There may be many of these in each email.
        original_url = http://anydomain.com/?just=athingwedontcareabout&but=letsmakeitinteresting

        Turns into:
        new_url = http://YOURDOMAIN.com/squeezemail/link/?sq_user_id=1&sq_drip_id=1&sq_user_token=123456789&just=athingwedontcareabout&but=letsmakeitinteresting&sq_target=http://somedomain.com

        When someone goes to the above new_url link, it'll hit our function at /link/ which re-creates the original url, but also passes subscriber_id, email_message_id, etc
        with it in case it's needed and redirects to the target url with the params. This is also where we throw some stats at Google Analytics.
        """
        site_domain = self.current_domain
        parsed_url = urlparse(raw_url)

        if parsed_url.netloc is '':
            # stick the scheme and netloc in the url if it's missing. This is so urls aren't just '/sublocation/'
            parsed_url = parsed_url._replace(scheme=SQUEEZE_DEFAULT_HTTP_PROTOCOL, netloc=site_domain)

        url_params = dict(parse_qsl(parsed_url.query))

        target_url = parsed_url._replace(query='')

        # where the user will be redirected to after clicking this link
        url_params['sq_target'] = urlunparse(target_url)

        # add subscriber_id, drip_id, token, subject_id to the params
        url_params.update(self.extra_url_params)

        parsed_url_list = list(parsed_url)
        parsed_url_list[4] = urlencode(url_params)

        new_url = urlparse('')._replace(
            scheme=SQUEEZE_DEFAULT_HTTP_PROTOCOL,
            netloc=site_domain,
            path=reverse('squeezemail:link'),
            query=parsed_url_list[4]
        )

        #rebuild new url
        new_url_with_extra_params = urlunparse(new_url)
        return new_url_with_extra_params

    @cached_property
    def extra_url_params(self):
        # These params will be inserted in every link in the content of the email.
        # Useful for tracking clicks and knowing who clicked it on which drip
        params = {
            'sq_subscriber_id': self.subscriber.id,
            'sq_email_message_id': self.email_message.id,
            'sq_token': self.get_email_token(),
            'sq_subject_id': self.subject_model.id
        }
        return params

    def get_email_token(self):
        if not self._token:
            self._token = str(self.subscriber.token)
        return self._token

    @cached_property
    def current_domain(self):
        return Site.objects.get_current().domain

    @cached_property
    def tracking_pixel(self):
        p = urlparse('')._replace(
            scheme=SQUEEZE_DEFAULT_HTTP_PROTOCOL,
            netloc=self.current_domain,
            path=reverse('squeezemail:tracking_pixel'),
            query=urlencode(self.extra_url_params)
        )
        return mark_safe(urlunparse(p))

    @cached_property
    def unsubscribe_link(self):
        url_params = {'sq_email': self.subscriber.email}
        url_params.update(self.extra_url_params)
        l = urlparse('')._replace(
            scheme=SQUEEZE_DEFAULT_HTTP_PROTOCOL,
            netloc=self.current_domain,
            path=reverse('squeezemail:unsubscribe'),
            query=urlencode(url_params)
        )
        return mark_safe(urlunparse(l))


class HandleEmailMessage(object):
    """
    A base object for defining a Drip.
    You can extend this manually and set it as your default drip
    handler class by setting SQUEEZE_DRIP_HANDLER in your settings.
    (e.g. SQUEEZE_DRIP_HANDLER = 'myapp.handlers.MyHandleDrip')
    """
    def __init__(self, *args, **kwargs):
        self.email_message_model = kwargs.get('email_message_model')
        self._queryset = kwargs.get('queryset', None)
        # self.step = kwargs.get('step', None)

    def get_queryset(self):
        if self._queryset is None:
            self._queryset = self.queryset()
        return self._queryset

    def queryset(self):
        """
        If there was no queryset passed in, our queryset is all active subscribers with our custom
        queryset rules applied to it (if the drip has any). This is used for broadcast drips.
        """
        # assert False, "drip handler is making a brand new queryset"
        base_qs = Subscriber.objects.filter(is_active=True)
        qs = self.email_message_model.apply_queryset_rules(base_qs).distinct()
        return qs

    def step_run(self, calling_step, subscription_qs):
        if subscription_qs.exists():  # let's avoid running on an empty queryset
            self.prune()
            # assert False, avoid_bug
            successfully_sent_subscriber_ids = self.send()
            # assert False, subscription_qs.filter(subscriber_id__in=successfully_sent_subscriber_ids)
            assert False, subscription_qs.filter(subscriber_id__in=successfully_sent_subscriber_ids)
            return subscription_qs.filter(subscriber_id__in=successfully_sent_subscriber_ids)
        else:
            return subscription_qs  # hand back the empty qs it passed in

    def broadcast_run(self):
        email_message = self.email_message_model
        if email_message.enabled:
            subscriber_id_list = self.prune().values_list('id', flat=True)
            if email_message.slice:
                subscriber_id_list = self.apply_slice(subscriber_list=subscriber_id_list, slice=email_message.slice)
            self.broadcast_send(email_message_id=email_message.id, subscriber_id_list=subscriber_id_list)
            return self.email_message_model.disable()
        return

    def prune(self):
        """
        Do an exclude for all Subscribers who have a SentEmailMessage already.
        """
        target_subscriber_ids = self.get_queryset().values_list('id', flat=True)
        exclude_subscriber_ids = SentEmailMessage.objects.filter(
            email_message_id=self.email_message_model.id,
            subscriber_id__in=target_subscriber_ids
        ).values_list('subscriber_id', flat=True)
        self._queryset = self.get_queryset().exclude(id__in=exclude_subscriber_ids).order_by(self.email_message_model.subscriber_order)
        return self._queryset

    def apply_slice(self, subscriber_list, slice):
        return subscriber_list[0:slice]

    def send(self):
        """
        Send the message to each subscriber on the queryset.
        Create SendDrip for each subscriber that gets a message.
        Returns count of created SendDrips.
        """
        MessageClass = message_class_for(self.email_message_model.message_class)
        successfully_sent_ids = []

        for subscriber in self.get_queryset():
            message_instance = MessageClass(self.email_message_model, subscriber)
            try:
                # Make sure they haven't received this drip just before sending.
                SentEmailMessage.objects.get(email_message_id=self.email_message_model.id, subscriber_id=subscriber.id)
                continue
            except SentEmailMessage.DoesNotExist:
                result = message_instance.message.send()
                if result:
                    SentEmailMessage.objects.create(email_message_id=self.email_message_model.id, subscriber_id=subscriber.id)
                    successfully_sent_ids.append(subscriber.id)
            except Exception as e:
                logging.error("Failed to send email message %s to subscriber %s: %s" % (str(self.email_message_model.id), str(subscriber.email), e))

        return successfully_sent_ids

    # def create_unsent_drips(self):
    #     """
    #     Create an unsent SendDrip objects for every subscriber_id in the queryset.
    #     Used for huge sendouts like broadcasts.
    #     """
    #     drip = self.drip_model
    #     subscriber_id_list = self.get_queryset().values_list('id', flat=True)
    #     # send_after = False
    #     # if drip.send_after:
    #     #     send_after = drip.send_after
    #
    #     for subscriber_id in subscriber_id_list:
    #         try:
    #             # if send_after:
    #             #     sentdrip = SendDrip.objects.create(drip_id=drip.id, subscriber_id=subscriber_id, date=send_after, sent=False)
    #             # else:
    #             sentdrip = SendDrip.objects.create(drip_id=drip.id, subscriber_id=subscriber_id, sent=False)
    #         except Exception as e:
    #             logger.warning("Failed to create SendDrip for subscriber_id %i & drip_id %i. (%r)", subscriber_id, drip.id, e)
    #     return

    # def create_tasks_for_broadcast(self, **kwargs):
    #     """
    #     Grab all of the SendDrips that haven't been sent yet, and queue up some celery tasks for them.
    #     A cron job would be running this every so often to create new celery tasks.
    #     """
    #     result_tasks = []
    #     kwargs['email_message_id'] = self.email_message_model.id
    #     now = timezone.now()
    #
    #     #lock it
    #
    #
    #     # Get a fresh list of all user IDs that haven't received this drip yet.
    #     subscriber_id_list = SentEmailMessage.objects.filter(email_message_id=self.email_message_model.id).values_list('subscriber_id', flat=True)
    #     chunk_size = SQUEEZE_CELERY_EMAIL_CHUNK_SIZE
    #     for chunk in chunked(subscriber_id_list, chunk_size):
    #         result_tasks.append(
    #             send_email_message.delay(chunk, **kwargs)
    #         )
    #     logging.info('broadcast chunk(s) queued')
    #     return result_tasks

    def broadcast_send(self, email_message_id, subscriber_id_list, *args, **kwargs):
        # result_tasks = []
        # kwargs['email_message_id'] = email_message_id

        chunk_size = SQUEEZE_CELERY_EMAIL_CHUNK_SIZE
        for chunk in chunked(subscriber_id_list, chunk_size):
            queue_email_messages_task.delay(email_message_id, chunk, *args, **kwargs)
        logging.info('Email message broadcast chunk(s) queued for sending')
        return
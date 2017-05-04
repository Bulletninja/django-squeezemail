from hashlib import md5

from celery import shared_task, task, Task
# from django.conf import settings
# from django.contrib.auth import get_user_model
# from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import get_connection
from django.core.cache import cache
from django.utils import dateparse
from django.db import IntegrityError
# from google_analytics_reporter.tracking import Event
# from django.utils import timezone
from squeezemail import SQUEEZE_BROADCAST_BACKEND_KWARGS
# from squeezemail import SQUEEZE_EMAIL_CONNECTION_TIMEOUT
from squeezemail import SQUEEZE_PREFIX, SQUEEZE_EMAIL_BACKEND, SQUEEZE_BROADCAST_EMAIL_RATE_LIMIT
from .models import SentEmailMessage, EmailMessage, Subscriber, Open, Click, Subject, Unsubscribe

from celery.utils.log import get_task_logger

# from celery import app
# from boto.ses.exceptions import SESAddressBlacklistedError, SESDomainEndsWithDotError, SESLocalAddressCharacterError, SESIllegalAddressError
# from django.core.mail import send_mail, EmailMessage
logger = get_task_logger(__name__)

LOCK_EXPIRE = (60 * 60) * 24  # Lock expires in 24 hours if it never gets unlocked


@task()
def run_steps():
    """
    Runs through all the active Steps, moving subscribers around, sending drips, tagging, etc.
    Recommended to have 1 worker on this for now until locking is working properly.
    """
    # for step in Step.objects.filter(is_active=True):
    #     step.run()
    return


class EmailConnectionTask(Task):
    """
    For persisting the email connection and setting the rate limit
    """
    _connection = None
    _timeout = None

    def __init__(self):
        super(EmailConnectionTask, self).__init__()
        self.rate_limit = SQUEEZE_BROADCAST_EMAIL_RATE_LIMIT
        self.backend_kwargs = SQUEEZE_BROADCAST_BACKEND_KWARGS or {}

    # def is_timed_out(self):
    #     if self._timeout is None:
    #         return True
    #     return timezone.now() > self._timeout

    @property
    def connection(self):
        # timed_out = self.is_timed_out()

        if self._connection is None:
            self._connection = get_connection(backend=SQUEEZE_EMAIL_BACKEND, **self.backend_kwargs)
            # self._timeout = timezone.now() + timezone.timedelta(minutes=SQUEEZE_EMAIL_CONNECTION_TIMEOUT)
        return self._connection


@task(base=EmailConnectionTask, ignore_result=True)
def send_email_message_task(email_message_id, subscriber_id, backend_kwargs=None):
    sent_email_exists = SentEmailMessage.objects.filter(subscriber_id=subscriber_id, email_message_id=email_message_id).exists()

    if not sent_email_exists:
        from squeezemail.handlers import message_class_for
        conn = send_email_message_task.connection

        try:
            email_message = EmailMessage.objects.get(id=email_message_id)
            MessageClass = message_class_for(email_message.message_class)

            subscriber = Subscriber.objects.get(pk=subscriber_id)
            message_instance = MessageClass(email_message, subscriber)
            sent = conn.send_messages([message_instance.message])
            if sent is not None:
                SentEmailMessage.objects.create(subscriber_id=subscriber_id, email_message_id=email_message_id)
                logger.info("Successfully sent email message to subscriber %i.", subscriber_id)
        except EmailMessage.DoesNotExist:
            logger.warning("EmailMessage %i doesn't exist" % email_message_id)
            return
        except Subscriber.DoesNotExist:
            logger.warning("Subscriber %i doesn't exist" % subscriber_id)
        except IntegrityError as e:  # Trouble creating the SentEmailMessage.
            logger.critical("Error trying to create SentEmailMessage %i for Subscriber %i. (%r)", email_message_id, subscriber_id, e)
        except Exception as e:
            logger.warning("Failed to send email message to %i. (%r)", subscriber_id, e)
            #send_email_message_task.retry([[message], combined_kwargs], exc=e, throw=False)
    return


@task(bind=True)
def queue_email_messages_task(self, email_message_id, subscriber_id_list, backend_kwargs=None, *args, **kwargs):
    """
    Used to send email messages to massive lists (100k+). Sending a broadcast uses this.
    """
    first_subscriber_id = subscriber_id_list[0]

    # The cache key consists of the squeeze_prefix (if it exists), drip id, first user id in the list and the MD5 digest.
    # This is to prevent a subscriber receiving 1 email multiple times if 2+ identical tasks are queued. The workers tend
    # to be so fast, that I've tested it without this and a subscriber was able to receive 1 email ~10 times when a bunch of
    # identical stale tasks were sitting in the queue waiting for celery to start.
    # Adding in the first_subscriber_id stops this from happening. Haven't figured out a better way yet.
    drip_id_hexdigest = md5(str(SQUEEZE_PREFIX).encode('utf-8') + str(email_message_id).encode('utf-8') + '_'.encode('utf-8') + str(first_subscriber_id).encode('utf-8')).hexdigest()
    # drip_id_hexdigest = md5(str(SQUEEZE_PREFIX).encode('utf-8') + str(drip_id).encode('utf-8')).hexdigest()
    lock_id = '{0}-lock-{1}'.format(self.name, drip_id_hexdigest)

    # cache.add fails if the key already exists
    acquire_lock = lambda: cache.add(lock_id, 'true', LOCK_EXPIRE)
    # memcache delete is very slow, but we have to use it to take
    # advantage of using add() for atomic locking
    release_lock = lambda: cache.delete(lock_id)

    logger.debug('Attempting to aquire lock for email_message_id %i', email_message_id)
    if acquire_lock():
        messages_sent = 0
        try:
            combined_kwargs = {}
            if backend_kwargs is not None:
                combined_kwargs.update(backend_kwargs)
            combined_kwargs.update(kwargs)

            for subscriber_id in subscriber_id_list:
                send_email_message_task.delay(email_message_id, subscriber_id)

        finally:
            release_lock()
            logger.info("EmailMessage %i chunk successfully queued: %i", email_message_id, messages_sent)
        return
    logger.info('EmailMessage %i is already being queued by another worker', email_message_id)
    return


# @task(bind=True)
# def send_email_message(self, email_message_id, subscriber_id_list, backend_kwargs=None, *args, **kwargs):
#     """
#     Used to send email messages to massive lists (100k+). Sending a broadcast uses this.
#     """
#     first_subscriber_id = subscriber_id_list[0]
#
#     # The cache key consists of the squeeze_prefix (if it exists), drip id, first user id in the list and the MD5 digest.
#     # This is to prevent a subscriber receiving 1 email multiple times if 2+ identical tasks are queued. The workers tend
#     # to be so fast, that I've tested it without this and a subscriber was able to receive 1 email ~10 times when a bunch of
#     # identical stale tasks were sitting in the queue waiting for celery to start.
#     # Adding in the first_subscriber_id stops this from happening. Haven't figured out a better way yet.
#     drip_id_hexdigest = md5(str(SQUEEZE_PREFIX).encode('utf-8') + str(email_message_id).encode('utf-8') + '_'.encode('utf-8') + str(first_subscriber_id).encode('utf-8')).hexdigest()
#     # drip_id_hexdigest = md5(str(SQUEEZE_PREFIX).encode('utf-8') + str(drip_id).encode('utf-8')).hexdigest()
#     lock_id = '{0}-lock-{1}'.format(self.name, drip_id_hexdigest)
#
#     # cache.add fails if the key already exists
#     acquire_lock = lambda: cache.add(lock_id, 'true', LOCK_EXPIRE)
#     # memcache delete is very slow, but we have to use it to take
#     # advantage of using add() for atomic locking
#     release_lock = lambda: cache.delete(lock_id)
#
#     logger.debug('Attempting to aquire lock for email_message_id %i', email_message_id)
#     if acquire_lock():
#         messages_sent = 0
#         try:
#             from squeezemail.handlers import message_class_for
#             # backward compat: handle **kwargs and missing backend_kwargs
#             combined_kwargs = {}
#             if backend_kwargs is not None:
#                 combined_kwargs.update(backend_kwargs)
#             combined_kwargs.update(kwargs)
#
#             try:
#                 email_message = EmailMessage.objects.get(id=email_message_id)
#                 MessageClass = message_class_for(email_message.message_class)
#             except EmailMessage.DoesNotExist:
#                 logger.warning("EmailMessage %i doesn't exist" % email_message_id)
#                 return
#
#             conn = get_connection(backend=settings.EMAIL_BACKEND, **combined_kwargs)
#             try:
#                 conn.open()
#             except Exception as e:
#                 logger.exception("Cannot reach EMAIL_BACKEND %s. (%r)", settings.EMAIL_BACKEND, e)
#
#             for subscriber in Subscriber.objects.filter(pk__in=subscriber_id_list):
#                 sent_email_exists = SentEmailMessage.objects.filter(subscriber_id=subscriber.pk, email_message_id=email_message_id).exists()
#
#                 try:
#                     if not sent_email_exists:
#                         message_instance = MessageClass(email_message, subscriber)
#                         sent = conn.send_messages([message_instance.message])
#
#                         if sent is not None:
#                             SentEmailMessage.objects.create(subscriber_id=subscriber.pk, email_message_id=email_message_id)
#                             messages_sent += 1
#                             logger.debug("Successfully sent email message to subscriber %i.", subscriber.pk)
#                             # Move subscriber to next step only after their drip has been sent
#                             # subscriber.move_to_step(next_step_id)
#                             # process_sent.delay(
#                             #     user_id=subscriber.id,
#                             #     subject=message_instance.subject,
#                             #     drip_id=drip_id,
#                             #     drip_name=drip.name,
#                             #     source='broadcast',
#                             #     split='main'
#                             # )
#                 except SentEmailMessage.IntegrityError as e:  # Trouble creating the SentEmailMessage.
#                     logger.critical("Error trying to create SentEmailMessage %i for Subscriber %i. (%r)", email_message_id, subscriber.pk, e)
#                     continue
#                 except Exception as e:
#                     logger.warning("Failed to send email message to %i. (%r)", subscriber.pk, e)
#                     #send_drip.retry([[message], combined_kwargs], exc=e, throw=False)
#                     continue
#             conn.close()
#         finally:
#             release_lock()
#             logger.info("EmailMessage %i chunk successfully sent: %i", email_message_id, messages_sent)
#         return
#     logger.info('EmailMessage %i is already being sent by another worker', email_message_id)
#     return


# @task(bind=True)
# def send_email_message(self, email_message_id, subscriber_id_list, backend_kwargs=None, *args, **kwargs):
#     """
#     Used to send email messages to massive lists (100k+). Sending a broadcast uses this.
#     """
#     first_subscriber_id = subscriber_id_list[0]
#
#     # The cache key consists of the squeeze_prefix (if it exists), drip id, first user id in the list and the MD5 digest.
#     # This is to prevent a subscriber receiving 1 email multiple times if 2+ identical tasks are queued. The workers tend
#     # to be so fast, that I've tested it without this and a subscriber was able to receive 1 email ~10 times when a bunch of
#     # identical stale tasks were sitting in the queue waiting for celery to start.
#     # Adding in the first_subscriber_id stops this from happening. Haven't figured out a better way yet.
#     drip_id_hexdigest = md5(str(SQUEEZE_PREFIX).encode('utf-8') + str(email_message_id).encode('utf-8') + '_'.encode('utf-8') + str(first_subscriber_id).encode('utf-8')).hexdigest()
#     # drip_id_hexdigest = md5(str(SQUEEZE_PREFIX).encode('utf-8') + str(drip_id).encode('utf-8')).hexdigest()
#     lock_id = '{0}-lock-{1}'.format(self.name, drip_id_hexdigest)
#
#     # cache.add fails if the key already exists
#     acquire_lock = lambda: cache.add(lock_id, 'true', LOCK_EXPIRE)
#     # memcache delete is very slow, but we have to use it to take
#     # advantage of using add() for atomic locking
#     release_lock = lambda: cache.delete(lock_id)
#
#     logger.debug('Attempting to aquire lock for email_message_id %i', email_message_id)
#     if acquire_lock():
#         messages_sent = 0
#         try:
#             from squeezemail.handlers import message_class_for
#             # backward compat: handle **kwargs and missing backend_kwargs
#             combined_kwargs = {}
#             if backend_kwargs is not None:
#                 combined_kwargs.update(backend_kwargs)
#             combined_kwargs.update(kwargs)
#
#             try:
#                 email_message = EmailMessage.objects.get(id=email_message_id)
#                 MessageClass = message_class_for(email_message.message_class)
#             except EmailMessage.DoesNotExist:
#                 logger.warning("EmailMessage %i doesn't exist" % email_message_id)
#                 return
#
#             conn = get_connection(backend=settings.EMAIL_BACKEND, **combined_kwargs)
#             try:
#                 conn.open()
#             except Exception as e:
#                 logger.exception("Cannot reach EMAIL_BACKEND %s. (%r)", settings.EMAIL_BACKEND, e)
#
#             for subscriber_id in subscriber_id_list:
#                 try:
#                     sent_email_message = SentEmailMessage.objects.get(subscriber_id=subscriber_id, email_message_id=email_message_id)
#
#                     try:
#                         if sent_email_message.sent is False:
#                             subscriber = Subscriber.objects.get(id=subscriber_id)
#
#                             message_instance = MessageClass(email_message, subscriber)
#
#                             sent = conn.send_messages([message_instance.message])
#                             if sent is not None:
#                                 sent_email_message.date = timezone.now()
#                                 sent_email_message.save()
#                                 messages_sent += 1
#                                 logger.debug("Successfully sent email message to subscriber %i.", subscriber.pk)
#                                 # Move subscriber to next step only after their drip has been sent
#                                 # subscriber.move_to_step(next_step_id)
#                                 # process_sent.delay(
#                                 #     user_id=subscriber.id,
#                                 #     subject=message_instance.subject,
#                                 #     drip_id=drip_id,
#                                 #     drip_name=drip.name,
#                                 #     source='broadcast',
#                                 #     split='main'
#                                 # )
#                     except ObjectDoesNotExist as e: #user doesn't exist
#                         logger.warning("Subscriber_id %i does not exist. (%r)", subscriber_id, e)
#                         continue
#                     except Exception as e:
#                         logger.warning("Failed to send email message to %i. (%r)", subscriber_id, e)
#                         #send_drip.retry([[message], combined_kwargs], exc=e, throw=False)
#                         continue
#                 except SentEmailMessage.MultipleObjectsReturned:
#                     logger.warning("Multiple SendDrips returned for subscriber_id: %i, drip_id: %i", subscriber_id, email_message_id)
#                     continue
#                 except SentEmailMessage.DoesNotExist:
#                     # a senddrip doesn't exist, shouldn't happen, but if it does, skip it
#                     logger.warning("Can't find a SendDrip object for subscriber_id: %i, drip_id: %i", subscriber_id, email_message_id)
#                     continue
#             conn.close()
#         finally:
#             release_lock()
#             logger.info("Drip_id %i chunk successfully sent: %i", email_message_id, messages_sent)
#         return
#     logger.info('Drip_id %i is already being sent by another worker', email_message_id)
#     return


@shared_task()
def process_sent(**kwargs):
    user_id = kwargs.get('user_id', None)
    subject = kwargs.get('subject', None)
    email_message_id = kwargs.get('sq_email_message_id', None)
    email_message_name = kwargs.get('email_message_name', None)
    source = kwargs.get('source', None)
    split = kwargs.get('split', None)
    # Event(user_id=user_id)\
    #     .send(
    #     category='email',
    #     action='sent',
    #     document_path='/email/',
    #     document_title=subject,
    #     campaign_id=email_message_id,
    #     campaign_name=email_message_name,
    #     campaign_source=source, #broadcast or step?
    #     campaign_medium='email',
    #     campaign_content=split  # body split test
    # )
    return


@shared_task()
def process_open(**kwargs):
    url_kwargs = kwargs

    token = url_kwargs.get('sq_token', None)
    timestamp = url_kwargs.get('sq_timestamp', None)
    subscriber_id = url_kwargs.get('sq_subscriber_id', None)
    email_message_id = url_kwargs.get('sq_email_message_id', None)
    ga_cid = url_kwargs.get('sq_cid', None)

    subject_id = url_kwargs.get('sq_subject_id', None)
    split = url_kwargs.get('sq_split', None)

    if token:  # if we don't get a token, we don't consider lifting a finger
        subscriber = Subscriber.objects.get(pk=subscriber_id)
        token_matched = subscriber.match_token(token)

        if token_matched:  # if token matched, we're allowed to do database writing
            logger.debug("Successfully matched token to user %r.", subscriber.email)
            sent_email_message = SentEmailMessage.objects.get(email_message_id=email_message_id, subscriber_id=subscriber_id)
            if not sent_email_message.opened:
                Open.objects.create(sent_email_message=sent_email_message, date=dateparse.parse_datetime(timestamp))
                logger.debug("SendDrip.open created")

                subject = Subject.objects.get(id=subject_id).text

                # utm_source=drip
                # utm_campaign=sentdrip.drip.name
                # utm_medium=email
                # utm_content=split ('A' or 'B')
                # target=target # don't need this for opens, but could be useful in clicks
                # event = 'open'?
                # Event(user_id=subscriber.id, client_id=ga_cid)\
                #     .sync_send(
                #     category='email',
                #     action='open',
                #     document_path='/email/',
                #     document_title=subject,
                #     campaign_id=email_message_id,
                #     campaign_name=sent_email_message.email_message.name,
                #     # campaign_source='', #broadcast or step?
                #     campaign_medium='email',
                #     campaign_content=split  # body split test
                # )
        else:
            logger.info("subscriber token didn't match")

    logger.debug("Email open processed for email message %r and subscriber %r", email_message_id, subscriber_id)
    return


@shared_task()
def process_click(**kwargs):
    url_kwargs = kwargs

    token = url_kwargs.get('sq_token', None)
    subscriber_id = url_kwargs.get('sq_subscriber_id', None)
    email_message_id = url_kwargs.get('sq_email_message_id', None)
    ga_cid = url_kwargs.get('sq_cid', None)

    subject_id = url_kwargs.get('sq_subject_id', None)
    split = url_kwargs.get('sq_split', None)
    tag_id = url_kwargs.get('sq_tag_id', None)

    if token:  # if a user token is passed in and matched, we're allowed to do database writing
        subscriber = Subscriber.objects.get(pk=subscriber_id)
        token_matched = subscriber.match_token(token)

        if token_matched:
            logger.debug("Successfully matched token to user %r.", subscriber.email)
            sent_email_message = SentEmailMessage.objects.get(email_message_id=email_message_id, subscriber_id=subscriber_id)
            subject = Subject.objects.get(id=subject_id).text
            if not sent_email_message.opened:
                # If there isn't an open, but it was clicked, we make an open.
                Open.objects.create(sent_email_message=sent_email_message)
                logger.debug("SendDrip.open created")
                # target=target # don't need this for opens, but could be useful in clicks
                # Event(user_id=subscriber.id, client_id=ga_cid)\
                #     .sync_send(
                #     category='email',
                #     action='open',
                #     document_path='/email/',
                #     document_title=subject,
                #     campaign_id=email_message_id,
                #     campaign_name=sent_email_message.email_message.name,
                #     # campaign_source='', #broadcast or step?
                #     campaign_medium='email',
                #     campaign_content=split  # body split test
                # )

            if not sent_email_message.clicked:
                Click.objects.create(sent_email_message=sent_email_message)
                logger.debug('Click created')
                # Event(user_id=subscriber.id, client_id=ga_cid)\
                #     .sync_send(
                #     category='email',
                #     action='click',
                #     document_path='/email/',
                #     document_title=subject,
                #     campaign_id=email_message_id,
                #     campaign_name=sent_email_message.email_message.name,
                #     # campaign_source='', #broadcast or step?
                #     campaign_medium='email',
                #     campaign_content=split  # body split test
                # )

            if tag_id:
                #TODO: tag 'em
                pass

        else:
            logger.info("user link didn't match token")

    logger.info("Email click processed")
    return


@shared_task()
def process_unsubscribe(**kwargs):
    url_kwargs = kwargs

    token = url_kwargs.get('sq_token', None)
    subscriber_id = url_kwargs.get('sq_subscriber_id', None)
    email_message_id = url_kwargs.get('sq_email_message_id', None)
    ga_cid = url_kwargs.get('sq_cid', None)

    subject_id = url_kwargs.get('sq_subject_id', None)
    split = url_kwargs.get('sq_split', None)
    tag_id = url_kwargs.get('sq_tag_id', None)

    if token:  # if a user token is passed in and matched, we're allowed to do database writing
        subscriber = Subscriber.objects.get(pk=subscriber_id)
        token_matched = subscriber.match_token(token)

        if token_matched:
            logger.debug("Successfully matched token to user %r.", subscriber.email)
            sent_email_message = SentEmailMessage.objects.get(email_message_id=email_message_id, subscriber_id=subscriber_id)
            subject = Subject.objects.get(id=subject_id).text
            if not sent_email_message.unsubscribed:
                Unsubscribe.objects.create(sent_email_message=sent_email_message)
                logger.debug("SendDrip.unsubscribed created")
                # target=target # don't need this for opens, but could be useful in clicks
                # Event(user_id=subscriber.id, client_id=ga_cid)\
                #     .sync_send(
                #     category='email',
                #     action='unsubscribe',
                #     document_path='/email/',
                #     document_title=subject,
                #     campaign_id=email_message_id,
                #     campaign_name=sent_email_message.email_message.name,
                #     # campaign_source='', #broadcast or step?
                #     campaign_medium='email',
                #     campaign_content=split  # body split test
                # )
        else:
            logger.info("user link didn't match token")
    return

import functools
import operator
import logging

# from content_editor.contents import contents_for_item#, contents_for_items
# from content_editor.renderer import PluginRenderer


try:
    from _md5 import md5  # Python 3
except ImportError:
    from hashlib import md5  # Python 2

from django.db.models import Q
# from gfklookupwidget.fields import GfkLookupField
# from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
# from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from django.db import models
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.conf import settings
from django.utils.functional import cached_property
from django.core.cache import cache
from django.utils import timezone
# from django.contrib.postgres.fields import JSONField
# just using this to parse, but totally insane package naming...
# https://bitbucket.org/schinckel/django-timedelta-field/
import timedelta as djangotimedelta
# from mptt.models import MPTTModel, TreeForeignKey


from squeezemail import SQUEEZE_EMAILMESSAGE_HANDLER
from squeezemail import SQUEEZE_PREFIX
# from squeezemail import SQUEEZE_SUBSCRIBER_MANAGER
from squeezemail import plugins
from squeezemail.utils import class_for, get_token_for_email

from content_editor.models import (
    Region, create_plugin_base
)

logger = logging.getLogger(__name__)

LOCK_EXPIRE = (60 * 60) * 24

STATUS_CHOICES = (
    ('draft', 'Draft'),
    ('paused', 'Paused'),
    ('active', 'Active'),
)

METHOD_TYPES = (
    ('filter', 'Filter'),
    ('exclude', 'Exclude'),
)

LOOKUP_TYPES = (
    ('exact', 'exactly'),
    ('iexact', 'exactly (case insensitive)'),
    ('contains', 'contains'),
    ('icontains', 'contains (case insensitive)'),
    ('regex', 'regex'),
    ('iregex', 'regex (case insensitive)'),
    ('gt', 'greater than'),
    ('gte', 'greater than or equal to'),
    ('lt', 'less than'),
    ('lte', 'less than or equal to'),
    ('startswith', 'starts with'),
    ('endswith', 'ends with'),
    ('istartswith', 'starts with (case insensitive)'),
    ('iendswith', 'ends with (case insensitive)'),
    ('isnull', 'isnull (boolean)'),
)

#
# class Funnel(models.Model):
#     name = models.CharField(max_length=75)
#     entry_step = models.ForeignKey('squeezemail.Step', related_name='funnels')
#     subscribers = models.ManyToManyField('squeezemail.Subscriber', through='Subscription', related_name='funnels')
#
#     def __str__(self):
#         return self.name
#
#     def create_subscription(self, subscriber, ignore_previous_history=False, *args, **kwargs):
#         """
#         Add/create a subscriber to go down this funnel path.
#         Won't go down the path if the subscriber has already been on it unless ignore_previous_history is True.
#         If the subscriber has already been down the path and you do force them down it again, they won't receive the
#         same drips unless you clear their senddrip history. They will continue to move down it, though, even without
#         drips being sent to them.
#         """
#         created = False
#         if isinstance(subscriber, Subscriber):
#             subscription, created = self.subscriptions.get_or_create(subscriber=subscriber)
#         else:
#             # Assume an email as a string has been passed in
#             subscriber = Subscriber.objects.get_or_add(email=subscriber)
#             subscription, created = self.subscriptions.get_or_create(subscriber=subscriber)
#         if created or ignore_previous_history:
#             subscription.move_to_step(self.entry_step_id)
#         return subscription
#
#     def get_subscription_count(self):
#         return self.subscriptions.count()
#
#     def step_add(self, subscriber):
#         return self.create_subscription(subscriber=subscriber)
#
#     get_subscription_count.short_description = "Subscriptions"


# step_choices = models.Q(app_label='squeezemail', model='decision') |\
#         models.Q(app_label='squeezemail', model='delay') |\
#         models.Q(app_label='squeezemail', model='drip') |\
#         models.Q(app_label='squeezemail', model='modify') |\
#         models.Q(app_label='squeezemail', model='emailactivity')

PRIORITY_CHOICES = (
    (0, 'No Priority'),
    (1, '[1] Priority'),
    (2, '[2] Priority'),
    (3, '[3] Priority'),
    (4, '[4] Priority'),
    (5, '[5] Priority'),
)

#
# class Step(MPTTModel):
#     funnel = models.ForeignKey('squeezemail.Funnel', related_name='steps')
#     parent = TreeForeignKey('self', null=True, blank=True, related_name='children', db_index=True)
#     description = models.CharField(max_length=75, null=True, blank=True)
#     is_active = models.BooleanField(verbose_name="Active", default=True, help_text="If not active, subscribers will still be allowed to move to this step, but this step won't run until it's active. Consider this a good way to 'hold' subscribers on this step. Note: Step children will still run.")
#     delay = models.DurationField(default=timezone.timedelta(days=1), help_text="How long should the subscriber sit on this step before it runs for them? The preferred format for durations in Django is '%d %H:%M:%S.%f (e.g. 3 00:40:00 for 3 day, 40 minute delay)'")
#     # resume_on_days = models.IntegerField(max_length=7, default=1111111) TODO: add ability to only run on specific days of the week
#     priority = models.IntegerField(default=0, choices=PRIORITY_CHOICES, help_text="To help avoid sending multiple emails to the same subscriber. Higher priority will run first.")
#     passed = models.ForeignKey('squeezemail.Step', null=True, blank=True, related_name='passed+', help_text="If the subscriber passes through <b>all</b> of the actions, you can optionally direct them to a specific step. This is useful if using a 'Queryset Rule' or 'Email Activity' action and you want to send any filtered/true users to a specific step. If nothing is specified here, any truthy subscribers will just move to this step's first child (if relevant).")
#     failed = models.ForeignKey('squeezemail.Step', null=True, blank=True, related_name='failed+', help_text="Useful if you use any type of action that removes subscribers from the original queryset (e.g. a 'Queryset Rule'). If nothing is specified here, any excluded subscribers will just move to this step's first child (if relevant).")
#     processed = models.IntegerField(default=0)
#     subscribers = models.ManyToManyField('squeezemail.Subscriber', through='Subscription', related_name='current_steps')
#
#     regions = [
#         Region(key='operators', title='Operators'),
#     ]
#
#     def __init__(self, *args, **kwargs):
#         super(Step, self).__init__(*args, **kwargs)
#         self.starting_subscriptions = None
#         self.passing_subscriptions = None
#         self.count = 0
#
#     def __str__(self):
#         if self.description:
#             return "%s - (delay for %s)" % (self.description, self.delay)
#         # contents = contents_for_items(self, plugins=[DripOperator])
#         return "%s - (delay for %s)" % (str(self.pk), self.delay)
#
#     def get_subscriptions(self):
#         if self.passing_subscriptions is not None:
#             return self.passing_subscriptions
#         else:
#             # get all subscribers currently on this step who are active
#             # and have been sitting on this step longer than the step duration
#             self.count += 1
#             print("getting subscriptions: %i" % self.count)
#             now = timezone.now()
#             goal_time = now - self.delay
#
#             qs = self.subscriptions.filter(is_active=True, subscriber__is_active=True, step_timestamp__lte=goal_time)
#
#             # if they already received an email today, let's make them sit here and try again next time
#             over_emailed_subscriber_ids = SendDrip.objects.filter(
#                 subscriber_id__in=qs.values_list('subscriber_id', flat=True),
#                 date__day=now.today().day).values_list('subscriber_id', flat=True)
#
#             qs = qs.exclude(subscriber_id__in=over_emailed_subscriber_ids)
#
#             self.starting_subscriptions = qs  # the original subscribers before the operator(s) began
#             self.passing_subscriptions = qs  # we'll be possibly plucking subscribers out of this qs as the operators go
#             return qs
#
#     @cached_property
#     def lock_id(self):
#         hexdigest = md5(str(SQUEEZE_PREFIX).encode('utf-8') +
#                 str('step_').encode('utf-8') +
#                 str(self.id).encode('utf-8') +
#                 '_'.encode('utf-8')).hexdigest()
#         return '{0}-lock-{1}'.format('step', hexdigest)
#
#     def acquire_lock(self):
#         return cache.add(self.lock_id, 'true', LOCK_EXPIRE)
#
#     def release_lock(self):
#         return cache.delete(self.lock_id)
#
#     def run(self):
#         # if self.acquire_lock():  # lock this step so it can't run while one is already running
#             # do what this step needs to do to the subscribers (tag, send a drip, etc.)
#             count = 0
#             if self.get_subscriptions().exists():
#                 action_list = contents_for_item(self, plugins=[DripOperator, ModificationOperator, QuerySetRule])
#                 for action in action_list:
#                     if self.get_subscriptions().exists():  # so we don't continue running actions on an empty qs
#                         print("running action %s" % str(action))
#                         current_qs = self.get_subscriptions()
#                         # runs actions, in order, on subscriber queryset. Possibly removing subscriptions for relevant actions.
#                         self.passing_subscriptions = action.step_run(self, current_qs)
#                         print(self.passing_subscriptions)
#
#                 true_ids = self.passing_subscriptions.values_list('id', flat=True)
#                 qs_false = self.starting_subscriptions.exclude(id__in=true_ids)
#
#                 next_step = self.get_next_step()
#                 if self.passed_id:
#                     for subscription in self.passing_subscriptions:
#                         subscription.move_to_step(self.passed_id)
#                         count += 1
#                 else:  # If there's no specified step to move to on true, move to the next step if there is one
#                     if next_step:
#                         for subscription in self.passing_subscriptions:
#                             subscription.move_to_step(next_step.id)
#                             count += 1
#
#                 if self.failed_id:
#                     for subscription in qs_false:
#                         subscription.move_to_step(self.failed_id)
#                         count += 1
#                 else:  # If there's no specified step to move to on false, move to the next step if there is one
#                     if next_step:
#                         for subscription in qs_false:
#                             subscription.move_to_step(next_step.id)
#                             count += 1
#                 if count > 0:
#                     self.processed += count
#                     self.save()
#             # self.release_lock()
#
#             return count
#         # else:
#         #     logger.warn('Step %i is already running', self.id)
#
#     def get_next_step(self):
#         next_step_exists = self.get_children().exists()
#         return self.get_children()[0] if next_step_exists else None  # Only get 1 child.
#
#     def get_active_subscription_count(self):
#         return self.subscriptions.filter(is_active=True).count()
#
#     get_active_subscription_count.short_description = "On Step"
#
#     #for modification method
#     def step_move(self, subscription):
#         return subscription.move_to_step(self.id)
#
#     # def apply_queryset_rules(self, qs):
#     #     """
#     #     First collect all filter/exclude kwargs and apply any annotations.
#     #     Then apply all filters at once, and all excludes at once.
#     #     """
#     #     clauses = {
#     #         'filter': [],
#     #         'exclude': []}
#     #
#     #     for rule in self.queryset_rules.all():
#     #
#     #         clause = clauses.get(rule.method_type, clauses['filter'])
#     #
#     #         kwargs = rule.filter_kwargs(qs)
#     #         clause.append(Q(**kwargs))
#     #
#     #         qs = rule.apply_any_annotation(qs)
#     #
#     #     if clauses['exclude']:
#     #         qs = qs.exclude(functools.reduce(operator.or_, clauses['exclude']))
#     #     qs = qs.filter(*clauses['filter'])
#     #     return qs
#
#
# StepPlugin = create_plugin_base(Step)


class Tag(models.Model):
    """
    Can Add/Remove a subscriber tag with a Modification action.
    Filter/Exclude off of a tag with a Queryset Rule.
    """
    name = models.CharField(unique=True, max_length=100)
    slug = models.SlugField(unique=True, max_length=100)

    def step_add(self, calling_step, subscription):
        return self.subscribers.add(subscription.subscriber_id)

    def step_remove(self, calling_step, subscription):
        return self.subscribers.remove(subscription.subscriber_id)

    def __str__(self):
        return self.name

#
# class Decision(models.Model):
#     description = models.CharField(max_length=75, null=True, blank=True)
#     on_true = models.ForeignKey('squeezemail.Step', null=True, blank=True, related_name='step_decision_on_true+')
#     on_false = models.ForeignKey('squeezemail.Step', null=True, blank=True, related_name='step_decision_on_false+')
#
#     queryset_rules = GenericRelation(
#         'squeezemail.QuerySetRule',
#         content_type_field='content_type_id',
#         object_id_field='object_id',
#     )
#
#     def __str__(self):
#         return "Decision: %s" % self.description
#
#     def apply_queryset_rules(self, qs):
#         """
#         First collect all filter/exclude kwargs and apply any annotations.
#         Then apply all filters at once, and all excludes at once.
#         """
#         clauses = {
#             'filter': [],
#             'exclude': []}
#
#         for rule in self.queryset_rules.all():
#
#             clause = clauses.get(rule.method_type, clauses['filter'])
#
#             kwargs = rule.filter_kwargs(qs)
#             clause.append(Q(**kwargs))
#
#             qs = rule.apply_any_annotation(qs)
#
#         if clauses['exclude']:
#             qs = qs.exclude(functools.reduce(operator.or_, clauses['exclude']))
#         qs = qs.filter(*clauses['filter'])
#         return qs
#
#     def step_run(self, calling_step, subscriber_qs):
#
#         qs_true = self.apply_queryset_rules(subscriber_qs).distinct()
#
#         true_ids = qs_true.values_list('id', flat=True)
#         qs_false = subscriber_qs.exclude(id__in=true_ids)
#         if self.on_true_id:
#             for subscriber in qs_true:
#                 subscriber.move_to_step(self.on_true_id)
#
#         if self.on_false_id:
#             for subscriber in qs_false:
#                 subscriber.move_to_step(self.on_false_id)
#         return subscriber_qs


class Subject(models.Model):
    email_message = models.ForeignKey('squeezemail.EmailMessage', related_name='subjects')
    text = models.CharField(max_length=150)
    enabled = models.BooleanField(default=True)

    def __str__(self):
        return self.text


class EmailMessage(models.Model):
    ORDER_CHOICES = (
        ('created', 'Oldest first'),
        ('-created', 'Newest first'),
        ('?', 'Random')
    )

    regions = [
        Region(key='body', title='Main Body'),
        # Region(key='split_test', title='Split Test Body',
        #        inherited=False),
    ]
    name = models.CharField(
        max_length=255,
        unique=True,
        verbose_name='Email Message Name',
        help_text='A unique name for this email message.')

    enabled = models.BooleanField(default=False)

    note = models.TextField(max_length=255, null=True, blank=True, help_text="This is only seen by staff.")

    from_email = models.EmailField(null=True, blank=True, help_text='Set a custom from email.')
    from_email_name = models.CharField(max_length=150, null=True, blank=True, help_text="Set a name for a custom from email.")
    message_class = models.CharField(max_length=120, blank=True, default='default')
    slice = models.IntegerField(null=True, blank=True, help_text='Send to only a specific amount of subscribers. Useful for testing to a portion of the list. A value of 1000 would send to 1000 subscribers each time this EmailMessage is sent out.')
    subscriber_order = models.CharField(max_length=25, choices=ORDER_CHOICES, default='created', help_text='Send out to subscribers in this order.')
    send_after = models.DateTimeField(blank=True, null=True)
    disable_after_broadcast = models.BooleanField(default=False, help_text="Useful with 'send after' broadcasts. After broadcast is initiated, disable this drip so it won't try to go out again.")
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def handler(self, *args, **kwargs):
        kwargs['email_message_model'] = self
        handler_class = class_for(SQUEEZE_EMAILMESSAGE_HANDLER)
        handler = handler_class(*args, **kwargs)
        return handler

    def __str__(self):
        return self.name

    @cached_property
    def lock_id(self):
        # example lock id: prefix_email_message_1
        return str(SQUEEZE_PREFIX).encode('utf-8') + 'email_message_'.encode('utf-8') + str(self.id).encode('utf-8')

    def acquire_lock(self):
        return cache.add(self.lock_id, 'true', LOCK_EXPIRE)

    def release_lock(self):
        return cache.delete(self.lock_id)

    @cached_property
    def subject(self):
        return self.choose_split_test_subject.text

    @cached_property
    def get_split_test_subjects(self):
        return self.subjects.filter(enabled=True)

    @cached_property
    def split_subject_active(self):
        return self.get_split_test_subjects.count() > 1

    @cached_property
    def choose_split_test_subject(self):
        # Return a subject object to be able to get the subject text and the subject id
        random_subject = self.subjects.filter(enabled=True).order_by('?')[0]
        return random_subject

    def get_split_test_body(self):
        pass

    def step_run(self, calling_step, subscription_qs):
        subscriber_qs = Subscriber.objects.filter(id__in=subscription_qs.values_list('subscriber_id', flat=True))

        successfully_sent_subscriber_qs = self.handler(step=calling_step, queryset=subscriber_qs).step_run(calling_step, subscription_qs)
        # assert False, successfully_sent_subscriber_qs
        return successfully_sent_subscriber_qs

    def apply_queryset_rules(self, qs):
        """
        First collect all filter/exclude kwargs and apply any annotations.
        Then apply all filters at once, and all excludes at once.
        """
        clauses = {
            'filter': [],
            'exclude': []}

        for rule in self.queryset_rules.all():

            clause = clauses.get(rule.method_type, clauses['filter'])

            kwargs = rule.filter_kwargs(qs)
            clause.append(Q(**kwargs))

            qs = rule.apply_any_annotation(qs)

        if clauses['exclude']:
            qs = qs.exclude(functools.reduce(operator.or_, clauses['exclude']))
        qs = qs.filter(*clauses['filter'])
        return qs

    def total_sent(self):
        return self.sent_email_messages.all().count()

    def open_rate(self):
        total_sent = self.total_sent()
        total_opened = Open.objects.filter(sent_email_message__email_message_id=self.pk).count()
        if total_sent > 0 and total_opened > 0:
            return (total_opened / total_sent) * 100
        return 0

    def click_through_rate(self):
        total_sent = self.total_sent()
        total_clicked = Click.objects.filter(sent_email_message__email_message_id=self.pk).count()
        if total_sent > 0 and total_clicked > 0:
            return (total_clicked / total_sent) * 100
        return 0

    def click_to_open_rate(self):
        """
        Click to open rate is the percentage of recipients who opened
        the email message and also clicked on any link in the email message.
        """
        total_opened = Open.objects.filter(sent_email_message__email_message_id=self.pk).count()
        total_clicked = Click.objects.filter(sent_email_message__email_message_id=self.pk).count()
        return (total_opened / total_clicked) * 100

    def disable(self):
        self.enabled = False
        return self.save()


class SentEmailMessage(models.Model):
    """
    Keeps a record of all sent drips.
    Has OneToOne relations for open, click, spam, unsubscribe. Calling self.opened will return a boolean.
    If it exists, it returns True, and you can assume it has been opened.
    This is done this way to save database space, since the majority of senddrips won't even be opened, and to add extra
    data (such as timestamps) to filter off, so you could see your open rate for a drip within the past 24 hours.
    """
    date = models.DateTimeField(default=timezone.now)
    email_message = models.ForeignKey('squeezemail.EmailMessage', related_name='sent_email_messages')
    subscriber = models.ForeignKey('squeezemail.Subscriber', related_name='sent_email_messages')
    # sent = models.BooleanField(default=False)

    class Meta:
        unique_together = ('email_message', 'subscriber')

    @property
    def opened(self):
        return hasattr(self, 'open')

    @property
    def clicked(self):
        return hasattr(self, 'click')

    @property
    def spammed(self):
        return hasattr(self, 'spam')

    @property
    def unsubscribed(self):
        return hasattr(self, 'unsubscribe')

    @property
    def bounced(self):
        return hasattr(self, 'bounce')


class Open(models.Model):
    sent_email_message = models.OneToOneField('SentEmailMessage', primary_key=True)
    date = models.DateTimeField(default=timezone.now)


class Click(models.Model):
    sent_email_message = models.OneToOneField('SentEmailMessage', primary_key=True)
    date = models.DateTimeField(default=timezone.now)


class Spam(models.Model):
    sent_email_message = models.OneToOneField('SentEmailMessage', primary_key=True)
    date = models.DateTimeField(default=timezone.now)


class Unsubscribe(models.Model):
    sent_email_message = models.OneToOneField('SentEmailMessage', primary_key=True)
    date = models.DateTimeField(default=timezone.now)


class Bounce(models.Model):
    sent_email_message = models.OneToOneField('SentEmailMessage', primary_key=True)
    date = models.DateTimeField(default=timezone.now)


# class QuerySetRule(StepPlugin):
class QuerySetRule(models.Model):
    email_message = models.ForeignKey('EmailMessage', null=True, blank=True, related_name="queryset_rules")
    # date = models.DateTimeField(auto_now_add=True)
    # lastchanged = models.DateTimeField(auto_now=True)
    # content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    # object_id = GfkLookupField('content_type')
    # content_object = GenericForeignKey('content_type', 'object_id')
    method_type = models.CharField(max_length=12, default='filter', choices=METHOD_TYPES)
    field_name = models.CharField(max_length=128, verbose_name='Field name of Subscriber')
    lookup_type = models.CharField(max_length=12, default='exact', choices=LOOKUP_TYPES)

    field_value = models.CharField(max_length=255,
        help_text=('Can be anything from a number, to a string. Or, do ' +
                   '`now-7 days` or `today+3 days` for fancy timedelta.'))

    def step_run(self, calling_step, subscription_qs):
        # We want to run the filters off of Subscriber instead of Subscription.
        subscriber_qs = Subscriber.objects.filter(id__in=subscription_qs.values_list('subscriber_id', flat=True))
        filtered_subscriber_ids = self.apply(subscriber_qs).values_list('id', flat=True)
        return subscription_qs.filter(subscriber_id__in=filtered_subscriber_ids)

    def clean(self):
        try:
            self.apply(Subscriber.objects.all())
        except Exception as e:
            raise ValidationError(
                '%s raised trying to apply rule: %s' % (type(e).__name__, e))

    @property
    def annotated_field_name(self):
        field_name = self.field_name
        if field_name.endswith('__count'):
            agg, _, _ = field_name.rpartition('__')
            field_name = 'num_%s' % agg.replace('__', '_')
        return field_name

    def apply_any_annotation(self, qs):
        if self.field_name.endswith('__count'):
            field_name = self.annotated_field_name
            agg, _, _ = self.field_name.rpartition('__')
            qs = qs.annotate(**{field_name: models.Count(agg, distinct=True)})
        return qs

    def filter_kwargs(self, qs, now=timezone.now):
        # Support Count() as m2m__count
        field_name = self.annotated_field_name
        field_name = '__'.join([field_name, self.lookup_type])
        field_value = self.field_value

        # set time deltas and dates
        if self.field_value.startswith('now-'):
            field_value = self.field_value.replace('now-', '')
            field_value = now() - djangotimedelta.parse(field_value)
        elif self.field_value.startswith('now+'):
            field_value = self.field_value.replace('now+', '')
            field_value = now() + djangotimedelta.parse(field_value)
        elif self.field_value.startswith('today-'):
            field_value = self.field_value.replace('today-', '')
            field_value = now().date() - djangotimedelta.parse(field_value)
        elif self.field_value.startswith('today+'):
            field_value = self.field_value.replace('today+', '')
            field_value = now().date() + djangotimedelta.parse(field_value)

        # F expressions
        if self.field_value.startswith('F_'):
            field_value = self.field_value.replace('F_', '')
            field_value = models.F(field_value)

        # set booleans
        if self.field_value == 'True':
            field_value = True
        if self.field_value == 'False':
            field_value = False

        kwargs = {field_name: field_value}

        return kwargs

    def apply(self, qs, now=timezone.now):

        kwargs = self.filter_kwargs(qs, now)
        qs = self.apply_any_annotation(qs)

        if self.method_type == 'filter':
            return qs.filter(**kwargs)
        elif self.method_type == 'exclude':
            return qs.exclude(**kwargs)

        # catch as default
        return qs.filter(**kwargs)


# class Subscription(models.Model):
#     funnel = models.ForeignKey('squeezemail.Funnel', related_name='subscriptions')
#     subscriber = models.ForeignKey('squeezemail.Subscriber', related_name="subscriptions")
#     created = models.DateTimeField(verbose_name="Subscribe Date", default=timezone.now)
#     is_active = models.BooleanField(verbose_name="Active", default=True)
#     step = models.ForeignKey('squeezemail.Step', related_name="subscriptions")
#     step_timestamp = models.DateTimeField(verbose_name="Last Step Activity Timestamp", default=timezone.now)
#
#     class Meta:
#         unique_together = ('funnel', 'subscriber')
#
#     def move_to_step(self, step_id):
#         self.step_id = step_id
#         self.step_timestamp = timezone.now()
#         self.save()
#         return self


class SubscriberManager(models.Manager):
    """
    Custom manager for Subscriber to provide extra functionality
    """
    use_for_related_fields = True

    def get_or_add(self, email, *args, **kwargs):
        try:
            #Try to get existing subscriber
            subscriber = self.get(email__iexact=email)
        except self.model.DoesNotExist:
            try:
                # Subscriber doesn't exist. Does a user exist with the same email?
                user = get_user_model().objects.get(email__iexact=email)
                # Create a new subscriber and tie to user
                subscriber = self.create(user=user, email=email)
            except ObjectDoesNotExist:
                # User doesn't exist, so create just the subscriber
                subscriber = self.create(email=email)
        return subscriber

    def active(self):
        """
        Gives only the active subscribers
        """
        return self.filter(is_active=True)


class Subscriber(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name="squeeze_subscriber", null=True, blank=True)
    email = models.EmailField(max_length=254, db_index=True, unique=True)
    is_active = models.BooleanField(verbose_name="Active", default=True)
    created = models.DateTimeField(default=timezone.now)
    tags = models.ManyToManyField('Tag', related_name='subscribers', blank=True)
    idle = models.BooleanField(default=False)

    objects = SubscriberManager()
    default_manager = objects

    def __str__(self):
        return self.email

    def get_email(self):
        return self.user.email if self.user_id else self.email

    def unsubscribe(self):
        if self.is_active:
            self.is_active = False
            self.save()
        return self

    def opened_email(self, email):
        return self.sent_email_messages.get(id=email.id).opened

    def get_token(self):
        """
        Gets a key/token to pass to email footer's unsubscribe link, so only the owner of the email can unsubscribe.
        Also used to allow database writing for clicks/opens/etc.
        """
        return get_token_for_email(self.email)

    @cached_property
    def token(self):
        return self.get_token()

    def match_token(self, token):
        return str(token) == str(self.token)

    def step_remove(self, subscriber):
        """
        Used by a 'Modify' step. it'll call this and pass in the subscriber.
        It may feel weird since we're not using self.is_active, but that's on purpose.
        """
        subscriber.is_active = False
        subscriber.save()
        return subscriber

    def is_idle(self):
        """
        Check if subscriber has any email activity (opens/clicks) over the past 90 days
        """
        return Open.objects.filter(date__gte=timezone.now() - timezone.timedelta(days=90)).exists()


EmailMessagePlugin = create_plugin_base(EmailMessage)


class RichText(plugins.RichText, EmailMessagePlugin):
    pass


# class Image(plugins.Image, DripPlugin):
#     url = models.TextField(max_length=500, null=True, blank=True)

#
# class DripOperator(StepPlugin):
#     drip = models.ForeignKey('squeezemail.Drip', related_name='operators+')
#
#     class Meta:
#         verbose_name = 'Send A Drip'
#
#     def step_run(self, calling_step, subscription_qs):
#         return self.drip.step_run(calling_step, subscription_qs)
#
#     def __str__(self):
#         return self.drip.name
#
#
# class ModificationOperator(StepPlugin):
#     """
#     Attempts to run the specified method of a class in the form of
#     step_*choice* (e.g. step_remove), and passes the subscriber to it.
#     Useful for adding/removing a tag,
#     """
#     MODIFY_CHOICES = (
#         ('add', 'Add'),
#         ('move', 'Move'),
#         ('remove', 'Remove'),
#     )
#     modify_type = models.CharField(max_length=75, choices=MODIFY_CHOICES)
#     content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
#     object_id = GfkLookupField('content_type')
#     content_object = GenericForeignKey('content_type', 'object_id')
#
#     class Meta:
#         verbose_name = 'Subscriber Modification'
#         verbose_name_plural = 'Subscriber Modifications'
#
#     def get_method_name(self):
#         # Get the method name to run on the content_object (e.g. 'step_add')
#         return 'step_%s' % self.modify_type
#
#     def step_run(self, calling_step, subscription_qs):
#         method_name = self.get_method_name()
#         content_object = self.content_object
#         for subscription in subscription_qs:
#             call_method = getattr(content_object, method_name)(calling_step=calling_step, subscription=subscription)
#         return subscription_qs
#
#     def clean(self):
#         """
#         Make sure the chosen content_object has the proper runnable method name on it.
#         You could 'add' or 'remove' a tag, but you can't 'move' a tag because it doesn't make sense.
#         """
#         try:
#             getattr(self.content_object, self.get_method_name())
#         except Exception as e:
#             raise ValidationError(
#                 '%s does not have method name %s: %s' % (type(e).__name__, self.get_method_name(), e))
#
#     def __str__(self):
#         return '%s %s "%s" ' % (self.modify_type, self.content_type, self.content_object)
#
#
# class EmailActivityOperator(models.Model):
#     TYPE_CHOICES = (
#         ('open', 'Opened'),
#         ('click', 'Clicked'),
#         ('spam', 'Reported Spam'),
#         ('unsubscribe', 'Unsubscribed'),
#         ('sent', 'Was Sent'),
#     )
#     type = models.CharField(max_length=75, choices=TYPE_CHOICES)
#     drip = models.ForeignKey('squeezemail.Drip', related_name='email_activity+')
#     # check_last = models.IntegerField(help_text="How many previously sent drips/emails to check", default=1)
#     # on_true = models.ForeignKey('squeezemail.Step', null=True, blank=True, related_name='step_email_activity_on_true+')
#     # on_false = models.ForeignKey('squeezemail.Step', null=True, blank=True, related_name='step_email_activity_on_false+')
#
#     def step_run(self, calling_step, subscriber_qs):
#         subscriber_id_list = subscriber_qs.values_list('id', flat=True)
#         qs_true = False
#         qs_false = False
#         true_ids = []
#
#         # Get all of the last SendDrips that our subscribers have been sent
#         # last_send_drip_id_list = SendDrip.objects.filter(subscriber_id__in=subscriber_id_list, sent=True)\
#         #     .order_by('-date')[:self.check_last].values_list('id', flat=True)
#
#         # if self.type is 'open':
#         #     # Get the last check_last Opens from the subscriber list
#         #     opened_senddrip_id_list = Open.objects.filter(drip_id__in=last_send_drip_id_list).values_list('senddrip_id', flat=True)
#         #     qs_true = subscriber_qs.filter(send_drips__id=opened_senddrip_id_list)
#         #     true_ids = qs_true.values_list('id', flat=True)
#         #
#         # if self.on_true_id:
#         #     for subscriber in qs_true:
#         #         subscriber.move_to_step(self.on_true_id)
#         #
#         # if self.on_false_id:
#         #     qs_false = qs.exclude(id__in=true_ids)
#         #     for subscriber in qs_false:
#         #         subscriber.move_to_step(self.on_false_id)
#         return subscriber_qs
#
#
# class Event(models.Model):
#     date = models.DateTimeField(default=timezone.now)
#     content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
#     object_id = GfkLookupField('content_type')
#     content_object = GenericForeignKey('content_type', 'object_id')
#     data = JSONField()

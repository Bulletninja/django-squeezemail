import json
import logging

import sys
from django import forms
from django.template import Context
from django.contrib import admin

# from squeezemail.actions.drip.models import DripOperator
# from squeezemail.actions.modification.models import ModificationOperator
from .models import EmailMessage, SentEmailMessage, QuerySetRule, Subject, Subscriber, Tag
from .handlers import configured_message_classes, message_class_for

from content_editor.admin import (
    ContentEditor
)

logger = logging.getLogger(__name__)


# class QuerySetRuleInline(GenericTabularInline):
#     model = QuerySetRule
#
#     def _media(self):
#         return forms.Media(
#             css={
#                 'all': ('css/queryset_rules.css',)
#             },
#         )
#     media = property(_media)


# class ActionQuerySetRuleInline(ContentEditorInline):
#     model = QuerySetRule
#     exclude = ('email_message',)
#
#     def _media(self):
#         return forms.Media(
#             css={
#                 'all': ('css/queryset_rules.css',)
#             },
#         )
#     media = property(_media)


# class ActionDripInline(ContentEditorInline):
#     model = DripOperator
#
#
# class ActionModificationInline(ContentEditorInline):
#     model = ModificationOperator

#
# class StepAdmin(DraggableMPTTAdmin, ContentEditor):
#     model = Step
#     generic_raw_id_fields = ['content_object']
#     # raw_id_fields = ('parent',)
#     list_display = ('tree_actions', 'indented_title', 'get_active_subscription_count')
#     list_display_links = ('indented_title',)
#
#     inlines = [
#         ActionDripInline,
#         ActionModificationInline,
#         ActionQuerySetRuleInline,
#         # ActionDecisionInline,
#         # QuerySetRuleInline
#     ]
#
#     def build_extra_context(self, extra_context):
#         from .utils import get_simple_fields
#         extra_context = extra_context or {}
#         extra_context['field_data'] = json.dumps(get_simple_fields(Subscriber))
#         return extra_context
#
#     def add_view(self, request, form_url='', extra_context=None):
#         return super(StepAdmin, self).add_view(
#             request, extra_context=self.build_extra_context(extra_context))
#
#     def change_view(self, request, object_id, form_url='', extra_context=None):
#         return super(StepAdmin, self).change_view(
#             request, object_id, extra_context=self.build_extra_context(extra_context))

#
# class FunnelAdmin(admin.ModelAdmin):
#     list_display = ('__str__', 'get_subscription_count')
#
#
# class SubscriptionInline(admin.TabularInline):
#     model = Subscription
#     extra = 1


class EmailMessageSplitSubjectInline(admin.TabularInline):
    model = Subject
    extra = 1


class EmailMessageForm(forms.ModelForm):
    message_class = forms.ChoiceField(
        choices=((k, '%s (%s)' % (k, v)) for k, v in configured_message_classes().items())
    )

    class Meta:
        model = EmailMessage
        exclude = []


class SubscriberAdmin(admin.ModelAdmin):
    # inlines = [SubscriptionInline]
    raw_id_fields = ('user',)
    search_fields = ['email', 'user__email', 'user__username', 'id', 'tags__name']
    list_display = ['email', 'created', 'is_active', 'idle']
    list_filter = ['created', 'is_active', 'idle']


class QuerySetRuleInline(admin.TabularInline):
    model = QuerySetRule
    exclude = ('parent', 'region', 'ordering',)

    def _media(self):
        return forms.Media(
            css={
                'all': ('css/queryset_rules.css',)
            },
        )
    media = property(_media)


class EmailMessageAdmin(ContentEditor):
    model = EmailMessage
    # change_form_template = 'admin/squeezemail/drip/change_form.html'
    # fieldsets = [
    #     (None, {
    #         'fields': ['enabled', 'name', 'message_class'],
    #         }),
    #     #('Important things', {'fields': ('DripSplitSubjectInline',)}),
    #     item_editor.FEINCMS_CONTENT_FIELDSET,
    #     ]
    list_display=(
        'name',
        'enabled',
        'message_class',
        'total_sent',
        'total_unique_opens',
        'total_opens',
        'total_unique_clicks',
        'total_clicks',
        'total_unsubscribes',
        'total_bounces',
        'total_spammed',
        'unique_open_rate',
        'open_rate',
        'unique_click_rate',
        'click_rate',
        'unique_click_to_open_rate',
        'click_to_open_rate',
        'bounce_rate',
        'unsubscribe_rate',
        'spam_rate'
    )

    def total_sent(self, obj):
        return obj.total_sent
    total_sent.short_description = "Sent"

    def total_unique_opens(self, obj):
        return obj.total_unique_opens
    total_unique_opens.short_description = "Unique Opens"

    def total_opens(self, obj):
        return obj.total_opens
    total_opens.short_description = "Total Opens"

    def total_unique_clicks(self, obj):
        return obj.total_unique_clicks
    total_unique_clicks.short_description = "Unique Clicks"

    def total_clicks(self, obj):
        return obj.total_clicks
    total_clicks.short_description = "Total Clicks"

    def total_unsubscribes(self, obj):
        return obj.total_unsubscribes
    total_unsubscribes.short_description = "Unsubscribes"

    def total_bounces(self, obj):
        return obj.total_bounces
    total_bounces.short_description = "Bounces"

    def total_spammed(self, obj):
        return obj.total_spammed
    total_spammed.short_description = "Spam Reports"

    def unique_open_rate(self, obj):
        return obj.unique_open_rate()
    unique_open_rate.short_description = "Unique Open Rate"

    def open_rate(self, obj):
        return obj.open_rate()
    open_rate.short_description = "Open Rate"

    def unique_click_rate(self, obj):
        return obj.unique_click_rate()
    unique_click_rate.short_description = "Unique Click Rate"

    def click_rate(self, obj):
        return obj.click_rate()
    click_rate.short_description = "Click Rate"

    def unique_click_to_open_rate(self, obj):
        return obj.unique_click_to_open_rate()
    unique_click_to_open_rate.short_description = "Unique Click to Open Rate"

    def click_to_open_rate(self, obj):
        return obj.click_to_open_rate()
    click_to_open_rate.short_description = "Click to Open Rate"

    def bounce_rate(self, obj):
        return obj.bounce_rate()
    bounce_rate.short_description = "Bounce Rate"

    def unsubscribe_rate(self, obj):
        return obj.unsubscribe_rate()
    unsubscribe_rate.short_description = "Unsubscribe Rate"

    def spam_rate(self, obj):
        return obj.spam_rate()
    spam_rate.short_description = "Spam Report Rate"

    form = EmailMessageForm

    # raw_id_fields = ['parent']

    av = lambda self, view: self.admin_site.admin_view(view)

    def email_message_preview(self, request, email_message_id, subscriber_id):
        from django.shortcuts import get_object_or_404
        from django.http import HttpResponse
        email_message = get_object_or_404(EmailMessage, id=email_message_id)
        subscriber = get_object_or_404(Subscriber, id=subscriber_id)
        MessageClass = message_class_for(email_message.message_class)
        email_message_class = MessageClass(email_message, subscriber)
        html = ''
        mime = ''
        if email_message_class.message.alternatives:
            for body, mime in email_message_class.message.alternatives:
                if mime == 'text/html':
                    html = body
                    mime = 'text/html'
        else:
            #TODO: consider adding ability to view plaintext email. Leaving this code here to expand upon.
            html = email_message_class.message.body
            mime = 'text/plain'
        return HttpResponse(html, content_type=mime)

    def email_message_broadcast_preview(self, request, email_message_id):
        from django.shortcuts import render, get_object_or_404
        email_message = get_object_or_404(EmailMessage, id=email_message_id)
        handler = email_message.handler()
        qs = handler.prune()  # Only show us subscribers that we're going to be sending to
        if email_message.slice:
            qs = handler.apply_slice(subscriber_list=qs, slice=email_message.slice)
        ctx = Context({
            'email_message': email_message,
            'queryset_preview': qs[:20],
            'count': qs.count(),
        })
        return render(request, 'admin/squeezemail/emailmessage/broadcast_preview.html', ctx)

    def email_message_broadcast_send(self, request, email_message_id):
        from django.shortcuts import get_object_or_404
        from django.http import HttpResponse
        email_message = get_object_or_404(EmailMessage, id=email_message_id)
        result_tasks = email_message.handler().broadcast_run()
        mime = 'text/plain'
        return HttpResponse('Broadcast queued. Email Message "%s" has been disabled to protect you from accidentally sending it out again. You may leave this page.' % email_message.name, content_type=mime)

    def build_extra_context(self, extra_context):
        from .utils import get_simple_fields
        extra_context = extra_context or {}
        extra_context['field_data'] = json.dumps(get_simple_fields(Subscriber))
        return extra_context

    def add_view(self, request, form_url='', extra_context=None):
        return super(EmailMessageAdmin, self).add_view(
            request, extra_context=self.build_extra_context(extra_context))

    def change_view(self, request, object_id, form_url='', extra_context=None):
        return super(EmailMessageAdmin, self).change_view(
            request, object_id, extra_context=self.build_extra_context(extra_context))

    def get_urls(self):
        from django.conf.urls import url
        urls = super(EmailMessageAdmin, self).get_urls()
        my_urls = [
            url(
                r'^(?P<email_message_id>[\d]+)/preview/(?P<subscriber_id>[\d]+)/$',
                self.av(self.email_message_preview),
                name='email_message_preview'
            ),
            url(
                r'^(?P<email_message_id>[\d]+)/broadcast/$',
                self.av(self.email_message_broadcast_preview),
                name='email_message_broadcast_preview'
            ),
            url(
                r'^(?P<email_message_id>[\d]+)/broadcast/send/$',
                self.av(self.email_message_broadcast_send),
                name='email_message_broadcast_send'
            )
        ]
        return my_urls + urls


class SentEmailMessageAdmin(admin.ModelAdmin):
    # list_display = [f.name for f in SentEmailMessage._meta.fields]
    ordering = ['-id']
    list_display = ['id', 'date', 'subscriber', 'email_message', 'opened', 'clicked', 'unsubscribed', 'bounced', 'spammed']
    search_fields = ['subscriber__email']

    def opened(self, obj):
        return obj.opened
    opened.short_description = "Opened"

    def clicked(self, obj):
        return obj.clicked
    clicked.short_description = "Clicked"

    def unsubscribed(self, obj):
        return obj.unsubscribed
    unsubscribed.short_description = "Unsubscribed"

    def bounced(self, obj):
        return obj.bounced
    bounced.short_description = "Bounced"

    def spammed(self, obj):
        return obj.spammed
    spammed.short_description = "Spammed"


# admin.site.register(EmailMessage, EmailMessageAdmin)
admin.site.register(Subscriber, SubscriberAdmin)
# admin.site.register(Step, StepAdmin)
admin.site.register(Tag)
# admin.site.register(Funnel, FunnelAdmin)
admin.site.register(SentEmailMessage, SentEmailMessageAdmin)

try:
    from squeezemail_extensions.admin import *
except ImportError as error:
    logger.error("You need to create a squeezemail_extensions app with admin.py inside.")
    raise error.with_traceback(sys.exc_info()[2])
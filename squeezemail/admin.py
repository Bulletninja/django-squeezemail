import json

from django import forms
from django.template import Context
#from django.contrib.contenttypes.admin import GenericTabularInline
from django.contrib import admin
#from mptt.admin import DraggableMPTTAdmin

# from squeezemail.actions.drip.models import DripOperator
# from squeezemail.actions.modification.models import ModificationOperator
from .models import EmailMessage, SentEmailMessage, QuerySetRule, Subject, Subscriber, RichText, Tag# Step, Funnel,  DripOperator, ModificationOperator, Subscription
from .handlers import configured_message_classes, message_class_for

from content_editor.admin import (
    ContentEditor, ContentEditorInline
)


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


# class CampaignDripInline(admin.TabularInline):
#     model = CampaignDrip


# class CampaignAdmin(admin.ModelAdmin):
#     inlines = [CampaignDripInline]


class SubscriberAdmin(admin.ModelAdmin):
    # inlines = [SubscriptionInline]
    pass


class RichTextInline(ContentEditorInline):
    """
    The only difference with the standard ``ContentEditorInline`` is that this
    inline adds the ``feincms3/plugin_ckeditor.js`` file which handles the
    CKEditor widget activation and deactivation inside the content editor.
    """
    model = RichText

    class Media:
        js = ('js/plugin_ckeditor.js',)


# class ImageInline(ContentEditorInline):
#     form = AlwaysChangedModelForm
#     model = Image
#     extra = 0
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
        'message_class'
    )
    # list_display_links=(
    #     'indented_title',
    # )
    # list_display = ('name', 'enabled', 'message_class')
    inlines = [
        EmailMessageSplitSubjectInline,
        QuerySetRuleInline,
        RichTextInline,
        # ImageInline
    ]

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
    list_display = [f.name for f in SentEmailMessage._meta.fields]
    ordering = ['-id']


admin.site.register(EmailMessage, EmailMessageAdmin)
admin.site.register(Subscriber, SubscriberAdmin)
# admin.site.register(Step, StepAdmin)
admin.site.register(Tag)
# admin.site.register(Funnel, FunnelAdmin)
admin.site.register(SentEmailMessage, SentEmailMessageAdmin)

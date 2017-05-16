"""
Provides a rich text area whose content is automatically cleaned using a
very restrictive white list of tags and attributes.

Depends on feincms-cleanse_.
"""
from django.db import models
from django.utils.html import mark_safe, strip_tags
from django.utils.text import Truncator
from django.utils.translation import ugettext_lazy as _

# from content_editor.admin import ContentEditorInline

from ckeditor.fields import RichTextField
from feincms_cleanse import Cleanse

__all__ = ('RichText', 'render_richtext', 'CleansedRichTextField', 'cleanse_html')

"""
HTML cleansing is by no means only useful for user generated content.
Managers also copy-paste content from word processing programs, the rich
text editor's output isn't always (almost never) in the shape we want it
to be, and a strict white-list based HTML sanitizer is the best answer
I have.
"""


# Site-wide patch of cleanse settings
# -----------------------------------

Cleanse.allowed_tags['a'] += ('id', 'name')  # Allow anchors
Cleanse.allowed_tags['hr'] = ()  # Allow horizontal rules
Cleanse.allowed_tags['h1'] = ()  # Allow H1
Cleanse.allowed_tags['h2'] = ()  # Allow H2
Cleanse.allowed_tags['h3'] = ()  # Allow H3
Cleanse.allowed_tags['h4'] = ()  # Allow H4
Cleanse.allowed_tags['img'] = ('src')  # Allow img
Cleanse.empty_tags += ('hr', 'a', 'br', 'img')  # Allow empty <hr/> and anchor targets


def cleanse_html(html):
    """
    Pass ugly HTML, get nice HTML back.
    """
    return Cleanse().cleanse(html)


class CleansedRichTextField(RichTextField):
    """
    This is a subclass of django-ckeditor's ``RichTextField``. The recommended
    configuration is as follows::

        CKEDITOR_CONFIGS = {
            'default': {
                'toolbar': 'Custom',
                'format_tags': 'h1;h2;h3;p;pre',
                'toolbar_Custom': [
                    ['Format', 'RemoveFormat'],
                    ['Bold', 'Italic', 'Strike', '-',
                     'NumberedList', 'BulletedList', '-',
                     'Anchor', 'Link', 'Unlink', '-',
                     'Source'],
                ],
            },
        }

        # Settings for feincms3.plugins.richtext.RichText
        CKEDITOR_CONFIGS['richtext-plugin'] = CKEDITOR_CONFIGS['default']

    If you want or require a different cleansing function, simply override
    the default with ``CleansedRichTextField(cleanse=your_function)``. The
    cleansing function receives the HTML as its first and only argument and
    returns the cleansed HTML.
    """

    def __init__(self, *args, **kwargs):
        self.cleanse = kwargs.pop('cleanse', cleanse_html)
        super(CleansedRichTextField, self).__init__(*args, **kwargs)

    def clean(self, value, instance):
        return self.cleanse(
            super(CleansedRichTextField, self).clean(value, instance))


class RichText(models.Model):
    """
    Rich text plugin

    Usage::

        class Page(...):
            # ...

        PagePlugin = create_plugin_base(Page)

        class RichText(plugins.RichText, PagePlugin):
            pass

    To use this, a django-ckeditor_ configuration named ``richtext-plugin`` is
    required. See the section :mod:`HTML cleansing <feincms3.cleanse>` for the
    recommended configuration.
    """

    # text = CleansedRichTextField(_('text'), config_name='richtext-plugin')
    text = RichTextField(_('text'), config_name='richtext-plugin')

    class Meta:
        abstract = True
        verbose_name = _('rich text')
        verbose_name_plural = _('rich texts')

    def __str__(self):
        # Return the first few words of the content (with tags stripped)
        return Truncator(strip_tags(self.text)).words(10, truncate=' ...')


def render_richtext(plugin, **kwargs):
    """
    Return the text of the rich text plugin as a safe string (``mark_safe``)
    """
    return mark_safe(plugin.text)

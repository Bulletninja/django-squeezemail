**Important Note:** It's a long road ahead to achieve the funnel features I'm striving for. Only broadcast emails are
implemented right now. It's possible to do some fancy things with it that are not broadcast emails, but I intend to
support funnel-like functionality in the distant future.

===========
Squeezemail
===========
Long term, this is to hopefully be a Django email drip/autoresponder primarily used by marketers to send their mailing list subscribers emails depending on
how long they've been on a mailing list, what they may have been tagged with, previous email activity, and filter/exclude queries defined by you.

"Broadcast" (send to all subscribers) emails supported so far.


Why?
====
After using django-drip (the package that this project was based on) for a couple years, I realized I was creating over
a hundred drips that all basically had the same custom queries, and I thought I could get a little more functionality
out of them if I hard coded those parts in, and also be less prone to human error.

With django-drip, sending a broadcast out to 100,000+ subscribers took 27+ hours, and all cronjobs would have to be paused so it wouldn't send a user the same email more than once. Lots of babysitting for a big list.

I found my database was absolutely massive from the 'SentDrip' model used by django-drip (8 million records).

Most importantly, I was looking for a way to 'funnel' users through steps without paying a ridiculous amount of money for a 3rd party solution.


Current Features
=============
- Broadcast emails to your subscribers.
- Open/Click/Spam/Unsubscribe tracking (and bounce tracking with things like Amazon SES).
- Content blocks.
- Partial email subject split testing (you can add different subjects to split test, but learning which one is best is not implemented).


To be implemented in the distant future
=============
- Multiple funnels that will start a subscriber on a specified step.
- A tree of 'Steps' that the subscriber is sent down. They flow through the steps depending on how you build it.
- Ability to send an email based on if the subscriber opened the previous email in the sequence they're on.
- Tests.


==========
Quickstart
==========
This quickstart assumes you have a working Celery worker running.
If you don't, follow this first: http://docs.celeryproject.org/en/latest/django/first-steps-with-django.html


1. Add all of the required apps to your settings.py:
::
    'content_editor',
    'ckeditor',
    'versatileimagefield',
    'squeezemail'


2. Add to settings.py:
::
    # Defaults to https, but if you use http, you need this setting.
    SQUEEZE_DEFAULT_HTTP_PROTOCOL = 'http'

    # For Squeezemail's Richtext editor. Customizable, but this'll get you started.
    CKEDITOR_JQUERY_URL = '//ajax.googleapis.com/ajax/libs/jquery/2.1.1/jquery.min.js'
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

    # Settings for squeezemail.plugins.richtext.RichText
    CKEDITOR_CONFIGS['richtext-plugin'] = CKEDITOR_CONFIGS['default']

    # Because squeezemail wants you to be able to fully customize your emails, you have to manage your own migrations.
    MIGRATION_MODULES = {
        'squeezemail': 'squeezemail_extensions.migrations',
    }

    # Does your email service have rate limits?
    SQUEEZE_BROADCAST_EMAIL_RATE_LIMIT = '20/s'  # 20 emails per second


3. Add squeezemail's url to your project's urls.py.
::
    url(r'^squeezemail/', include('squeezemail.urls', namespace="squeezemail")),

All rebuilt links point to yourdomain.com/squeezemail/..., but doesn't have to be /squeezemail/. I personally use /e/. Change that here.


4. Create the squeezemail_extensions app.
::
It has to be called "squeezemail_extensions". Do not add it to your settings.py installed apps.

    ./manage.py startapp squeezemail_extensions

Squeezemail is opinionated on some things, but doesn't dare to assume anything when it comes to rendering your emails. Slightly hacky because of the way Django is.
You need a squeezemail_extensionns app to create your own email rendering content blocks (like text, images, personalized coupons, etc.)
A richtext and image plugin are provided for you to subclass and add to your app easily, though.

5. Add your email message content blocks
::
You'll want a Richtext plugin at the very least, but we'll add both a Richtext and Image plugin to get started.

    # squeezemail_extensions.models.py

    from django.db import models

    from squeezemail import plugins

    from squeezemail.models import EmailMessagePlugin


    class RichText(plugins.RichText, EmailMessagePlugin):
        pass


    class Image(plugins.Image, EmailMessagePlugin):
        pass


    # squeezemail_extensions.renderer.py

    from django.utils.safestring import mark_safe

    from squeezemail.renderer import renderer
    from squeezemail_extensions.models import Image, RichText, Recipe


    renderer.register_string_renderer(
        RichText,
        lambda plugin: mark_safe(plugin.text),
    )

    renderer.register_template_renderer(
        Image,
        'squeezemail/plugins/image.html',
    )


    # squeezemail_extensions.admin.py

    from django.contrib import admin
    from content_editor.admin import ContentEditorInline

    from squeezemail.admin import EmailMessageAdmin, EmailMessageSplitSubjectInline, QuerySetRuleInline
    from squeezemail.models import EmailMessage
    from squeezemail.plugins import ImageInline, RichTextInline
    from squeezemail_extensions.models import Image, RichText


    class CustomEmailMessageAdmin(EmailMessageAdmin):
        inlines = [
            EmailMessageSplitSubjectInline,
            QuerySetRuleInline,
            RichTextInline.create(model=RichText),
            ImageInline.create(model=Image),
            RecipeInline,
        ]


    admin.site.register(EmailMessage, CustomEmailMessageAdmin)


6. Make migrations and migrate.
::
    ./manage.py makemigrations squeezemail
    ./manage.py migrate squeezemail


7. Run collectstatic:
::
    ./manage.py collectstatic



Special Thanks
==============
Bryan Helmig & Zapier for django-drip (https://github.com/zapier/django-drip), which this project is based off of.

Marc Egli's Pennyblack for inspiration to use feincms in a newsletter.

matthiask for content-blocks, feincms and many other excellent repos.

pmclanahan's django-celery-email (https://github.com/pmclanahan/django-celery-email) for his clever chunked function with celery.

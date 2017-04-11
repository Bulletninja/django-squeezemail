**ATTENTION: This code is all subject to change. Not recommended for production use. Don't use if you value your sanity.**

**If you're using the original prototype of squeezemail, this isn't compatible with the previous prototype because of the massive model changes.**

**Important Note:** It's a long road ahead to achieve the funnel features I'm striving for. Only broadcast emails are
implemented right now. It's possible to do some fancy things with it that are not broadcast emails, but I intend to
support funnel-like functionality in the distant future.

===========
Squeezemail
===========
A Django email drip/autoresponder primarily used by marketers to send their mailing list subscribers emails depending on
how long they've been on a mailing list, what they may have been tagged with, previous email activity,
and filter/exclude queries defined by you.

"Broadcast" (send to all) emails supported so far.

Why?
====
After using django-drip (the package that this project was based on) for a couple years, I realized I was creating over
a hundred drips that all basically had the same custom queries, and I thought I could get a little more functionality
out of them if I hard coded those parts in, and also be less prone to human error.

With django-drip, sending a broadcast out to 100,000+ subscribers took 27+ hours, and all cronjobs would have to be paused so it wouldn't send a user the same email more than once. Lots of babysitting for a big list.

I found my database was absolutely massive from the 'SentDrip' model used by django-drip (8 million records).

Most importantly, I was looking for a way to 'funnel' users through steps without paying a ridiculous amount of money for a 3rd party solution.

Main Features (to be implemented)
=============
- Broadcast emails to your subscribers.
- Multiple funnels that will start a subscriber on a specified step.
- A tree of 'Steps' that the subscriber is sent down. They flow through the steps depending on how you build it.
- Ability to send an email based on if the subscriber opened the previous email in the sequence they're on.
- Open/Click/Spam/Unsubscribe tracking.
- Email Subject & body split testing.
- Tiny 'SentEmailMessage' model, with bare minimum fields.
- Feincms3's content blocks.
- Send stats to google analytics.

==========
Quickstart
==========
This quickstart assumes you have a working Celery worker running.
If you don't, follow this first: http://docs.celeryproject.org/en/latest/django/first-steps-with-django.html


1. Add all of the required apps to your settings.py:
::
    'feincms3',
    'content_editor',
    'ckeditor',
    'squeezemail'

2. Add to settings.py:
::
    SQUEEZE_DEFAULT_HTTP_PROTOCOL = 'http'
We rebuild all the links in each email to track clicks, so we need to know which protocol to use. If your site is http, set to http, if it's ssl, set to https.

::
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

    # Settings for feincms3.plugins.richtext.RichText
    CKEDITOR_CONFIGS['richtext-plugin'] = CKEDITOR_CONFIGS['default']

    #Tracking
    GOOGLE_ANALYTICS_ID = 'UA-XXXXXXXXX-1' # Your google analytics id
    DEFAULT_TRACKING_DOMAIN = 'yourdomain.com'


3. Add squeezemail's url to your project's urls.py.
::
    url(r'^squeezemail/', include('squeezemail.urls', namespace="squeezemail")),

All rebuilt links point to yourdomain.com/squeezemail/..., but doesn't have to be /squeezemail/, it can just be /e/ if you'd like. Change that here.


4. Migrate.
::
    ./manage.py migrate squeezemail


5. Run collectstatic:
::
    ./manage.py collectstatic



Special Thanks
==============
Bryan Helmig & Zapier for django-drip (https://github.com/zapier/django-drip), which this project is based off of.

Marc Egli's Pennyblack for inspiration to use feincms in a newsletter.

pmclanahan's django-celery-email (https://github.com/pmclanahan/django-celery-email) for his clever chunked function with celery.

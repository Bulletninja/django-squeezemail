from django.utils import timezone

try:
    # Python 3 imports
    from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
except ImportError:
    # Python 2 imports
    from urlparse import urlparse, parse_qs, urlunparse
    from urllib import urlencode

from django.contrib import messages
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import get_object_or_404

from google_analytics_reporter.utils import get_client_id
from squeezemail.models import Subscriber
from .tasks import process_click, process_open, process_unsubscribe


# def link_hash(request, link_hash):
#
#     #unencode link
#
#     link = request.build_absolute_uri()
#
#     return link_click(request, link)


def email_message_open(request):
    """
    Used by an img pixel embeded in every email.

    Returns a 204 No Content http response to save bandwidth.
    Thanks https://github.com/SpokesmanReview/Pixel-Tracker/blob/master/pixel_tracker/views.py
    """
    orig_params = {}
    sq_params = {}
    for key, value in request.GET.items():
        if key.startswith('sq_'):
            sq_params[key] = value
        else:
            orig_params[key] = value
    sq_params['sq_cid'] = get_client_id(request)
    sq_params['sq_timestamp'] = timezone.now().isoformat()
    process_open.delay(**sq_params)
    return HttpResponse(status=204)


def email_message_click(request):
    """
    Decodes the link hash, makes sure their token matches ours, make a new celery task to process stats, redirect to the link target
    """
    orig_params = {}
    sq_params = {}

    for key, value in request.GET.items():
        if key.startswith('sq_'):
            sq_params[key] = value
        else:
            orig_params[key] = value
    sq_params['sq_cid'] = get_client_id(request)
    sq_params['sq_timestamp'] = timezone.now().isoformat()
    # Send sq_params to task for further processing (stats, database operations for user, etc)
    process_click.delay(**sq_params)
    redirect_parsed_url = urlparse(sq_params['sq_target'])._replace(query=urlencode(orig_params))
    redirect_url = urlunparse(redirect_parsed_url)
    return HttpResponseRedirect(redirect_url)


def unsubscribe(request):
    subscriber_id = request.GET.get('sq_subscriber_id', None)
    email = request.GET.get('sq_email', None)
    token = request.GET.get('sq_token', None)
    subscriber = get_object_or_404(Subscriber, id=subscriber_id) if subscriber_id else get_object_or_404(Subscriber, email=email)
    if subscriber.match_token(token):
        subscriber.unsubscribe()  # unsubscribe right away so we don't anger them
        orig_params = {}
        sq_params = {}
        for key, value in request.GET.items():
            if key.startswith('sq_'):
                sq_params[key] = value
            else:
                orig_params[key] = value
        sq_params['sq_cid'] = get_client_id(request)
        sq_params['sq_timestamp'] = timezone.now().isoformat()
        messages.add_message(request, messages.SUCCESS, "<strong>Success!</strong><br>You've been successfully unsubscribed.")
        process_unsubscribe.delay(**sq_params)
    return HttpResponseRedirect('/')

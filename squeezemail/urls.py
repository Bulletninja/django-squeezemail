from django.conf.urls import patterns, url

from squeezemail.views import email_message_click, email_message_open, unsubscribe

urlpatterns = [
   url(r'^link/$', email_message_click, name='link'),
   #url(r'^link/(?P<link_hash>[a-z0-9]+)/$', 'squeezemail.views.link_hash', name='link_hash'),
   url(r'^pixel.png', email_message_open, name="tracking_pixel"),
   url(r'^unsubscribe/$', unsubscribe, name='unsubscribe'),
]

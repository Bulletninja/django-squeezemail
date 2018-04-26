from django.urls import re_path

from . import views

app_name = 'squeezemail'
urlpatterns = [
   re_path(r'^link/$', views.email_message_click, name='link'),
   re_path(r'^pixel.png', views.email_message_open, name="tracking_pixel"),
   re_path(r'^unsubscribe/$', views.unsubscribe, name='unsubscribe'),
]

import datetime
import re
import hashlib

import six

from django.db import models
from django.db.models.fields.related import (
    ForeignObjectRel, ManyToManyRel, ManyToOneRel, OneToOneRel, RelatedField
)
from django.core.mail import EmailMultiAlternatives, EmailMessage
from django.utils.module_loading import import_module
from django.conf import settings


basestring = (str, bytes)
unicode = str


def get_fields(Model,
               parent_field="",
               model_stack=None,
               stack_limit=3,
               excludes=['permissions', 'comment', 'content_type']):
    """
    Given a Model, return a list of lists of strings with important stuff:
    ...
    ['test_user__user__customuser', 'customuser', 'User', 'RelatedObject']
    ['test_user__unique_id', 'unique_id', 'TestUser', 'CharField']
    ['test_user__confirmed', 'confirmed', 'TestUser', 'BooleanField']
    ...

     """
    out_fields = []

    if model_stack is None:
        model_stack = []

    # github.com/omab/python-social-auth/commit/d8637cec02422374e4102231488481170dc51057
    if isinstance(Model, basestring):
        app_label, model_name = Model.split('.')
        Model = models.get_model(app_label, model_name)

    #fields = Model._meta.fields + Model._meta.many_to_many + tuple(Model._meta.get_all_related_objects())
    fields = Model._meta.get_fields()
    model_stack.append(Model)

    # do a variety of checks to ensure recursion isnt being redundant

    stop_recursion = False
    if len(model_stack) > stack_limit:
        # rudimentary CustomUser->User->CustomUser->User detection
        if model_stack[-3] == model_stack[-1]:
            stop_recursion = True

        # stack depth shouldn't exceed x
        if len(model_stack) > 5:
            stop_recursion = True

        # we've hit a point where we are repeating models
        if len(set(model_stack)) != len(model_stack):
            stop_recursion = True

    if stop_recursion:
        return [] # give empty list for "extend"

    for field in fields:
        field_name = field.name

        # if instance(field, Man)

        if isinstance(field, ForeignObjectRel):
            # from pdb import set_trace
            # set_trace()
            # print (field, type(field))
            field_name = field.field.related_query_name()

        if parent_field:
            full_field = "__".join([parent_field, field_name])
        else:
            full_field = field_name

        # print (field, field_name, full_field)

        if len([True for exclude in excludes if (exclude in full_field)]):
            continue

        # add to the list
        out_fields.append([full_field, field_name, Model, field.__class__])

        if not stop_recursion and \
                (isinstance(field, ForeignObjectRel) or isinstance(field, OneToOneRel) or isinstance(field, RelatedField) or isinstance(field, ManyToManyRel) or isinstance(field, ManyToOneRel)):

            # from pdb import set_trace
            # set_trace()

            if not isinstance(field, ForeignObjectRel):
                RelModel = field.model
                # print(RelModel)
            else:
                RelModel = field.related_model
                # print(RelModel)
            # if isinstance(field, OneToOneRel):
            #     print(field.related_model)
                # print(field.related_model)
            # print(RelModel)
            # if isinstance(field, OneToOneRel):
            #     RelModel = field.model
            #     out_fields.extend(get_fields(RelModel, full_field, True))
            # else:
            #     # RelModel = field.related.parent_model
            #     RelModel = field.related_model.parent_model

            out_fields.extend(get_fields(RelModel, full_field, list(model_stack)))

    return out_fields


def give_model_field(full_field, Model):
    """
    Given a field_name and Model:

    "test_user__unique_id", <AchievedGoal>

    Returns "test_user__unique_id", "id", <Model>, <ModelField>
    """
    field_data = get_fields(Model, '', [])

    for full_key, name, _Model, _ModelField in field_data:
        if full_key == full_field:
            return full_key, name, _Model, _ModelField

    raise Exception('Field key `{0}` not found on `{1}`.'.format(full_field, Model.__name__))


def get_simple_fields(Model, **kwargs):
    return [[f[0], f[3].__name__] for f in get_fields(Model, **kwargs)]


def chunked(iterator, chunksize):
    """
    Yields items from 'iterator' in chunks of size 'chunksize'.
    >>> list(chunked([1, 2, 3, 4, 5], chunksize=2))
    [(1, 2), (3, 4), (5,)]
    """
    chunk = []
    for idx, item in enumerate(iterator, 1):
        chunk.append(item)
        if idx % chunksize == 0:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


def email_to_dict(message):
    if isinstance(message, dict):
        return message

    message_dict = {'subject': message.subject,
                    'body': message.body,
                    'from_email': message.from_email,
                    'to': message.to,
                    # 'bcc': message.bcc,
                    # ignore connection
                    'attachments': message.attachments, #TODO: need attachments and headers passed correctly
                    'headers': message.extra_headers,
                    #'cc': message.cc
                    #'user_id': message.user.id,
                    #'drip_id': message.drip.id
                    }

    # Django 1.8 support
    # https://docs.djangoproject.com/en/1.8/topics/email/#django.core.mail.EmailMessage
    if hasattr(message, 'reply_to'):
        message_dict['reply_to'] = message.reply_to

    if hasattr(message, 'alternatives'):
        message_dict['alternatives'] = message.alternatives
    if message.content_subtype != EmailMessage.content_subtype:
        message_dict["content_subtype"] = message.content_subtype
    if message.mixed_subtype != EmailMessage.mixed_subtype:
        message_dict["mixed_subtype"] = message.mixed_subtype
    return message_dict


def dict_to_email(messagedict):
    if isinstance(messagedict, dict) and "content_subtype" in messagedict:
        content_subtype = messagedict["content_subtype"]
        del messagedict["content_subtype"]
    else:
        content_subtype = None
    if isinstance(messagedict, dict) and "mixed_subtype" in messagedict:
        mixed_subtype = messagedict["mixed_subtype"]
        del messagedict["mixed_subtype"]
    else:
        mixed_subtype = None
    if hasattr(messagedict, 'from_email'):
        ret = messagedict
    elif 'alternatives' in messagedict:
        ret = EmailMultiAlternatives(**messagedict)
    else:
        ret = EmailMessage(**messagedict)
    if content_subtype:
        ret.content_subtype = content_subtype
        messagedict["content_subtype"] = content_subtype  # bring back content subtype for 'retry'
    if mixed_subtype:
        ret.mixed_subtype = mixed_subtype
        messagedict["mixed_subtype"] = mixed_subtype  # bring back mixed subtype for 'retry'
    return ret


def class_for(path):
    mod_name, klass_name = path.rsplit('.', 1)
    mod = import_module(mod_name)
    klass = getattr(mod, klass_name)
    return klass


def get_token_for_email(email):
    return hashlib.md5(email.encode('utf-8') + settings.SECRET_KEY.encode('utf-8')).hexdigest()


def get_token_for_subscriber_id(subscriber_id):
    subscriber_id = str(subscriber_id)
    return hashlib.md5(subscriber_id.encode('utf-8') + settings.SECRET_KEY.encode('utf-8')).hexdigest()


def string_to_timedelta(string):
    """
    Parse a string into a timedelta object.

    >>> parse("1 day")
    datetime.timedelta(1)
    >>> parse("2 days")
    datetime.timedelta(2)
    >>> parse("1 d")
    datetime.timedelta(1)
    >>> parse("1 hour")
    datetime.timedelta(0, 3600)
    >>> parse("1 hours")
    datetime.timedelta(0, 3600)
    >>> parse("1 hr")
    datetime.timedelta(0, 3600)
    >>> parse("1 hrs")
    datetime.timedelta(0, 3600)
    >>> parse("1h")
    datetime.timedelta(0, 3600)
    >>> parse("1wk")
    datetime.timedelta(7)
    >>> parse("1 week")
    datetime.timedelta(7)
    >>> parse("1 weeks")
    datetime.timedelta(7)
    >>> parse("2 wks")
    datetime.timedelta(14)
    >>> parse("1 sec")
    datetime.timedelta(0, 1)
    >>> parse("1 secs")
    datetime.timedelta(0, 1)
    >>> parse("1 s")
    datetime.timedelta(0, 1)
    >>> parse("1 second")
    datetime.timedelta(0, 1)
    >>> parse("1 seconds")
    datetime.timedelta(0, 1)
    >>> parse("1 minute")
    datetime.timedelta(0, 60)
    >>> parse("1 min")
    datetime.timedelta(0, 60)
    >>> parse("1 m")
    datetime.timedelta(0, 60)
    >>> parse("1 minutes")
    datetime.timedelta(0, 60)
    >>> parse("1 mins")
    datetime.timedelta(0, 60)
    >>> parse("2 ws")
    Traceback (most recent call last):
    ...
    TypeError: '2 ws' is not a valid time interval
    >>> parse("2 ds")
    Traceback (most recent call last):
    ...
    TypeError: '2 ds' is not a valid time interval
    >>> parse("2 hs")
    Traceback (most recent call last):
    ...
    TypeError: '2 hs' is not a valid time interval
    >>> parse("2 ms")
    Traceback (most recent call last):
    ...
    TypeError: '2 ms' is not a valid time interval
    >>> parse("2 ss")
    Traceback (most recent call last):
    ...
    TypeError: '2 ss' is not a valid time interval
    >>> parse("")
    Traceback (most recent call last):
    ...
    TypeError: '' is not a valid time interval
    >>> parse("1.5 days")
    datetime.timedelta(1, 43200)
    >>> parse("3 weeks")
    datetime.timedelta(21)
    >>> parse("4.2 hours")
    datetime.timedelta(0, 15120)
    >>> parse(".5 hours")
    datetime.timedelta(0, 1800)
    >>> parse(" hours")
    Traceback (most recent call last):
        ...
    TypeError: 'hours' is not a valid time interval
    >>> parse("1 hour, 5 mins")
    datetime.timedelta(0, 3900)

    >>> parse("-2 days")
    datetime.timedelta(-2)
    >>> parse("-1 day 0:00:01")
    datetime.timedelta(-1, 1)
    >>> parse("-1 day, -1:01:01")
    datetime.timedelta(-2, 82739)
    >>> parse("-1 weeks, 2 days, -3 hours, 4 minutes, -5 seconds")
    datetime.timedelta(-5, 11045)

    >>> parse("0 seconds")
    datetime.timedelta(0)
    >>> parse("0 days")
    datetime.timedelta(0)
    >>> parse("0 weeks")
    datetime.timedelta(0)

    >>> zero = datetime.timedelta(0)
    >>> parse(nice_repr(zero))
    datetime.timedelta(0)
    >>> parse(nice_repr(zero, 'minimal'))
    datetime.timedelta(0)
    >>> parse(nice_repr(zero, 'short'))
    datetime.timedelta(0)
    >>> parse('  50 days 00:00:00   ')
    datetime.timedelta(50)
    """
    string = string.strip()

    if string == "":
        raise TypeError("'%s' is not a valid time interval" % string)
    # This is the format we get from sometimes Postgres, sqlite,
    # and from serialization
    d = re.match(r'^((?P<days>[-+]?\d+) days?,? )?(?P<sign>[-+]?)(?P<hours>\d+):'
                 r'(?P<minutes>\d+)(:(?P<seconds>\d+(\.\d+)?))?$',
                 six.text_type(string))
    if d:
        d = d.groupdict(0)
        if d['sign'] == '-':
            for k in 'hours', 'minutes', 'seconds':
                d[k] = '-' + d[k]
        d.pop('sign', None)
    else:
        # This is the more flexible format
        d = re.match(
                     r'^((?P<weeks>-?((\d*\.\d+)|\d+))\W*w((ee)?(k(s)?)?)(,)?\W*)?'
                     r'((?P<days>-?((\d*\.\d+)|\d+))\W*d(ay(s)?)?(,)?\W*)?'
                     r'((?P<hours>-?((\d*\.\d+)|\d+))\W*h(ou)?(r(s)?)?(,)?\W*)?'
                     r'((?P<minutes>-?((\d*\.\d+)|\d+))\W*m(in(ute)?(s)?)?(,)?\W*)?'
                     r'((?P<seconds>-?((\d*\.\d+)|\d+))\W*s(ec(ond)?(s)?)?)?\W*$',
                     six.text_type(string))
        if not d:
            raise TypeError("'%s' is not a valid time interval" % string)
        d = d.groupdict(0)

    return datetime.timedelta(**dict(( (k, float(v)) for k,v in d.items())))

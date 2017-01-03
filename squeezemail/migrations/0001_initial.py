# -*- coding: utf-8 -*-
# Generated by Django 1.9.9 on 2016-12-08 18:43
from __future__ import unicode_literals

import datetime
from django.conf import settings
import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.db.models.deletion
import django.db.models.manager
import django.utils.timezone
import gfklookupwidget.fields
import mptt.fields
import squeezemail.plugins.richtext


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='ActionDrip',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('region', models.CharField(max_length=255)),
                ('ordering', models.IntegerField(default=0)),
            ],
            options={
                'verbose_name': 'Send A Drip',
            },
        ),
        migrations.CreateModel(
            name='ActionModification',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('region', models.CharField(max_length=255)),
                ('ordering', models.IntegerField(default=0)),
                ('modify_type', models.CharField(choices=[('add', 'Add'), ('move', 'Move'), ('remove', 'Remove')], max_length=75)),
                ('object_id', gfklookupwidget.fields.GfkLookupField()),
                ('content_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='contenttypes.ContentType')),
            ],
            options={
                'verbose_name': 'Subscriber Modification',
                'verbose_name_plural': 'Subscriber Modifications',
            },
        ),
        migrations.CreateModel(
            name='Drip',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='A unique name for this drip.', max_length=255, unique=True, verbose_name='Drip Name')),
                ('enabled', models.BooleanField(default=False)),
                ('note', models.TextField(blank=True, help_text='This is only seen by staff.', max_length=255, null=True)),
                ('from_email', models.EmailField(blank=True, help_text='Set a custom from email.', max_length=254, null=True)),
                ('from_email_name', models.CharField(blank=True, help_text='Set a name for a custom from email.', max_length=150, null=True)),
                ('message_class', models.CharField(blank=True, default='default', max_length=120)),
                ('date', models.DateTimeField(auto_now_add=True)),
                ('lastchanged', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='DripSubject',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.CharField(max_length=150)),
                ('enabled', models.BooleanField(default=True)),
                ('drip', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='subjects', to='squeezemail.Drip')),
            ],
        ),
        migrations.CreateModel(
            name='EmailActivity',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.CharField(choices=[('open', 'Opened'), ('click', 'Clicked'), ('spam', 'Reported Spam'), ('unsubscribe', 'Unsubscribed'), ('sent', 'Was Sent')], max_length=75)),
                ('drip', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='email_activity+', to='squeezemail.Drip')),
            ],
        ),
        migrations.CreateModel(
            name='Event',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateTimeField(auto_now_add=True)),
                ('object_id', gfklookupwidget.fields.GfkLookupField()),
                ('data', django.contrib.postgres.fields.jsonb.JSONField()),
                ('content_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='contenttypes.ContentType')),
            ],
        ),
        migrations.CreateModel(
            name='Funnel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=75)),
            ],
        ),
        migrations.CreateModel(
            name='QuerySetRule',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('region', models.CharField(max_length=255)),
                ('ordering', models.IntegerField(default=0)),
                ('method_type', models.CharField(choices=[('filter', 'Filter'), ('exclude', 'Exclude')], default='filter', max_length=12)),
                ('field_name', models.CharField(max_length=128, verbose_name='Field name of Subscriber')),
                ('lookup_type', models.CharField(choices=[('exact', 'exactly'), ('iexact', 'exactly (case insensitive)'), ('contains', 'contains'), ('icontains', 'contains (case insensitive)'), ('regex', 'regex'), ('iregex', 'regex (case insensitive)'), ('gt', 'greater than'), ('gte', 'greater than or equal to'), ('lt', 'less than'), ('lte', 'less than or equal to'), ('startswith', 'starts with'), ('endswith', 'ends with'), ('istartswith', 'starts with (case insensitive)'), ('iendswith', 'ends with (case insensitive)'), ('isnull', 'isnull (boolean)')], default='exact', max_length=12)),
                ('field_value', models.CharField(help_text='Can be anything from a number, to a string. Or, do `now-7 days` or `today+3 days` for fancy timedelta.', max_length=255)),
                ('drip', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='queryset_rules', to='squeezemail.Drip')),
            ],
            options={
                'ordering': ['ordering'],
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='RichText',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', squeezemail.plugins.richtext.CleansedRichTextField(verbose_name='text')),
                ('region', models.CharField(max_length=255)),
                ('ordering', models.IntegerField(default=0)),
                ('parent', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='squeezemail_richtext_set', to='squeezemail.Drip')),
            ],
            options={
                'verbose_name': 'rich text',
                'verbose_name_plural': 'rich texts',
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='SendDrip',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateTimeField(auto_now_add=True)),
                ('sent', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='Step',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('description', models.CharField(blank=True, max_length=75, null=True)),
                ('is_active', models.BooleanField(default=True, help_text="If not active, subscribers will still be allowed to move to this step, but this step won't run until it's active. Consider this a good way to 'hold' subscribers on this step. Note: Step children will still run.", verbose_name='Active')),
                ('delay', models.DurationField(default=datetime.timedelta(1), help_text="How long should the subscriber sit on this step before it runs for them? The preferred format for durations in Django is '%d %H:%M:%S.%f (e.g. 3 00:40:00 for 3 day, 40 minute delay)'")),
                ('priority', models.IntegerField(choices=[(0, 'No Priority'), (1, '[1] Priority'), (2, '[2] Priority'), (3, '[3] Priority'), (4, '[4] Priority'), (5, '[5] Priority')], default=0, help_text='To help avoid sending multiple emails to the same subscriber. Higher priority will run first.')),
                ('processed', models.IntegerField(default=0)),
                ('lft', models.PositiveIntegerField(db_index=True, editable=False)),
                ('rght', models.PositiveIntegerField(db_index=True, editable=False)),
                ('tree_id', models.PositiveIntegerField(db_index=True, editable=False)),
                ('level', models.PositiveIntegerField(db_index=True, editable=False)),
                ('failed', models.ForeignKey(blank=True, help_text="Useful if you use any type of action that removes subscribers from the original queryset (e.g. a 'Queryset Rule'). If nothing is specified here, any excluded subscribers will just move to this step's first child (if relevant).", null=True, on_delete=django.db.models.deletion.CASCADE, related_name='failed+', to='squeezemail.Step')),
                ('parent', mptt.fields.TreeForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='children', to='squeezemail.Step')),
                ('passed', models.ForeignKey(blank=True, help_text="If the subscriber passes through <b>all</b> of the actions, you can optionally direct them to a specific step. This is useful if using a 'Queryset Rule' or 'Email Activity' action and you want to send any filtered/true users to a specific step. If nothing is specified here, any truthy subscribers will just move to this step's first child (if relevant).", null=True, on_delete=django.db.models.deletion.CASCADE, related_name='passed+', to='squeezemail.Step')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Subscriber',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email', models.EmailField(db_index=True, max_length=254, unique=True)),
                ('is_active', models.BooleanField(default=True, verbose_name='Active')),
                ('created', models.DateTimeField(default=django.utils.timezone.now)),
                ('idle', models.BooleanField(default=False)),
            ],
            managers=[
                ('default_manager', django.db.models.manager.Manager()),
            ],
        ),
        migrations.CreateModel(
            name='Subscription',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Subscribe Date')),
                ('is_active', models.BooleanField(default=True, verbose_name='Active')),
                ('step_timestamp', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Last Step Activity Timestamp')),
                ('funnel', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='subscriptions', to='squeezemail.Funnel')),
                ('step', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='subscriptions', to='squeezemail.Step')),
                ('subscriber', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='subscriptions', to='squeezemail.Subscriber')),
            ],
        ),
        migrations.CreateModel(
            name='Tag',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('slug', models.SlugField(max_length=100, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='Click',
            fields=[
                ('senddrip', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to='squeezemail.SendDrip')),
                ('date', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='Open',
            fields=[
                ('senddrip', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to='squeezemail.SendDrip')),
                ('date', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='Spam',
            fields=[
                ('senddrip', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to='squeezemail.SendDrip')),
                ('date', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='Unsubscribe',
            fields=[
                ('senddrip', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to='squeezemail.SendDrip')),
                ('date', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.AddField(
            model_name='subscriber',
            name='tags',
            field=models.ManyToManyField(blank=True, null=True, related_name='subscribers', to='squeezemail.Tag'),
        ),
        migrations.AddField(
            model_name='subscriber',
            name='user',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='squeeze_subscriber', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='step',
            name='subscribers',
            field=models.ManyToManyField(related_name='current_steps', through='squeezemail.Subscription', to='squeezemail.Subscriber'),
        ),
        migrations.AddField(
            model_name='senddrip',
            name='drip',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='send_drips', to='squeezemail.Drip'),
        ),
        migrations.AddField(
            model_name='senddrip',
            name='subscriber',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='send_drips', to='squeezemail.Subscriber'),
        ),
        migrations.AddField(
            model_name='querysetrule',
            name='parent',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='squeezemail_querysetrule_set', to='squeezemail.Step'),
        ),
        migrations.AddField(
            model_name='funnel',
            name='entry_step',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='funnels', to='squeezemail.Step'),
        ),
        migrations.AddField(
            model_name='funnel',
            name='subscribers',
            field=models.ManyToManyField(related_name='funnels', through='squeezemail.Subscription', to='squeezemail.Subscriber'),
        ),
        migrations.AddField(
            model_name='actionmodification',
            name='parent',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='squeezemail_actionmodification_set', to='squeezemail.Step'),
        ),
        migrations.AddField(
            model_name='actiondrip',
            name='drip',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='actions+', to='squeezemail.Drip'),
        ),
        migrations.AddField(
            model_name='actiondrip',
            name='parent',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='squeezemail_actiondrip_set', to='squeezemail.Step'),
        ),
        migrations.AlterUniqueTogether(
            name='subscription',
            unique_together=set([('funnel', 'subscriber')]),
        ),
        migrations.AlterUniqueTogether(
            name='senddrip',
            unique_together=set([('drip', 'subscriber')]),
        ),
    ]

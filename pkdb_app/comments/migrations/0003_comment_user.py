# Generated by Django 2.0.6 on 2018-08-08 10:44

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('comments', '0002_auto_20180808_1044'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='comment',
            name='user',
            field=models.ForeignKey(on_delete=False, related_name='comments', to=settings.AUTH_USER_MODEL),
        ),
    ]

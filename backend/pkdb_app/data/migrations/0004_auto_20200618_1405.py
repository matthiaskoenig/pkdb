# Generated by Django 3.0.7 on 2020-06-18 14:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('data', '0003_auto_20200616_1313'),
    ]

    operations = [
        migrations.AlterField(
            model_name='data',
            name='data_type',
            field=models.CharField(choices=[('scatter', 'scatter'), ('timecourse', 'timecourse')], max_length=200),
        ),
    ]

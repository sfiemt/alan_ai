# Generated by Django 4.2.10 on 2024-03-21 00:01

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('datasources', '0004_alter_userfiles_user'),
    ]

    operations = [
        migrations.DeleteModel(
            name='UserFiles',
        ),
    ]

# Generated by Django 5.1.7 on 2025-05-29 13:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0014_alter_userlesson_practice_window_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='lesson',
            name='description',
            field=models.TextField(blank=True, help_text='Brief description of the lesson.'),
        ),
    ]

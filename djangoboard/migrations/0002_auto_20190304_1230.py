# Generated by Django 2.1.7 on 2019-03-04 12:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('djangoboard', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='board',
            name='short_description',
            field=models.CharField(blank=True, max_length=20),
        ),
    ]

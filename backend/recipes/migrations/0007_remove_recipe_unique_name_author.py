# Generated by Django 4.1.4 on 2023-07-04 21:00

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('recipes', '0006_alter_ingredientamount_ingredient'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='recipe',
            name='unique_name_author',
        ),
    ]

import csv

from django.core.management.base import BaseCommand

from recipes.models import Ingredient


class Command(BaseCommand):
    """ Заполняет таблицу ингредиентов. """

    def handle(self, *args, **options):
        with open('../data/ingredients.csv', 'r') as file:
            reader = csv.reader(file)
            data = []
            for row in reader:
                data.append(Ingredient(
                    name=row[0],
                    measurement_unit=row[1],
                ))
            Ingredient.objects.bulk_create(data)

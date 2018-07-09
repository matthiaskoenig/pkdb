"""
the managers can be used to overwrite class methods of the models module.
"""
from django.db import models


class GroupManager(models.Manager):
    def update_or_create(self, *args, **kwargs):
        characteristic_values = kwargs["defaults"].pop("characteristic_values", [])
        group, created = super(GroupManager, self).update_or_create(*args, **kwargs)
        group.characteristic_values.all().delete()
        for characteristic_value in characteristic_values:
            group.characteristic_values.create(**characteristic_value)

        group.save()


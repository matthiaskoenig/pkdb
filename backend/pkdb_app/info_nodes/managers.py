from django.apps import apps
from django.db import models
from pkdb_app.utils import update_or_create_multiple


class InfoNodeManager(models.Manager):
    def update_or_create(self, *args, **kwargs):

        annotations = kwargs.pop('annotations', [])
        parents = kwargs.pop('parents', [])
        synonyms = kwargs.pop('synonyms', [])
        ntype = kwargs.get('ntype')
        extra_fields = kwargs.get(ntype,{})

        NOTE_TYPES = {
            "measurement_types": "MeasurementType",
            "substances": "Substance",
            "routes": "Route",
            "forms": "Form",
            "applications": "Application",
            "tissues": "Tissue",
            "choices": "Choice",
        }

        Model = apps.get_model('info_nodes', NOTE_TYPES[ntype])

        instance = super().create(*args, **kwargs)

        update_or_create_multiple(instance, annotations, 'annotations', lookup_fields=["term", "relation"])
        update_or_create_multiple(instance, synonyms, 'synonyms', lookup_fields=["name"])
        instance.parents.add(*parents)

        units = extra_fields.pop('units',[])

        specific_instance = Model.object.create(info_node=instance, **extra_fields)
        update_or_create_multiple(specific_instance, units, 'units', lookup_fields=["name"])







        instance.save()
        return instance
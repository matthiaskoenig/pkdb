"""Managers which override class methods of the models module."""

from django.db import models

from ..utils import _create


class OutputManager(models.Manager):
    """Manager for `Output` which creates instances and attaches their interventions."""

    def create(self, *args, **kwargs):
        """Create the output and add the interventions passed in `kwargs`."""
        output, _ = _create(
            model_manager=super(),
            validated_data=kwargs,
            add_multiple_keys=["interventions"],
        )
        return output

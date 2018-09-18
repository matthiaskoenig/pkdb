from django.contrib import admin

# Register your models here.
from pkdb_app.interventions.models import InterventionSet, Intervention, Substance


@admin.register(Intervention)
class InterventionAdmin(admin.ModelAdmin):
    pass


@admin.register(InterventionSet)
class InterventionSetAdmin(admin.ModelAdmin):
    pass


@admin.register(Substance)
class SubstanceAdmin(admin.ModelAdmin):
    pass

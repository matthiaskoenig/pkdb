from django.contrib import admin

from pkdb_app.interventions.models import Substance


@admin.register(Substance)
class SubstanceAdmin(admin.ModelAdmin):
    fields = ('pk', 'name',)
    list_display = ('pk', 'name',)
    # list_filter = ('name',)
    search_fields = ('name',)

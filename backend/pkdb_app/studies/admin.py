from django.contrib import admin
from pkdb_app.studies.models import Study, Reference


@admin.register(Reference)
class ReferenceAdmin(admin.ModelAdmin):
    fields = ('pk', 'pmid', 'sid', 'name', 'doi', 'title', 'journal', 'date', 'pdf')
    list_display = ('pk', 'pmid', 'sid', 'name', 'doi', 'title', 'journal', 'date', 'pdf')


@admin.register(Study)
class StudyAdmin(admin.ModelAdmin):
    fields = ('pk', 'pkdb_version', 'name', 'creator', 'reference',)
    list_display = ('pk', 'pkdb_version', 'name', 'creator', 'reference',)

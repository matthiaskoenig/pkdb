from django.contrib import admin
from pkdb_app.studies.models import Study, Keyword, Reference


@admin.register(Keyword)
class KeywordAdmin(admin.ModelAdmin):
    fields = ('pk', 'name',)
    list_display = ('pk', 'name',)
    # list_filter = ('name',)
    search_fields = ('name',)


@admin.register(Reference)
class ReferenceAdmin(admin.ModelAdmin):
    fields = ('pk', 'pmid', 'sid', 'name', 'doi', 'title', 'journal', 'date', 'pdf')
    list_display = ('pk', 'pmid', 'sid', 'name', 'doi', 'title', 'journal', 'date', 'pdf')


@admin.register(Study)
class StudyAdmin(admin.ModelAdmin):
    fields = ('pk', 'pkdb_version', 'name', 'creator', 'design', 'reference',)
    list_display = ('pk', 'pkdb_version', 'name', 'creator', 'design', 'reference',)

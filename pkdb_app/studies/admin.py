from django.contrib import admin


# Register your models here.
from pkdb_app.studies.models import Study


@admin.register(Study)
class StudyAdmin(admin.ModelAdmin):
    pass

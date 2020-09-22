"""
Views
"""
import os

from django.http import  FileResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404
from rest_framework.authentication import TokenAuthentication
from pkdb_app.users.permissions import get_study_file_permission
from .subjects.models import DataFile

from drf_yasg.generators import OpenAPISchemaGenerator


def serve_protected_document(request, file):
    try:
        user, _ = TokenAuthentication().authenticate(request=request)
    except TypeError:
        user = request.user

    path, file_name = os.path.split(file)
    datafile = get_object_or_404(DataFile, file=file)
    study = datafile.study_set.all()[0]
    if get_study_file_permission(user, study):
        # Split the elements of the path
        response = FileResponse(datafile.file, )
        response["Content-Disposition"] = "attachment; filename=" + file_name

        return response

    else:
        return HttpResponseForbidden()


class CustomOpenAPISchemaGenerator(OpenAPISchemaGenerator):
    def get_schema(self, request=None, public=False):
        """Generate a :class:`.Swagger` object with custom tags"""

        swagger = super().get_schema(request, public)
        swagger.tags = [
            {
                "name": "flat",
                "description": "Under 'flat' all endpoints are grouped which have a flat representation "
                               "of the data."
            }

        ]

        return swagger
"""
Views
"""
import os
from copy import copy

from django.http import FileResponse, HttpResponseForbidden
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

    return HttpResponseForbidden()


class CustomOpenAPISchemaGenerator(OpenAPISchemaGenerator):
    """Definition of additional API parameters."""

    @staticmethod
    def _params(table, swagger):
        if swagger.paths.get(f'/{table}/'):
            _params = []
            params = swagger.paths.get(f'/{table}/').get('get').get("parameters").copy()

            for p in params:
                _p = copy(p)
                if p.name not in ["ordering", "search_multi_match", "page", "page_size"]:
                    if table not in p.name:
                        _p.name = f'{table}__{p.name}'
                        _params.append(_p)
            return _params

    def get_schema(self, request=None, public=False):
        """Generate a :class:`.Swagger` object with custom tags"""

        swagger = super().get_schema(request, public)
        swagger.tags = [
            {
                "name": "filter",
                "description": "Filter and search queries (corresponds to search in web interface)"
            },
            {
                "name": "groups",
                "description": "Query groups"
            },
            {
                "name": "individuals",
                "description": "Query individual subjects"
            },
            {
                "name": "info_nodes",
                "description": "Query info nodes"
            },
            {
                "name": "outputs",
                "description": "Query outputs"
            },
            {
                "name": "statistics",
                "description": "Query PK-DB statistics"
            },
            {
                "name": "studies",
                "description": "Query studies"
            },
            {
                "name": "interventions",
                "description": "Query interventions"
            },
            {
                "name": "subsets",
                "description": "Query subsets (timecourses and scatters)"
            },

        ]

        for table in ["studies", "individuals", "groups", "interventions", "outputs", "subsets"]:
            if self._params(table, swagger):
                swagger.paths.get('/filter/').get('get')["parameters"] += self._params(table, swagger)

        return swagger

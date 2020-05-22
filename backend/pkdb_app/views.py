"""
Views
"""
import os

from django.http import  FileResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404
from rest_framework.authentication import TokenAuthentication
from pkdb_app.users.permissions import get_study_file_permission
from .subjects.models import DataFile


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

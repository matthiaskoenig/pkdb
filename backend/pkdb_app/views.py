"""
Views
"""
import os
from django.http import HttpResponse, FileResponse,HttpResponseForbidden
from django.shortcuts import render, get_object_or_404
from django.core.exceptions import ObjectDoesNotExist

from .categoricals import OPEN
from .studies.models import Reference
from .subjects.models import DataFile


def test_view(request):
    return render(request, "test.html", {"version": 1})


def test_500_view(request):
    # Return an "Internal Server Error" 500 response code.
    return HttpResponse(status=500)


from rest_framework_swagger.renderers import SwaggerUIRenderer, OpenAPIRenderer
from rest_framework.decorators import (
    api_view,
    renderer_classes,
    authentication_classes,
    permission_classes,
)
from rest_framework.renderers import CoreJSONRenderer
from rest_framework.schemas import SchemaGenerator
from rest_framework.authentication import (
    SessionAuthentication,
    TokenAuthentication,
    BasicAuthentication,
)
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

@api_view()
@renderer_classes([SwaggerUIRenderer, OpenAPIRenderer, CoreJSONRenderer])
@authentication_classes((SessionAuthentication, BasicAuthentication))
@permission_classes((AllowAny,))
def schema_view(request):
    generator = SchemaGenerator(title="PKDB Web API")
    return Response(generator.get_schema(request=request))

class CreateListModelMixin(object):
    def get_serializer(self, *args, **kwargs):
        """ if an array is passed, set serializer to many """
        if isinstance(kwargs.get('data', {}), list):
            kwargs['many'] = True
            return super(CreateListModelMixin, self).get_serializer(*args, **kwargs)
        #elif kwargs.get('many', False):
        #   new_kwargs['many'] = True
        #    new_kwargs['data'] = kwargs["data"].get("files")
        #    return super(CreateListModelMixin, self).get_serializer(*args, **new_kwargs)


def serve_protected_document(request, file):
    path, file_name = os.path.split(file)
    user = request.user



    try:
        ref = Reference.objects.get(pdf=file)
        if user.is_staff:
            # Split the elements of the path
            response = FileResponse(ref.pdf, )
            response["Content-Disposition"] = "attachment; filename=" + file_name
            return response
        else:

            return HttpResponseForbidden()


    except Reference.DoesNotExist:
        datafile = get_object_or_404(DataFile, file=file)
        study = datafile.study_set.all()[0]
        is_curator = user in study.curators.all()
        is_creator = user == study.creator
        is_open = study.licence == OPEN

        requirements = [is_curator,is_creator,is_open,user.is_staff ]

        if any(requirements):
            # Split the elements of the path
            response = FileResponse(datafile.file,)
            response["Content-Disposition"] = "attachment; filename=" + file_name

            return response

        else:
            return HttpResponseForbidden()

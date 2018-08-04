"""
Views
"""

from django.shortcuts import render
from rest_framework_swagger.renderers import SwaggerUIRenderer,OpenAPIRenderer
from rest_framework.decorators import api_view,renderer_classes,authentication_classes,permission_classes
from rest_framework.renderers import CoreJSONRenderer
from rest_framework.schemas import SchemaGenerator
from rest_framework.authentication import SessionAuthentication, TokenAuthentication, BasicAuthentication
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view()
@renderer_classes([SwaggerUIRenderer, OpenAPIRenderer, CoreJSONRenderer])
@authentication_classes((SessionAuthentication, BasicAuthentication))
@permission_classes((AllowAny,))
def schema_view(request):
    generator = SchemaGenerator(
        title='PKDB Web API')
    return Response(generator.get_schema(request=request))

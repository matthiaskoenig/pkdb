"""
Views
"""
from django.http import HttpResponse
from django.shortcuts import render


# for debugging of templates
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


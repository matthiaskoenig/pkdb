from collections import OrderedDict

from drf_yasg import openapi
from drf_yasg.inspectors import DjangoRestResponsePagination
from rest_framework.pagination import LimitOffsetPagination, PageNumberPagination, CursorPagination
class ResponsePagination(DjangoRestResponsePagination):
    """Provides response schema pagination warpping for django-rest-framework's LimitOffsetPagination,
    PageNumberPagination and CursorPagination
    """

    def get_paginated_response(self, paginator, response_schema):
        assert response_schema.type == openapi.TYPE_ARRAY, "array return expected for paged response"
        paged_schema = None
        if isinstance(paginator, (LimitOffsetPagination, PageNumberPagination, CursorPagination)):
            has_count = not isinstance(paginator, CursorPagination)
            paged_schema = openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties=OrderedDict((
                    ('current_page', openapi.Schema(type=openapi.TYPE_INTEGER)),
                    ('last_page', openapi.Schema(type=openapi.TYPE_INTEGER)),
                    ('next_page_url', openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_URI, x_nullable=True)),
                    ('prev_page_url', openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_URI, x_nullable=True)),
                    ('data',  openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties=OrderedDict((
                            ('count', openapi.Schema(type=openapi.TYPE_INTEGER) if has_count else None),
                            ('data', response_schema))),
                        required=['data']))
                    )),
                required=['data']
            )

        return paged_schema
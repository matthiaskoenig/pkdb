"""Pagination response format shared by the API list views."""

from typing import TYPE_CHECKING

from rest_framework import pagination
from rest_framework.response import Response

if TYPE_CHECKING:
    from django.core.paginator import Page


class CustomPagination(pagination.PageNumberPagination):
    """Page number pagination which nests the page data under a ``data`` key."""

    page_size_query_param = "page_size"

    if TYPE_CHECKING:
        # paginate_queryset sets the page before the response is built
        page: "Page"

    def get_paginated_response(self, data):
        """Return the paginated response with page metadata and the count."""
        return Response(
            {
                "current_page": self.page.number,
                "last_page": self.page.paginator.num_pages,
                "next_page_url": self.get_next_link(),
                "prev_page_url": self.get_previous_link(),
                "data": {"count": self.page.paginator.count, "data": data},
            }
        )

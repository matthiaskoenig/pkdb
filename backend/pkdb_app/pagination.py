"""Pagination response format shared by the API list views."""

from rest_framework import pagination
from rest_framework.response import Response


class CustomPagination(pagination.PageNumberPagination):
    """Page number pagination which nests the page data under a ``data`` key."""

    page_size_query_param = "page_size"

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

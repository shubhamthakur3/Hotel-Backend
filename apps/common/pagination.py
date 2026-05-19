"""
Custom pagination classes for the Hotel Backend API.
"""

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardResultsPagination(PageNumberPagination):
    """
    Standard page-based pagination with configurable page size.

    Query parameters:
        - page: Page number (default: 1)
        - page_size: Items per page (default: 20, max: 100)
    """

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response(
            {
                "pagination": {
                    "count": self.page.paginator.count,
                    "total_pages": self.page.paginator.num_pages,
                    "current_page": self.page.number,
                    "page_size": self.get_page_size(self.request),
                    "next": self.get_next_link(),
                    "previous": self.get_previous_link(),
                },
                "results": data,
            }
        )


class SmallResultsPagination(PageNumberPagination):
    """Smaller page size for nested/related resources."""

    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 50

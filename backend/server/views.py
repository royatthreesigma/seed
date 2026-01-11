from typing import Any
from rest_framework.request import Request
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


class AnonymousUserHealthCheckViewSet(APIView):
    # GET /health/
    def get(self, request: Request) -> Response:
        return Response(
            {"status": "Unauthenticated api health check passed!"},
            status=status.HTTP_200_OK,
        )


class AuthenticatedUserHealthCheckView(APIView):
    # GET /authenticated-health/
    def get(self, request: Request) -> Response:
        return Response(
            {"status": "Authenticated api health check failed: not implemented!"},
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )

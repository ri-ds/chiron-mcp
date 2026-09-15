from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from importlib.metadata import version


class VersionViewSet(viewsets.GenericViewSet):
    """
    API endpoint for reporting version of Chiron being run
    """

    permission_classes = [AllowAny]

    def list(self, request):
        try:
            return Response({"chiron": version("chiron")})
        except Exception:
            return Response({"chiron": "Unknown"})

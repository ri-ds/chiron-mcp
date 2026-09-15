from importlib.metadata import version as get_version

from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from chiron.api_v2.serializers import AuthSerializer


class AuthViewSetV2(viewsets.ViewSet):
    """
    API endpoint that shows the logged in users' information, the dataset information,
    and the Chiron version being used
    """

    permission_classes = [AllowAny]

    def list(self, request):
        try:
            version = "v" + get_version("chiron")
        except Exception:
            version = "v0.0.0"

        user = request.user
        if not user.is_authenticated:
            return Response({"user": None, "chironVersion": version})

        serializer = AuthSerializer(
            {
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "isStaff": user.is_staff,
                    "name": user.get_full_name(),
                    "email": user.email,
                },
                "chironVersion": version,
            }
        )

        return Response(serializer.data)

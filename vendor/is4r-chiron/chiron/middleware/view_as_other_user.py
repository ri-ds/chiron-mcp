from django.contrib.auth.middleware import RemoteUserMiddleware
from django.contrib.auth import get_user_model


class ViewAsOtherUser(RemoteUserMiddleware):
    """
    This class checks the session for override_user_id, and if set will
    set that user as the request.user. Also adds a flag to the request
    request.viewing_as_user
    Depends on these middleware classes and needs to be run after them:
    - django.contrib.sessions.middleware.SessionMiddleware
    - django.contrib.auth.middleware.AuthenticationMiddleware
    """

    def process_request(self, request):
        request.view_as_other_user_middleware_installed = True
        override_user_id = request.session.get("override_user_id", None)
        if override_user_id:
            User = get_user_model()
            oUser = User.objects.filter(id=override_user_id).first()
            if oUser:
                request.user = oUser
                request.viewing_as_other_user = oUser.username
        return None

# Custom Authentication Classes for Chiron API

from rest_framework.authentication import SessionAuthentication


class CsrfExemptSessionAuthentication(SessionAuthentication):
    """
    Session Authentication without CSRF Token Check.
    """

    # TODO: Check whether this is a security risk for this use-case and/or threat model.
    def enforce_csrf(self, request):
        """Empty CSRF Check function"""
        return

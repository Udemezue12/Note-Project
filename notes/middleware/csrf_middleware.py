
import secrets
from rest_framework.response import Response as JsonResponse
from rest_framework.request import HttpRequest

SAFE_METHODS = ("GET", "HEAD", "OPTIONS")


class CustomCSRFMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request:HttpRequest):
       
        if request.method in SAFE_METHODS:
            return self.get_response(request)

        
        cookie_token = request.COOKIES.get("csrfToken")
        header_token = request.headers.get("X-CSRFToken")

        if not cookie_token or not header_token:
            return JsonResponse(
                {"detail": "CSRF token missing"},
                status=403
            )

       
        if not secrets.compare_digest(cookie_token, header_token):
            return JsonResponse(
                {"detail": "Invalid CSRF token"},
                status=403
            )

        return self.get_response(request)
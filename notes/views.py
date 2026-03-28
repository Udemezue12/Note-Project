import secrets

from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .env import ENV


@api_view()
def get_csrf_token(request):
    token = secrets.token_urlsafe(32)

    response = Response({"detail": "CSRF cookie set", "csrf_token": token})
    if ENV == " production":
        response.set_cookie(
            key="csrfToken",
            value=token,
            httponly=False,
            secure=True,  
            samesite="Lax",
            max_age=60 * 60 * 24,
        )

        return response
    else:
        response.set_cookie(
            key="csrfToken",
            value=token,
            httponly=False,
            secure=False, 
            samesite="Lax",
            max_age=60 * 60 * 24,
        )
def index(request):
    return render(request,"base.html")
def dashboard(request):
    return render(request, "dashboard.html")
def login_view(request):
    return render(request, "login.html")
def register_view(request):
    return render (request, "register.html")
def forgot_password_view(request):
    return render (request, "forgot_password.html")
def reset_password_view(request):
    return render(request, "reset_password.html" )
def note_view(request):
    return render(request, "note_partials.html")
def verify_email_view(request):
    return render(request, "verify_email.html")
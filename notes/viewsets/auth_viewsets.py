from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.utils.timezone import now
from rest_framework import status, viewsets
from rest_framework.decorators import action, permission_classes
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import HttpRequest
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework_simplejwt.tokens import RefreshToken

from note_app.celery_app import app as task_app

from ..auth_utils import blacklist_token
from ..crud_deps import crud_actions
from ..env import ENV
from ..serializers.auth_serializers import (
    ForgotPasswordSerializer,
    LoginSerializer,
    RegisterSerializer,
    ResetPasswordSerializer,
    VerifyEmailSerializer,
)
from ..user_generate import user_generate
from ..user_verification import user_verify
from ..webscokets.note_websocket_update import send_force_logout

User = get_user_model()


class AuthViewSet(viewsets.ViewSet):
    def list(self, request):
        return Response(
            {
                "Authentication": {
                    "register": reverse("auth-register", request=request),
                    "login": reverse("auth-login", request=request),
                    "logout": reverse("auth-logout", request=request),
                    "refresh": reverse("auth-refresh", request=request),
                    "verify_email": reverse("auth-verify-email", request=request),
                    "forgot_password": reverse("auth-forgot-password", request=request),
                    "reset_password": reverse("auth-reset-password", request=request),
                    "resend_verification_link": reverse(
                        "auth-resend-verification-link", request=request
                    ),
                    "resend_password_reset_link": reverse(
                        "auth-resend-password-reset-link", request=request
                    ),
                }
            }
        )

    @action(detail=False, methods=["post"])
    @permission_classes([AllowAny])
    def register(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        password = data.pop("password")
        data.pop("confirm_password")
        user = User.objects.create(**data)

        user.set_password(password)
        user.is_verified = False
        user.save()

        otp = user_generate.generate_otp(user.email)
        token = user_generate.generate_verify_token(user.email)
        name = f"{user.last_name} {user.first_name}"
        task_app.send_task(
            "send_verify_email_notification",
            args=[
                str(user.phone_number),
                str(user.email),
                str(otp),
                str(name),
                str(token),
            ],
        )

        return Response(
            {"message": "Registration successful. Verify account via email or SMS."},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["post"])
    @permission_classes([AllowAny])
    def login(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        username = serializer.validated_data["username"]
        password = serializer.validated_data["password"]

        user = authenticate(request, username=username, password=password)

        if not user:
            raise AuthenticationFailed("Invalid credentials")

        # login_user(request, user)
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)
        access_lifetime = settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"]
        refresh_lifetime = settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"]

        response = Response(
            {
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                },
                "access_token": access_token,
                "refresh_token": refresh_token,
            }
        )
        if ENV == " production":
            response.set_cookie(
                key="access_token",
                value=access_token,
                max_age=int(access_lifetime.total_seconds()),
                httponly=True,
                secure=True,  # True in production (HTTPS)
                samesite="Lax",  # or "Strict"
            )

            response.set_cookie(
                key="refresh_token",
                value=refresh_token,
                httponly=True,
                secure=True,
                samesite="Lax",
                max_age=int(refresh_lifetime.total_seconds()),
            )

            return response
        else:
            response.set_cookie(
                key="access_token",
                value=access_token,
                max_age=int(access_lifetime.total_seconds()),
                httponly=True,
                secure=False,
                samesite="Lax",
            )

            response.set_cookie(
                key="refresh_token",
                value=refresh_token,
                httponly=True,
                secure=False,
                samesite="Lax",
                max_age=int(refresh_lifetime.total_seconds()),
            )

            return response

    @action(detail=False, methods=["post"])
    @permission_classes([IsAuthenticated])
    def logout(self, request: HttpRequest):
        access_token = request.COOKIES.get("access_token") or request.data.get(
            "access_token"
        )
        refresh_token = request.COOKIES.get("refresh_token") or request.data.get(
            "refresh_token"
        )

        try:
            if access_token:
                blacklist_token(access_token)
            if refresh_token:
                blacklist_token(refresh_token)
                token_refresh = RefreshToken(refresh_token)
                token_refresh.blacklist()
            response = Response({"detail": "Logout successful"})
            send_force_logout(request.user.id)
            response.delete_cookie("access_token")
            response.delete_cookie("refresh_token")
            response.delete_cookie("csrfToken")
            response.delete_cookie("sessionid")

            return response

        except Exception:
            return Response({"error": "Invalid token"}, status=400)

    @action(detail=False, methods=["get"])
    @permission_classes([AllowAny])
    def refresh(self, request):
        refresh_token = request.COOKIES.get("refresh_token") or request.data.get(
            "refresh_token"
        )

        try:
            token = RefreshToken(refresh_token)

            access_token = str(token.access_token)
            access_lifetime = settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"]

            response = Response({"access_token": access_token})
            if ENV == " production":
                response.set_cookie(
                    key="access_token",
                    value=access_token,
                    max_age=int(access_lifetime.total_seconds()),
                    httponly=True,
                    secure=True,
                    samesite="Lax",  # or "Strict"
                )

                return response
            else:
                response.set_cookie(
                    key="access_token",
                    value=access_token,
                    max_age=int(access_lifetime.total_seconds()),
                    httponly=True,
                    secure=False,
                    samesite="Lax",
                )

            return response

        except Exception:
            return Response({"error": "Invalid refresh token"}, status=401)

    @action(detail=False, methods=["post"])
    @permission_classes([AllowAny])
    def verify_email(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        otp = serializer.validated_data.get("otp")
        token = serializer.validated_data.get("token")

        if otp:
            email = user_verify.verify_otp(otp)

        elif token:
            email = user_verify.verify_verify_token(token)

        else:
            raise ValidationError("No verification data provided")

        if not email:
            raise ValidationError("Invalid or expired verification token")

        user = crud_actions.get_object(User, email=email)

        user.is_verified = True
        user.verified_at = now()
        user.save()

        return Response(
            {"message": "Email verified successfully"},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"])
    @permission_classes([AllowAny])
    def resend_verification_link(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].strip().lower()
        user = crud_actions.get_object(User, email=email)

        if user.is_verified:
            return Response(
                {"message": "Email already verified."},
                status=200,
            )

        otp = user_generate.generate_otp(user.email)
        token = user_generate.generate_verify_token(user.email)
        name = f"{user.last_name} {user.first_name}"
        task_app.send_task(
            "send_verify_email_notification",
            args=[
                str(user.phone_number),
                str(user.email),
                str(otp),
                str(name),
                str(token),
            ],
        )
        return Response(
            {"message": "Verification link sent to your email."},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"])
    @permission_classes([AllowAny])
    def resend_password_reset_link(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"].strip().lower()
        user = crud_actions.get_object(model=User, email=email)

        otp = user_generate.generate_otp(email)
        token = user_generate.generate_reset_token(email)
        name = f"{user.last_name} {user.first_name}"

        task_app.send_task(
            "send_password_reset_notification",
            args=[
                str(user.phone_number),
                str(user.email),
                str(otp),
                str(name),
                str(token),
            ],
        )
        return Response(
            {"message": "Password reset link sent successfully."},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"])
    @permission_classes([AllowAny])
    def forgot_password(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]

        user = crud_actions.first(User, email=email)
        otp = user_generate.generate_otp(user.email)
        token = user_generate.generate_reset_token(user.email)
        name = f"{user.last_name} {user.first_name}"

        if user:
            task_app.send_task(
                "send_password_reset_notification",
                args=[
                    str(user.phone_number),
                    str(user.email),
                    str(otp),
                    str(name),
                    str(token),
                ],
            )

        response = Response(
            {"message": "If the email exists a reset link was sent"})
        response["HX-Redirect"] = "/reset_password/"
        return response

    @action(detail=False, methods=["post"])
    @permission_classes([AllowAny])
    def reset_password(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data.get("token")
        otp = serializer.validated_data.get("otp")

        new_password = serializer.validated_data["new_password"]

        email = None

        if token:
            try:
                email = user_verify.verify_reset_token(token)
            except Exception:
                return Response({"error": "Invalid or expired token"}, status=400)

        elif otp:
            try:
                email = user_verify.verify_otp(otp)
            except Exception:
                return Response({"error": "Invalid or expired OTP"}, status=400)

        else:
            return Response({"error": "OTP or token required"}, status=400)

        user = crud_actions.get_object(User, email=email)

        if not user:
            return Response({"error": "User not found"}, status=404)

        user.set_password(new_password)
        user.save()

        return Response({"message": "Password reset successful"})

"""Sign-in endpoints: csrf, login, logout, me (HANDOFF "HTTP API")."""

from django.contrib.auth import authenticate, login, logout
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.exceptions import NotAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from accounts.permissions import AnyMember, signed_in_user
from accounts.serializers import LoginRequestSerializer, SessionSerializer, session_payload
from eingang.problem import ProblemError
from eingang.throttles import GeneralThrottle, LoginThrottle

TAGS = ["auth"]


class CsrfView(APIView):
    authentication_classes = ()
    permission_classes = ()

    @extend_schema(
        responses={204: OpenApiResponse(description="Sets the csrftoken cookie.")}, tags=TAGS
    )
    @method_decorator(ensure_csrf_cookie)
    def get(self, request: Request) -> Response:
        return Response(status=204)


class LoginView(APIView):
    authentication_classes = ()
    permission_classes = ()
    throttle_classes = (GeneralThrottle, LoginThrottle)

    @extend_schema(request=LoginRequestSerializer, responses={200: SessionSerializer}, tags=TAGS)
    @method_decorator(csrf_protect)
    def post(self, request: Request) -> Response:
        payload = LoginRequestSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        user = authenticate(
            request._request,
            username=payload.validated_data["email"].lower(),
            password=payload.validated_data["password"],
        )
        # Inactive users (the sandbox's sample people) are refused by Django's backend.
        if not isinstance(user, User):
            raise ProblemError(
                400,
                "INVALID_CREDENTIALS",
                "Sign-in failed",
                "The email address or password is not correct.",
            )
        login(request._request, user)
        return Response(session_payload(user))


class LogoutView(APIView):
    permission_classes = (AnyMember,)

    @extend_schema(request=None, responses={204: None}, tags=TAGS)
    def post(self, request: Request) -> Response:
        logout(request._request)
        return Response(status=204)


class MeView(APIView):
    permission_classes = (AnyMember,)

    @extend_schema(responses={200: SessionSerializer}, tags=TAGS)
    def get(self, request: Request) -> Response:
        user = signed_in_user(request)
        if user is None:
            raise NotAuthenticated
        return Response(session_payload(user))

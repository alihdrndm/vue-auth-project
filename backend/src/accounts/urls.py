from django.urls import path

from accounts.api import (
    CsrfView,
    LoginView,
    LogoutView,
    MemberDetailView,
    MemberListView,
    MeView,
    OrganizationView,
)

urlpatterns = [
    path("auth/csrf", CsrfView.as_view(), name="auth-csrf"),
    path("auth/login", LoginView.as_view(), name="auth-login"),
    path("auth/logout", LogoutView.as_view(), name="auth-logout"),
    path("auth/me", MeView.as_view(), name="auth-me"),
    path("organization", OrganizationView.as_view(), name="organization"),
    path("members", MemberListView.as_view(), name="member-list"),
    path("members/<uuid:member_id>", MemberDetailView.as_view(), name="member-detail"),
]

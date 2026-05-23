from django.urls import path

from sandbox.api import SandboxView

urlpatterns = [path("sandbox", SandboxView.as_view(), name="sandbox")]

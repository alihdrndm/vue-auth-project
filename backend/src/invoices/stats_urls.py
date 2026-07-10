from django.urls import path

from invoices.stats_api import StatsView

urlpatterns = [
    path("stats", StatsView.as_view(), name="stats"),
]

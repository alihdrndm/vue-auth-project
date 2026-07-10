from django.urls import path

from invoices.rules_api import RuleExplanationView

urlpatterns = [
    path("rules/<str:rule_id>", RuleExplanationView.as_view(), name="rule-explanation"),
]

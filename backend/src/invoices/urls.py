from django.urls import path

from invoices.api import (
    DocumentCollectionView,
    DocumentDetailView,
    DocumentFileView,
    DocumentTextView,
    DocumentVisualizationView,
    DocumentXmlView,
)
from invoices.review_api import (
    CheckResolveView,
    DecisionView,
    InvoiceEditView,
    MarkReviewedView,
    ReopenView,
    RetryView,
    SendBackView,
)

urlpatterns = [
    path("documents", DocumentCollectionView.as_view(), name="document-list"),
    path("documents/<uuid:document_id>", DocumentDetailView.as_view(), name="document-detail"),
    path("documents/<uuid:document_id>/file", DocumentFileView.as_view(), name="document-file"),
    path("documents/<uuid:document_id>/xml", DocumentXmlView.as_view(), name="document-xml"),
    path("documents/<uuid:document_id>/text", DocumentTextView.as_view(), name="document-text"),
    path(
        "documents/<uuid:document_id>/visualization",
        DocumentVisualizationView.as_view(),
        name="document-visualization",
    ),
    path("documents/<uuid:document_id>/invoice", InvoiceEditView.as_view(), name="invoice-edit"),
    path(
        "documents/<uuid:document_id>/mark-reviewed",
        MarkReviewedView.as_view(),
        name="document-mark-reviewed",
    ),
    path("documents/<uuid:document_id>/decision", DecisionView.as_view(), name="document-decision"),
    path(
        "documents/<uuid:document_id>/send-back",
        SendBackView.as_view(),
        name="document-send-back",
    ),
    path("documents/<uuid:document_id>/reopen", ReopenView.as_view(), name="document-reopen"),
    path("documents/<uuid:document_id>/retry", RetryView.as_view(), name="document-retry"),
    path("checks/<uuid:check_id>/resolve", CheckResolveView.as_view(), name="check-resolve"),
]

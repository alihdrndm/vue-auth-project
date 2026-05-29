from django.urls import path

from invoices.api import (
    DocumentCollectionView,
    DocumentDetailView,
    DocumentFileView,
    DocumentTextView,
    DocumentVisualizationView,
    DocumentXmlView,
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
]

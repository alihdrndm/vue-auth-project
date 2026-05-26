from django.urls import path

from invoices.api import DocumentCollectionView

urlpatterns = [
    path("documents", DocumentCollectionView.as_view(), name="document-list"),
]

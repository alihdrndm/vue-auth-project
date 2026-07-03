from django.urls import path

from exports.api import ExportCollectionView, ExportDownloadView

urlpatterns = [
    path("exports", ExportCollectionView.as_view(), name="export-list"),
    path("exports/<uuid:export_id>/download", ExportDownloadView.as_view(), name="export-download"),
]

from django.urls import path

from suppliers.api import SupplierDetailView, SupplierListView

urlpatterns = [
    path("suppliers", SupplierListView.as_view(), name="supplier-list"),
    path("suppliers/<uuid:supplier_id>", SupplierDetailView.as_view(), name="supplier-detail"),
]

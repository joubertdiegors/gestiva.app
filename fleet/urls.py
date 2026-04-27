from django.urls import path
from . import views

app_name = "fleet"

urlpatterns = [
    # Dashboard
    path("", views.dashboard, name="dashboard"),

    # Veículos
    path("vehicles/", views.vehicle_list, name="vehicle_list"),
    path("vehicles/new/", views.vehicle_create, name="vehicle_create"),
    path("vehicles/<int:pk>/", views.vehicle_detail, name="vehicle_detail"),
    path("vehicles/<int:pk>/edit/", views.vehicle_edit, name="vehicle_edit"),

    # Categorias
    path("categories/", views.category_list, name="category_list"),
    path("categories/new/", views.category_create, name="category_create"),
    path("categories/<int:pk>/edit/", views.category_edit, name="category_edit"),

    # Documentos (por veículo)
    path("vehicles/<int:vehicle_pk>/documents/new/", views.document_create, name="document_create"),
    path("documents/<int:pk>/edit/", views.document_edit, name="document_edit"),

    # Manutenções
    path("vehicles/<int:vehicle_pk>/maintenances/new/", views.maintenance_create, name="maintenance_create"),
    path("maintenances/<int:pk>/edit/", views.maintenance_edit, name="maintenance_edit"),

    # Abastecimentos
    path("vehicles/<int:vehicle_pk>/fuelings/new/", views.fueling_create, name="fueling_create"),
    path("fuelings/<int:pk>/edit/", views.fueling_edit, name="fueling_edit"),

    # Multas
    path("fines/", views.fine_list, name="fine_list"),
    path("vehicles/<int:vehicle_pk>/fines/new/", views.fine_create, name="fine_create"),
    path("fines/<int:pk>/edit/", views.fine_edit, name="fine_edit"),

    # Despesas
    path("vehicles/<int:vehicle_pk>/expenses/new/", views.expense_create, name="expense_create"),
    path("expenses/<int:pk>/edit/", views.expense_edit, name="expense_edit"),
]

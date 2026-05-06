from django.urls import path
from . import views

app_name = "equipment"

urlpatterns = [
    # Equipamentos
    path("", views.equipment_list, name="list"),
    path("new/", views.equipment_create, name="create"),
    path("<int:pk>/", views.equipment_detail, name="detail"),
    path("<int:pk>/edit/", views.equipment_edit, name="edit"),

    # Categorias
    path("categories/", views.category_list, name="category_list"),
    path("categories/save/", views.category_save, name="category_save"),
    path("categories/<int:pk>/save/", views.category_save, name="category_update"),
    path("categories/<int:pk>/delete/", views.category_delete, name="category_delete"),

    # Empréstimos
    path("loans/", views.loan_list, name="loan_list"),
    path("<int:equipment_pk>/loan/", views.loan_create, name="loan_create"),
    path("loans/<int:pk>/return/", views.loan_return, name="loan_return"),
    path("loans/<int:pk>/ticket/", views.loan_ticket, name="loan_ticket"),

    # Venda a funcionário
    path("<int:equipment_pk>/sell/", views.sale_create, name="sale_create"),
    path("sales/<int:pk>/edit/", views.sale_edit, name="sale_edit"),
]

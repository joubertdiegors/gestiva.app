from django.urls import path
from . import views

app_name = 'catalog'

urlpatterns = [
    # Units of Measure (lista + API JSON para modal)
    path('units/save/', views.unit_save, name='unit_save'),
    path('units/<int:pk>/save/', views.unit_save, name='unit_update'),
    path('units/<int:pk>/delete/', views.unit_delete, name='unit_delete'),
    path('units/', views.unit_list, name='unit_list'),

    # Categories (lista + API JSON para modal)
    path('categories/save/', views.category_save, name='category_save'),
    path('categories/<int:pk>/save/', views.category_save, name='category_update'),
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete'),
    path('categories/', views.category_list, name='category_list'),

    # Products
    path('', views.product_list, name='product_list'),
    path('create/', views.product_create, name='product_create'),
    path('<int:pk>/', views.product_detail, name='product_detail'),
    path('<int:pk>/edit/', views.product_update, name='product_update'),
    path('<int:pk>/delete/', views.product_delete, name='product_delete'),
    path('<int:pk>/toggle-approved/', views.product_toggle_approved, name='product_toggle_approved'),
    path('<int:pk>/toggle-active/', views.product_toggle_active, name='product_toggle_active'),
]

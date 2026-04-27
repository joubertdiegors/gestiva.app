from django.urls import path
from . import views

app_name = 'suppliers'

urlpatterns = [
    path('', views.supplier_list, name='list'),
    path('create/', views.supplier_create, name='create'),
    path('<int:pk>/', views.supplier_detail, name='detail'),
    path('<int:pk>/edit/', views.supplier_update, name='update'),
    path('<int:pk>/delete/', views.supplier_delete, name='delete'),

    # Address AJAX
    path('<int:supplier_pk>/addresses/save/', views.address_save, name='address_save'),
    path('<int:supplier_pk>/addresses/<int:pk>/save/', views.address_save, name='address_update'),
    path('<int:supplier_pk>/addresses/<int:pk>/delete/', views.address_delete, name='address_delete'),

    # Contact AJAX
    path('<int:supplier_pk>/contacts/save/', views.contact_save, name='contact_save'),
    path('<int:supplier_pk>/contacts/<int:pk>/save/', views.contact_save, name='contact_update'),
    path('<int:supplier_pk>/contacts/<int:pk>/delete/', views.contact_delete, name='contact_delete'),
]

from django.urls import path
from . import views

app_name = 'clients'

urlpatterns = [
    path('', views.client_list, name='list'),
    path('create/', views.client_create, name='create'),
    path('<int:pk>/', views.client_detail, name='detail'),
    path('<int:pk>/edit/', views.client_update, name='update'),

    # Address AJAX
    path('<int:client_pk>/addresses/save/', views.address_save, name='address_save'),
    path('<int:client_pk>/addresses/<int:pk>/save/', views.address_save, name='address_update'),
    path('<int:client_pk>/addresses/<int:pk>/delete/', views.address_delete, name='address_delete'),

    # Contact AJAX
    path('<int:client_pk>/contacts/save/', views.contact_save, name='contact_save'),
    path('<int:client_pk>/contacts/<int:pk>/save/', views.contact_save, name='contact_update'),
    path('<int:client_pk>/contacts/<int:pk>/delete/', views.contact_delete, name='contact_delete'),
]

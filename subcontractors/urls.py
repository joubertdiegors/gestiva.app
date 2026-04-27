from django.urls import path
from . import views

app_name = 'subcontractors'

urlpatterns = [
    path('', views.subcontractor_list, name='list'),
    path('create/', views.subcontractor_create, name='create'),
    path('<int:pk>/', views.subcontractor_detail, name='detail'),
    path('<int:pk>/edit/', views.subcontractor_update, name='update'),

    # Address AJAX
    path('<int:sub_pk>/addresses/save/', views.address_save, name='address_save'),
    path('<int:sub_pk>/addresses/<int:pk>/save/', views.address_save, name='address_update'),
    path('<int:sub_pk>/addresses/<int:pk>/delete/', views.address_delete, name='address_delete'),
]

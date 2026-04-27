from django.urls import path
from . import views

urlpatterns = [
    path('', views.project_list, name='project_list'),
    path('create/', views.project_create, name='project_create'),
    path('<int:pk>/edit/', views.project_update, name='project_update'),
    path('ajax/contacts/', views.get_contacts_by_client, name='ajax_contacts'),
]
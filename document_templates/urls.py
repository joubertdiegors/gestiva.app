from django.urls import path
from . import views

app_name = 'document_templates'

urlpatterns = [
    path('',                       views.template_list,      name='list'),
    path('create/',                views.template_create,    name='create'),
    path('<int:pk>/editor/',       views.template_editor,    name='editor'),
    path('<int:pk>/delete/',       views.template_delete,    name='delete'),
    path('<int:pk>/duplicate/',    views.template_duplicate, name='duplicate'),
]

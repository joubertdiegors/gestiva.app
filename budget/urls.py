from django.urls import path
from . import views

app_name = 'budget'

urlpatterns = [
    # List / create / detail / edit / delete
    path('',                      views.budget_list,   name='budget_list'),
    path('create/',               views.budget_create, name='budget_create'),
    path('<int:pk>/',             views.budget_detail, name='budget_detail'),
    path('<int:pk>/edit/',        views.budget_update, name='budget_update'),
    path('<int:pk>/delete/',      views.budget_delete, name='budget_delete'),

    # AJAX — project helpers
    path('ajax/projects/',        views.ajax_projects_by_client, name='ajax_projects'),
    path('ajax/project-create/',  views.ajax_project_create,     name='ajax_project_create'),

    # AJAX — service info
    path('ajax/service/<int:pk>/',views.service_info,            name='service_info'),

    # AJAX — chapters
    path('<int:budget_pk>/chapters/save/',              views.chapter_save,   name='chapter_save'),
    path('<int:budget_pk>/chapters/<int:pk>/save/',     views.chapter_save,   name='chapter_update'),
    path('<int:budget_pk>/chapters/<int:pk>/delete/',   views.chapter_delete, name='chapter_delete'),

    # AJAX — items
    path('<int:budget_pk>/items/save/',                 views.item_save,   name='item_save'),
    path('<int:budget_pk>/items/<int:pk>/save/',        views.item_save,   name='item_update'),
    path('<int:budget_pk>/items/<int:pk>/delete/',      views.item_delete, name='item_delete'),
]

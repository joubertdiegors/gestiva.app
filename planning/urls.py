from django.urls import path
from . import views

app_name = 'planning'

urlpatterns = [
    path('', views.planning_list, name='list'),
    path('board/blank-line/', views.blank_line_save, name='blank_line_save'),
    path('board/assign/', views.board_assign_worker, name='board_assign'),
    path('board/assign-project/', views.board_assign_project, name='board_assign_project'),
    path('board/projects/', views.board_projects_search, name='board_projects_search'),
    path('board/subcontractors/', views.board_subcontractors_search, name='board_subcontractors_search'),
    path('board/subcontractors/assign/', views.board_assign_subcontractor, name='board_assign_subcontractor'),
    path('board/workers/', views.board_workers_search, name='board_workers_search'),
    path('board/duplicate/', views.board_duplicate_planning, name='board_duplicate_planning'),
    path('board/clear/', views.board_clear_day, name='board_clear_day'),
    path('project/<int:project_pk>/create/', views.planning_create, name='create'),
    path('<int:pk>/', views.planning_detail, name='detail'),
    path('<int:pk>/delete/', views.planning_delete, name='delete'),

    # API JSON — workers
    path('<int:planning_pk>/workers/add/', views.planning_add_worker, name='add_worker'),
    path('workers/<int:pw_pk>/update/', views.planning_update_worker, name='update_worker'),
    path('workers/<int:pw_pk>/remove/', views.planning_remove_worker, name='remove_worker'),

    # API JSON — subcontractors
    path('<int:planning_pk>/subcontractors/add/', views.planning_add_subcontractor, name='add_subcontractor'),
    path('subcontractors/<int:ps_pk>/remove/', views.planning_remove_subcontractor, name='remove_subcontractor'),
]
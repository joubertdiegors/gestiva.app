from django.urls import path
from . import views

app_name = 'timesheets'

urlpatterns = [
    path('',                                    views.timesheet_list,               name='list'),
    path('lista-valores/',                      views.timesheet_list_values,         name='list_values'),
    path('board/',                              views.timesheet_daily_board,         name='daily_board'),
    path('board/save/',                         views.timesheet_daily_board_save,    name='daily_board_save'),
    path('board/calendar/',                     views.timesheet_calendar_days,       name='calendar_days'),
    path('create/',                             views.timesheet_create,             name='create'),
    path('<int:pk>/edit/',                      views.timesheet_update,             name='update'),
    path('<int:pk>/delete/',                    views.timesheet_delete,             name='delete'),
    path('project/<int:project_pk>/summary/',   views.timesheet_project_summary,    name='project_summary'),
    path('planning/<int:planning_pk>/bulk/',    views.timesheet_bulk_from_planning, name='bulk_from_planning'),
]

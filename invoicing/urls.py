from django.urls import path
from . import views

app_name = 'invoicing'

urlpatterns = [
    path('',                              views.invoice_list,             name='list'),
    path('create/',                       views.invoice_create,           name='create'),
    path('<int:pk>/',                     views.invoice_detail,           name='detail'),
    path('<int:pk>/edit/',                views.invoice_update,           name='update'),
    path('<int:pk>/print/',               views.invoice_print,            name='print'),
    path('<int:pk>/pdf/',                 views.invoice_pdf,              name='pdf'),
    path('<int:pk>/email/',               views.invoice_send_email,       name='send_email'),
    path('<int:pk>/send/',                views.invoice_mark_sent,        name='send'),
    path('<int:pk>/cancel/',              views.invoice_cancel,           name='cancel'),

    # AJAX helpers
    path('ajax/projects/',                        views.ajax_projects_by_client,  name='ajax_projects'),
    path('<int:pk>/lines/save/',                  views.line_save,                name='line_save'),
    path('<int:pk>/lines/reorder/',               views.line_reorder,             name='line_reorder'),
    path('<int:pk>/lines/<int:line_pk>/delete/',  views.line_delete,              name='line_delete'),
    path('<int:pk>/lines/<int:line_pk>/duplicate/', views.line_duplicate,         name='line_duplicate'),
]

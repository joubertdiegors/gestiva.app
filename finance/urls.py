from django.urls import path
from . import views

app_name = 'finance'

urlpatterns = [
    path('',              views.dashboard,       name='dashboard'),
    path('payables/',     views.payable_list,    name='payables'),
    path('receivables/',  views.receivable_list, name='receivables'),

    # AJAX — payables
    path('payables/save/',          views.payable_save,   name='payable_save'),
    path('payables/<int:pk>/delete/', views.payable_delete, name='payable_delete'),

    # AJAX — payments (shared for payable + receivable)
    path('payments/save/',            views.payment_save,   name='payment_save'),
    path('payments/<int:pk>/delete/', views.payment_delete, name='payment_delete'),
]

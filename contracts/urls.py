from django.urls import path
from . import views

app_name = 'contracts'

urlpatterns = [
    # ── Contracts ──────────────────────────────────────────────────────────────
    path('',                                views.contract_list,        name='list'),
    path('create/',                         views.contract_create,      name='create'),
    path('<int:pk>/',                        views.contract_detail,      name='detail'),
    path('<int:pk>/edit/',                   views.contract_edit,        name='edit'),
    path('<int:pk>/delete/',                 views.contract_delete,      name='delete'),
    path('<int:pk>/lines/add/',              views.contract_line_add,    name='line_add'),
    path('<int:pk>/lines/<int:line_pk>/delete/', views.contract_line_delete, name='line_delete'),

    # ── Addenda ────────────────────────────────────────────────────────────────
    path('addenda/',                                    views.addendum_list,        name='addendum_list'),
    path('addenda/create/',                             views.addendum_create,      name='addendum_create'),
    path('<int:contract_pk>/addenda/create/',            views.addendum_create,      name='addendum_create_for'),
    path('addenda/<int:pk>/',                           views.addendum_detail,      name='addendum_detail'),
    path('addenda/<int:pk>/edit/',                      views.addendum_edit,        name='addendum_edit'),
    path('addenda/<int:pk>/delete/',                    views.addendum_delete,      name='addendum_delete'),
    path('addenda/<int:pk>/lines/add/',                 views.addendum_line_add,    name='addendum_line_add'),
    path('addenda/<int:pk>/lines/<int:line_pk>/delete/', views.addendum_line_delete, name='addendum_line_delete'),
    path('addenda/<int:pk>/copy-lines/',                views.addendum_copy_lines,  name='addendum_copy_lines'),

    # Subcontractor invoices
    path('addenda/<int:addendum_pk>/invoices/create/', views.subinvoice_create, name='subinvoice_create'),
    path('invoices/<int:pk>/delete/',                  views.subinvoice_delete, name='subinvoice_delete'),

    # ── Entity contract views ──────────────────────────────────────────────────
    path('by-client/<int:client_pk>/',          views.client_contracts,          name='client_contracts'),
    path('by-subcontractor/<int:sub_pk>/',       views.subcontractor_contracts,   name='subcontractor_contracts'),
    path('by-supplier/<int:supplier_pk>/',       views.supplier_contracts,        name='supplier_contracts'),

    # ── Supplier contracts CRUD ────────────────────────────────────────────────
    path('supplier/<int:supplier_pk>/create/',           views.supplier_contract_create, name='supplier_contract_create'),
    path('supplier-contract/<int:pk>/',                  views.supplier_contract_detail, name='supplier_contract_detail'),
    path('supplier-contract/<int:pk>/edit/',             views.supplier_contract_edit,   name='supplier_contract_edit'),
    path('supplier-contract/<int:pk>/delete/',           views.supplier_contract_delete, name='supplier_contract_delete'),
    path('supplier-contract/<int:pk>/lines/add/',        views.supplier_line_add,        name='supplier_line_add'),
    path('supplier-contract/<int:pk>/lines/<int:line_pk>/delete/', views.supplier_line_delete, name='supplier_line_delete'),

    # ── Statements (EA) ────────────────────────────────────────────────────────
    path('statements/',                                       views.statement_list,        name='statement_list'),
    path('statements/create/',                                views.statement_create,      name='statement_create'),
    path('<int:contract_pk>/statements/create/',              views.statement_create,      name='statement_create_client'),
    path('addenda/<int:addendum_pk>/statements/create/',      views.statement_create,      name='statement_create_sub'),
    path('statements/<int:pk>/',                              views.statement_detail,      name='statement_detail'),
    path('statements/<int:pk>/edit/',                         views.statement_edit,        name='statement_edit'),
    path('statements/<int:pk>/delete/',                       views.statement_delete,      name='statement_delete'),
    path('statements/<int:pk>/send/',                         views.statement_send,        name='statement_send'),
    path('statements/<int:pk>/lines/add/',                    views.statement_line_add,    name='statement_line_add'),
    path('statements/<int:pk>/lines/<int:line_pk>/delete/',   views.statement_line_delete, name='statement_line_delete'),
]

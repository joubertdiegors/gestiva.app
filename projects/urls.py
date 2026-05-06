from django.urls import path
from . import views

urlpatterns = [
    path('', views.project_list, name='project_list'),
    path('create/', views.project_create, name='project_create'),
    path('<int:pk>/', views.project_detail, name='project_detail'),
    path('<int:pk>/edit/', views.project_update, name='project_update'),
    path('ajax/contacts/', views.get_contacts_by_client, name='ajax_contacts'),

    # Interactions (mini-CRM)
    path('<int:pk>/interactions/save/', views.interaction_save, name='project_interaction_save'),
    path('<int:pk>/interactions/<int:entry_pk>/delete/', views.interaction_delete, name='project_interaction_delete'),

    # Supplier invoices
    path('<int:pk>/invoices/save/', views.invoice_save, name='project_invoice_save'),
    path('<int:pk>/invoices/<int:entry_pk>/delete/', views.invoice_delete, name='project_invoice_delete'),

    # Materials
    path('<int:pk>/materials/save/', views.material_save, name='project_material_save'),
    path('<int:pk>/materials/<int:entry_pk>/delete/', views.material_delete, name='project_material_delete'),

    # Labour
    path('<int:pk>/labour/save/', views.labour_save, name='project_labour_save'),
    path('<int:pk>/labour/<int:entry_pk>/delete/', views.labour_delete, name='project_labour_delete'),

    # CIAW
    path('<int:pk>/ciaw/tree/',               views.ciaw_tree,   name='project_ciaw_tree'),
    path('<int:pk>/ciaw/search/',             views.ciaw_search, name='project_ciaw_search'),
    path('<int:pk>/ciaw/add/',                views.ciaw_add,    name='project_ciaw_add'),
    path('<int:pk>/ciaw/<int:node_pk>/remove/', views.ciaw_remove, name='project_ciaw_remove'),

    # WorkRegistrationType (tabela auxiliar)
    path('work-registration-types/',                      views.work_registration_type_list,   name='work_registration_type_list'),
    path('work-registration-types/save/',                 views.work_registration_type_save,   name='work_registration_type_save'),
    path('work-registration-types/<int:pk>/update/',      views.work_registration_type_save,   name='work_registration_type_update'),
    path('work-registration-types/<int:pk>/delete/',      views.work_registration_type_delete, name='work_registration_type_delete'),
]

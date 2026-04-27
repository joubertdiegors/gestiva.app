from django.urls import path
from . import views

app_name = 'workforce'

urlpatterns = [
    path('', views.collaborator_list, name='list'),
    path('create/', views.collaborator_create, name='create'),
    # Ficheiros sensíveis (antes de <pk>/ para não sombrear rotas mais específicas)
    path('<int:pk>/photo/', views.collaborator_photo_serve, name='collaborator_photo'),
    path('<int:pk>/driver-license/scan/', views.driver_license_scan_serve, name='driver_license_scan'),
    path('<int:pk>/', views.collaborator_detail, name='detail'),
    path('<int:pk>/edit/', views.collaborator_update, name='update'),
    path('<int:pk>/status/toggle/', views.collaborator_status_toggle, name='status_toggle'),
    # Valor/hora
    path('<int:pk>/hourly-rate/create/', views.collaborator_hourly_rate_create, name='hourly_rate_create'),
    path('<int:pk>/hourly-rate/<int:rate_pk>/edit/', views.collaborator_hourly_rate_edit, name='hourly_rate_edit'),
    # Endereços
    path('<int:pk>/addresses/save/', views.collaborator_address_save, name='address_save'),
    path('<int:pk>/addresses/<int:addr_pk>/save/', views.collaborator_address_save, name='address_update'),
    path('<int:pk>/addresses/<int:addr_pk>/delete/', views.collaborator_address_delete, name='address_delete'),
    # Notas de seguro
    path('<int:pk>/insurance-notes/create/', views.insurance_note_create, name='insurance_note_create'),
    path('<int:pk>/insurance-notes/<int:note_pk>/resolve/', views.insurance_note_resolve, name='insurance_note_resolve'),
    # Carta de condução
    path('<int:pk>/driver-license/save/', views.driver_license_save, name='driver_license_save'),
    # Estacionamento
    path('<int:pk>/parking-permits/create/', views.parking_permit_create, name='parking_permit_create'),
    path('<int:pk>/parking-permits/<int:permit_pk>/delete/', views.parking_permit_delete, name='parking_permit_delete'),
    # Autocomplete
    path('autocomplete/nationalities/', views.nationality_autocomplete, name='nationality_autocomplete'),
    path('autocomplete/languages/', views.language_autocomplete, name='language_autocomplete'),
    # ── Tabelas auxiliares: Nacionalidades ─────────────────────────────────
    path('nationalities/', views.nationality_list, name='nationality_list'),
    path('nationalities/create/', views.nationality_create, name='nationality_create'),
    path('nationalities/<int:pk>/edit/', views.nationality_edit, name='nationality_edit'),
    path('nationalities/<int:pk>/delete/', views.nationality_delete, name='nationality_delete'),
    # ── Tabelas auxiliares: Idiomas ────────────────────────────────────────
    path('languages/', views.language_list, name='language_list'),
    path('languages/create/', views.language_create, name='language_create'),
    path('languages/<int:pk>/edit/', views.language_edit, name='language_edit'),
    path('languages/<int:pk>/delete/', views.language_delete, name='language_delete'),
    # ── Tabelas auxiliares: Caixas de Seguro ──────────────────────────────
    path('insurance-funds/', views.insurance_fund_list, name='insurance_fund_list'),
    path('insurance-funds/create/', views.insurance_fund_create, name='insurance_fund_create'),
    path('insurance-funds/<int:pk>/', views.insurance_fund_detail, name='insurance_fund_detail'),
    path('insurance-funds/<int:pk>/edit/', views.insurance_fund_edit, name='insurance_fund_edit'),
    path('insurance-funds/<int:pk>/delete/', views.insurance_fund_delete, name='insurance_fund_delete'),
    path('insurance-funds/<int:fund_pk>/contacts/save/', views.insurance_fund_contact_save, name='insurance_fund_contact_save'),
    path('insurance-funds/<int:fund_pk>/contacts/<int:contact_pk>/save/', views.insurance_fund_contact_save, name='insurance_fund_contact_update'),
    path('insurance-funds/<int:fund_pk>/contacts/<int:contact_pk>/delete/', views.insurance_fund_contact_delete, name='insurance_fund_contact_delete'),
    # ── Formas Jurídicas (CRUD) ────────────────────────────────────────────
    path('legal-forms/', views.legal_form_list, name='legal_form_list'),
    path('legal-forms/create/', views.legal_form_create, name='legal_form_create'),
    path('legal-forms/<int:pk>/edit/', views.legal_form_edit, name='legal_form_edit'),
    path('legal-forms/<int:pk>/delete/', views.legal_form_delete, name='legal_form_delete'),
]

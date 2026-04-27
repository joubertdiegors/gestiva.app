from django.urls import path
from . import views


app_name = 'procurement'


urlpatterns = [
    path(
        'offers/<int:pk>/history/',
        views.offer_price_history,
        name='offer_price_history',
    ),

    path(
        'suppliers/<int:supplier_pk>/contacts/<int:contact_pk>/json/',
        views.supplier_contact_json,
        name='supplier_contact_json',
    ),

    # RFQ
    path('rfq/', views.rfq_list, name='rfq_list'),
    path('rfq/create/', views.rfq_create, name='rfq_create'),
    path('rfq/<int:pk>/', views.rfq_detail, name='rfq_detail'),

    # RFQ AJAX: items
    path('rfq/<int:rfq_pk>/items/save/', views.rfq_item_save, name='rfq_item_save'),
    path('rfq/<int:rfq_pk>/items/batch-add/', views.rfq_item_batch_add, name='rfq_item_batch_add'),
    path('rfq/<int:rfq_pk>/items/<int:pk>/save/', views.rfq_item_save, name='rfq_item_update'),
    path('rfq/<int:rfq_pk>/items/<int:pk>/delete/', views.rfq_item_delete, name='rfq_item_delete'),

    # RFQ AJAX: vendors
    path('rfq/<int:rfq_pk>/vendors/add/', views.rfq_vendor_add, name='rfq_vendor_add'),
    path('rfq/<int:rfq_pk>/vendors/batch-add/', views.rfq_vendor_batch_add, name='rfq_vendor_batch_add'),
    path('rfq/<int:rfq_pk>/vendors/<int:pk>/remove/', views.rfq_vendor_remove, name='rfq_vendor_remove'),

    # RFQ send
    path('rfq/<int:rfq_pk>/send/', views.rfq_send, name='rfq_send'),

    # RFQ header (per vendor)
    path(
        'rfq/<int:rfq_pk>/vendors/<int:pk>/header/',
        views.rfq_vendor_header_save,
        name='rfq_vendor_header',
    ),

    # RFQ answers + apply
    path(
        'rfq/<int:rfq_pk>/vendors/<int:vendor_pk>/items/<int:item_pk>/answer/',
        views.rfq_answer_save,
        name='rfq_answer_save',
    ),
    path(
        'rfq/<int:rfq_pk>/items/<int:item_pk>/select-vendor/',
        views.rfq_select_vendor,
        name='rfq_select_vendor',
    ),
    path(
        'rfq/<int:rfq_pk>/apply-selected/',
        views.rfq_apply_selected,
        name='rfq_apply_selected',
    ),

    # Manage offers from product screen
    path(
        'products/<int:product_pk>/offers/save/',
        views.product_offer_save,
        name='product_offer_save',
    ),
    path(
        'products/<int:product_pk>/offers/<int:pk>/save/',
        views.product_offer_save,
        name='product_offer_update',
    ),
    path(
        'products/<int:product_pk>/offers/<int:pk>/delete/',
        views.product_offer_delete,
        name='product_offer_delete',
    ),

    # Manage offers from supplier screen
    path(
        'suppliers/<int:supplier_pk>/offers/save/',
        views.supplier_offer_save,
        name='supplier_offer_save',
    ),
    path(
        'suppliers/<int:supplier_pk>/offers/<int:pk>/save/',
        views.supplier_offer_save,
        name='supplier_offer_update',
    ),
    path(
        'suppliers/<int:supplier_pk>/offers/<int:pk>/delete/',
        views.supplier_offer_delete,
        name='supplier_offer_delete',
    ),
]


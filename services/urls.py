from django.urls import path
from . import views

app_name = 'services'

urlpatterns = [
    # Categories
    path('categories/save/',          views.category_save,   name='category_save'),
    path('categories/<int:pk>/save/', views.category_save,   name='category_update'),
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete'),
    path('categories/',               views.category_list,   name='category_list'),

    # Services
    path('',                          views.service_list,          name='service_list'),
    path('create/',                   views.service_create,        name='service_create'),
    path('<int:pk>/',                  views.service_detail,        name='service_detail'),
    path('<int:pk>/edit/',             views.service_update,        name='service_update'),
    path('<int:pk>/delete/',           views.service_delete,        name='service_delete'),
    path('<int:pk>/toggle-active/',    views.service_toggle_active, name='service_toggle_active'),

    # Materials (AJAX)
    path('<int:service_pk>/materials/',              views.material_list,   name='material_list'),
    path('<int:service_pk>/materials/save/',         views.material_save,   name='material_save'),
    path('<int:service_pk>/materials/<int:pk>/save/',views.material_save,   name='material_update'),
    path('<int:service_pk>/materials/<int:pk>/delete/', views.material_delete, name='material_delete'),
]

from django.urls import path

from . import views, views_otp

app_name = 'accounts'

urlpatterns = [
    # Users
    path('',                         views.user_list,           name='list'),
    path('new/',                     views.user_create,         name='create'),
    path('<int:pk>/edit/',           views.user_edit,           name='edit'),
    path('<int:pk>/toggle/',         views.user_toggle_active,  name='toggle'),
    path('<int:pk>/reset-password/', views.user_reset_password, name='reset_password'),

    # Access profiles
    path('profiles/',                views.profile_list,   name='profile_list'),
    path('profiles/new/',            views.profile_create, name='profile_create'),
    path('profiles/<int:pk>/edit/',  views.profile_edit,   name='profile_edit'),
    path('profiles/<int:pk>/delete/',views.profile_delete, name='profile_delete'),

    # 2FA TOTP (Sprint 5)
    path('2fa/setup/',   views_otp.otp_setup,   name='otp_setup'),
    path('2fa/verify/',  views_otp.otp_verify,  name='otp_verify'),
    path('2fa/disable/', views_otp.otp_disable, name='otp_disable'),

    # API: preferências de colunas por utilizador
    path('prefs/table/<str:table_id>/', views.api_table_prefs, name='api_table_prefs'),
]
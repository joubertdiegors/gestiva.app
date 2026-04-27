from django.contrib import admin
from django.urls import path, include
from django.conf.urls.i18n import i18n_patterns
from django.contrib.auth.views import LogoutView
from django.conf import settings
from django.conf.urls.static import static
from django.urls import re_path
from django.views.static import serve
from . import views
from catalog import views as catalog_views

urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),
    path('login/', views.login_view, name='login'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
    path('setup-inicial-4x9z/', views.setup_view, name='setup'),
]

urlpatterns += i18n_patterns(
    path('', views.home_view, name='home'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('projects/', include('projects.urls')),
    path('subcontractors/', include('subcontractors.urls')),
    path('planning/', include('planning.urls')),
    path('clients/', include('clients.urls')),
    path('suppliers/', include('suppliers.urls')),
    path('procurement/', include('procurement.urls')),
    # Alias para compatibilidade: alguns templates usam {% url 'product_list' %}
    path('catalog/', catalog_views.product_list, name='product_list'),
    path('catalog/', include('catalog.urls')),
    path('contacts/', include('contacts.urls')),
    path('workforce/', include('workforce.urls')),
    path('timesheets/', include('timesheets.urls')),
    path('services/', include('services.urls')),
    path('budget/',   include('budget.urls')),
    path('fleet/',    include('fleet.urls')),
)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
elif getattr(settings, 'SERVE_MEDIA', False):
    _media_prefix = settings.MEDIA_URL.strip('/')
    if _media_prefix:
        urlpatterns += [
            re_path(
                rf'^{_media_prefix}/(?P<path>.*)$',
                serve,
                {'document_root': str(settings.MEDIA_ROOT)},
            ),
        ]

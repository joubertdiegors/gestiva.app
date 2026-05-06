from django.contrib import admin
from django.urls import path, include
from django.conf.urls.i18n import i18n_patterns
from django.contrib.auth.views import LogoutView
from django.conf import settings
from django.conf.urls.static import static
from django.urls import re_path
from django.views.static import serve
from django.views.defaults import permission_denied
from . import views
from catalog import views as catalog_views
from accounts.views import api_table_prefs

handler403 = lambda request, exception=None: permission_denied(request, exception, template_name='403.html')

urlpatterns = [
    # "/" is not under LocalePrefixPattern; send users to the localized home URL.
    path('', views.root_redirect, name='site_root'),
    path('i18n/', include('django.conf.urls.i18n')),
    path('login/', views.login_view, name='login'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
    path('setup-inicial-4x9z/', views.setup_view, name='setup'),
    path('search/', views.global_search, name='global_search'),
    # API sem prefixo de língua para uso em fetch() do JS
    path('api/prefs/table/<str:table_id>/', api_table_prefs, name='api_table_prefs'),
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
    path('budget/',     include('budget.urls')),
    path('invoicing/',  include('invoicing.urls')),
    path('finance/',    include('finance.urls')),
    path('fleet/',      include('fleet.urls')),
    path('equipment/',  include('equipment.urls')),
    path('contracts/',          include('contracts.urls')),
    path('document-templates/', include('document_templates.urls')),
    # True: every language has a URL prefix (/pt-br/..., /en/...). The cookie is then
    # respected on paths outside i18n (e.g. /login/) and language switching is reliable.
    prefix_default_language=True,
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

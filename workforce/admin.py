from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import (
    InsuranceFund,
    InsuranceFundContact,
    Collaborator,
    CollaboratorHourlyRate,
    DriverLicense,
)


# 🏦 CONTACTS INLINE (dentro da caisse)
class InsuranceFundContactInline(admin.TabularInline):
    model = InsuranceFundContact
    extra = 1


# 🏦 INSURANCE FUND
@admin.register(InsuranceFund)
class InsuranceFundAdmin(admin.ModelAdmin):

    list_display = (
        'name',
        'phone',
        'email'
    )

    search_fields = (
        'name',
    )

    ordering = ('name',)

    inlines = [InsuranceFundContactInline]


# 👥 CONTACT (opcional separado)
@admin.register(InsuranceFundContact)
class InsuranceFundContactAdmin(admin.ModelAdmin):

    list_display = (
        'name',
        'fund',
        'phone',
        'email'
    )

    search_fields = (
        'name',
        'fund__name'
    )

    list_filter = ('fund',)


# 💰 HOURLY RATE INLINE (dentro do colaborador)
class CollaboratorHourlyRateInline(admin.TabularInline):
    model = CollaboratorHourlyRate
    extra = 1
    ordering = ('-start_date',)


# 👷 COLLABORATOR
@admin.register(Collaborator)
class CollaboratorAdmin(admin.ModelAdmin):

    list_display = (
        'name',
        'company',
        'insurance_fund',
        'status',
        'current_hourly_rate'
    )

    list_filter = (
        'status',
        'company',
        'insurance_fund'
    )

    search_fields = (
        'name',
        'phone',
        'email'
    )

    ordering = ('name',)

    inlines = [CollaboratorHourlyRateInline]

    # 💰 mostrar valor atual
    def current_hourly_rate(self, obj):
        rate = obj.get_current_hourly_rate()
        return rate.hourly_rate if rate else "-"
    
    current_hourly_rate.short_description = "Hourly Rate"


@admin.register(DriverLicense)
class DriverLicenseAdmin(admin.ModelAdmin):
    list_display = ["collaborator", "license_number", "categories", "expiry_date", "is_expired"]
    search_fields = ["collaborator__name", "license_number"]
    list_filter = ["expiry_date"]

    @admin.display(boolean=True, description=_("Expired"))
    def is_expired(self, obj):
        return obj.is_expired


# 💰 HOURLY RATE (admin separado)
@admin.register(CollaboratorHourlyRate)
class CollaboratorHourlyRateAdmin(admin.ModelAdmin):

    list_display = (
        'collaborator',
        'hourly_rate',
        'start_date',
        'end_date'
    )

    list_filter = (
        'collaborator',
    )

    search_fields = (
        'collaborator__name',
    )

    ordering = ('-start_date',)
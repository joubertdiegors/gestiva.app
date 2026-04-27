from django.contrib import admin
from .models import Client, ClientAddress, ClientContact


class ClientAddressInline(admin.TabularInline):
    model = ClientAddress
    extra = 1


class ClientContactInline(admin.TabularInline):
    model = ClientContact
    extra = 1


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'vat_number', 'is_active')
    search_fields = ('name', 'vat_number')

    inlines = [ClientAddressInline, ClientContactInline]
from django.contrib import admin
from .models import (
    Contract, ContractLine,
    Addendum, AddendumLine,
    Statement, StatementLine,
    SubcontractorInvoice,
)


class ContractLineInline(admin.TabularInline):
    model = ContractLine
    extra = 0


class AddendumInline(admin.TabularInline):
    model = Addendum
    extra = 0
    show_change_link = True
    fields = ('number', 'title', 'subcontractor', 'project', 'status')


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display  = ('title', 'contract_type', 'status', 'signed_date', 'created_at')
    list_filter   = ('contract_type', 'status')
    search_fields = ('title', 'reference', 'client__name', 'subcontractor__name')
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')
    inlines = [ContractLineInline, AddendumInline]


class AddendumLineInline(admin.TabularInline):
    model = AddendumLine
    extra = 0


class StatementInline(admin.TabularInline):
    model = Statement
    extra = 0
    show_change_link = True
    fields = ('number', 'statement_type', 'issue_date', 'status')


@admin.register(Addendum)
class AddendumAdmin(admin.ModelAdmin):
    list_display  = ('number', 'title', 'subcontractor', 'project', 'status')
    list_filter   = ('status',)
    search_fields = ('title', 'number', 'subcontractor__name', 'project__name')
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')
    inlines = [AddendumLineInline, StatementInline]


class StatementLineInline(admin.TabularInline):
    model = StatementLine
    extra = 0


@admin.register(Statement)
class StatementAdmin(admin.ModelAdmin):
    list_display  = ('number', 'statement_type', 'issue_date', 'status')
    list_filter   = ('statement_type', 'status')
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')
    inlines = [StatementLineInline]


@admin.register(SubcontractorInvoice)
class SubcontractorInvoiceAdmin(admin.ModelAdmin):
    list_display  = ('invoice_number', 'addendum', 'invoice_date', 'amount', 'status')
    list_filter   = ('status',)
    readonly_fields = ('created_at', 'payable')

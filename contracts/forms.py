from django import forms
from django.utils.translation import gettext_lazy as _

from .models import (
    Contract, ContractLine,
    Addendum, AddendumLine,
    Statement, StatementLine,
    SubcontractorInvoice,
    SupplierContract, SupplierContractLine,
)

_DATE_WIDGET   = lambda: forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
_TEXT_WIDGET   = lambda: forms.TextInput(attrs={'class': 'form-control'})
_SELECT_WIDGET = lambda: forms.Select(attrs={'class': 'form-control'})
_TEXTAREA      = lambda rows=3: forms.Textarea(attrs={'class': 'form-control', 'rows': rows})
_NUMBER        = lambda step='0.01': forms.NumberInput(attrs={'class': 'form-control', 'step': step, 'min': '0'})


# ── Contract ──────────────────────────────────────────────────────────────────

class ContractForm(forms.ModelForm):
    class Meta:
        model  = Contract
        fields = [
            'contract_type', 'title', 'reference',
            'client', 'subcontractor', 'supplier', 'project',
            'signed_date', 'start_date', 'end_date', 'status',
            'discount_percent', 'vat_rate',
            'notes_internal', 'notes_client',
        ]
        widgets = {
            'contract_type':    _SELECT_WIDGET(),
            'title':            _TEXT_WIDGET(),
            'reference':        _TEXT_WIDGET(),
            'client':           _SELECT_WIDGET(),
            'subcontractor':    _SELECT_WIDGET(),
            'supplier':         _SELECT_WIDGET(),
            'project':          _SELECT_WIDGET(),
            'signed_date':      _DATE_WIDGET(),
            'start_date':       _DATE_WIDGET(),
            'end_date':         _DATE_WIDGET(),
            'status':           _SELECT_WIDGET(),
            'discount_percent': _NUMBER(),
            'vat_rate':         _NUMBER(),
            'notes_internal':   _TEXTAREA(3),
            'notes_client':     _TEXTAREA(3),
        }


class ContractLineForm(forms.ModelForm):
    class Meta:
        model  = ContractLine
        fields = ['line_type', 'description', 'detail', 'quantity', 'unit', 'unit_price', 'discount_percent', 'vat_rate']
        widgets = {
            'line_type':         _SELECT_WIDGET(),
            'description':       _TEXT_WIDGET(),
            'detail':            _TEXTAREA(1),
            'quantity':          _NUMBER('any'),
            'unit':              _TEXT_WIDGET(),
            'unit_price':        _NUMBER('0.01'),
            'discount_percent':  _NUMBER('0.01'),
            'vat_rate':          _NUMBER('0.01'),
        }


# ── Addendum ──────────────────────────────────────────────────────────────────

class AddendumForm(forms.ModelForm):
    class Meta:
        model  = Addendum
        fields = [
            'number', 'title', 'subcontractor', 'project',
            'signed_date', 'start_date', 'end_date', 'status',
            'discount_percent', 'vat_rate',
            'notes_internal', 'notes_sub',
        ]
        widgets = {
            'number':           _TEXT_WIDGET(),
            'title':            _TEXT_WIDGET(),
            'subcontractor':    _SELECT_WIDGET(),
            'project':          _SELECT_WIDGET(),
            'signed_date':      _DATE_WIDGET(),
            'start_date':       _DATE_WIDGET(),
            'end_date':         _DATE_WIDGET(),
            'status':           _SELECT_WIDGET(),
            'discount_percent': _NUMBER(),
            'vat_rate':         _NUMBER(),
            'notes_internal':   _TEXTAREA(3),
            'notes_sub':        _TEXTAREA(3),
        }

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get('start_date')
        end   = cleaned.get('end_date')
        if start and end and end < start:
            self.add_error('end_date', _('End date cannot be before start date.'))
        return cleaned


class AddendumLineForm(forms.ModelForm):
    class Meta:
        model  = AddendumLine
        fields = ['line_type', 'description', 'detail', 'quantity', 'unit', 'unit_price', 'discount_percent', 'vat_rate']
        widgets = {
            'line_type':         _SELECT_WIDGET(),
            'description':       _TEXT_WIDGET(),
            'detail':            _TEXTAREA(1),
            'quantity':          _NUMBER('any'),
            'unit':              _TEXT_WIDGET(),
            'unit_price':        _NUMBER('0.01'),
            'discount_percent':  _NUMBER('0.01'),
            'vat_rate':          _NUMBER('0.01'),
        }


# ── Statement (EA) ────────────────────────────────────────────────────────────

class StatementForm(forms.ModelForm):
    class Meta:
        model  = Statement
        fields = [
            'statement_type', 'number',
            'contract', 'addendum',
            'period_start', 'period_end',
            'issue_date', 'due_date', 'status',
            'notes_internal', 'notes_external',
        ]
        widgets = {
            'statement_type': _SELECT_WIDGET(),
            'number':         _TEXT_WIDGET(),
            'contract':       _SELECT_WIDGET(),
            'addendum':       _SELECT_WIDGET(),
            'period_start':   _DATE_WIDGET(),
            'period_end':     _DATE_WIDGET(),
            'issue_date':     _DATE_WIDGET(),
            'due_date':       _DATE_WIDGET(),
            'status':         _SELECT_WIDGET(),
            'notes_internal': _TEXTAREA(2),
            'notes_external': _TEXTAREA(2),
        }

    def clean(self):
        cleaned = super().clean()
        stype    = cleaned.get('statement_type')
        contract = cleaned.get('contract')
        addendum = cleaned.get('addendum')
        if stype == Statement.TYPE_CLIENT and not contract:
            self.add_error('contract', _('Select the client contract for this EA.'))
        if stype == Statement.TYPE_SUBCONTRACTOR and not addendum:
            self.add_error('addendum', _('Select the addendum for this EA.'))
        return cleaned


class StatementLineForm(forms.ModelForm):
    class Meta:
        model  = StatementLine
        fields = ['description', 'amount', 'notes']
        widgets = {
            'description': _TEXT_WIDGET(),
            'amount':      _NUMBER('0.01'),
            'notes':       _TEXTAREA(1),
        }


# ── Supplier Contract ─────────────────────────────────────────────────────────

class SupplierContractForm(forms.ModelForm):
    class Meta:
        model  = SupplierContract
        fields = ['reference', 'title', 'signed_date', 'valid_from', 'valid_until', 'status', 'notes']
        widgets = {
            'reference':   _TEXT_WIDGET(),
            'title':       _TEXT_WIDGET(),
            'signed_date': _DATE_WIDGET(),
            'valid_from':  _DATE_WIDGET(),
            'valid_until': _DATE_WIDGET(),
            'status':      _SELECT_WIDGET(),
            'notes':       _TEXTAREA(3),
        }


class SupplierContractLineForm(forms.ModelForm):
    class Meta:
        model  = SupplierContractLine
        fields = ['description', 'unit', 'unit_price', 'notes']
        widgets = {
            'description': _TEXT_WIDGET(),
            'unit':        _TEXT_WIDGET(),
            'unit_price':  _NUMBER('0.01'),
            'notes':       _TEXTAREA(1),
        }


# ── Subcontractor Invoice ─────────────────────────────────────────────────────

class SubcontractorInvoiceForm(forms.ModelForm):
    class Meta:
        model  = SubcontractorInvoice
        fields = ['invoice_number', 'invoice_date', 'due_date', 'amount', 'statement', 'status', 'notes']
        widgets = {
            'invoice_number': _TEXT_WIDGET(),
            'invoice_date':   _DATE_WIDGET(),
            'due_date':       _DATE_WIDGET(),
            'amount':         _NUMBER('0.01'),
            'statement':      _SELECT_WIDGET(),
            'status':         _SELECT_WIDGET(),
            'notes':          _TEXTAREA(2),
        }

from django import forms
from .models import DocumentTemplate


class DocumentTemplateCreateForm(forms.ModelForm):
    """Minimal form used only on the creation screen (name + type)."""
    class Meta:
        model  = DocumentTemplate
        fields = ['name', 'document_type']
        widgets = {
            'name':          forms.TextInput(attrs={'class': 'form-control', 'autofocus': True}),
            'document_type': forms.HiddenInput(),
        }


class DocumentTemplateForm(forms.ModelForm):
    class Meta:
        model  = DocumentTemplate
        fields = ['name', 'document_type', 'status', 'is_default', 'custom_css']
        widgets = {
            'name':          forms.TextInput(attrs={'class': 'form-control'}),
            'document_type': forms.Select(attrs={'class': 'form-control'}),
            'status':        forms.Select(attrs={'class': 'form-control'}),
            'custom_css':    forms.Textarea(attrs={'class': 'form-control font-mono', 'rows': 6}),
        }



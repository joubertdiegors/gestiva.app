from django import forms
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _

from .models import User, AccessProfile


# ---------------------------------------------------------------------------
# User forms
# ---------------------------------------------------------------------------

_USER_FIELDS = [
    'first_name', 'last_name', 'username',
    'email', 'phone', 'access_profile', 'is_active',
]

_USER_WIDGETS = {
    'first_name':     forms.TextInput(attrs={'class': 'form-control'}),
    'last_name':      forms.TextInput(attrs={'class': 'form-control'}),
    'username':       forms.TextInput(attrs={'class': 'form-control'}),
    'email':          forms.EmailInput(attrs={'class': 'form-control'}),
    'phone':          forms.TextInput(attrs={'class': 'form-control'}),
    'access_profile': forms.Select(attrs={'class': 'form-control'}),
    'is_active':      forms.CheckboxInput(),
}


class UserCreateForm(forms.ModelForm):
    password1 = forms.CharField(
        label=_("Senha"),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'autocomplete': 'new-password',
        }),
    )
    password2 = forms.CharField(
        label=_("Confirmar senha"),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'autocomplete': 'new-password',
        }),
    )

    class Meta:
        model   = User
        fields  = _USER_FIELDS
        widgets = _USER_WIDGETS

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show groups that have a managed AccessProfile
        self.fields['access_profile'].queryset = (
            Group.objects.filter(access_profile__isnull=False).order_by('name')
        )
        self.fields['access_profile'].empty_label = _("— Sem perfil —")

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password1')
        p2 = cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', _("As senhas não coincidem."))
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
        return user


class UserEditForm(forms.ModelForm):
    class Meta:
        model   = User
        fields  = _USER_FIELDS
        widgets = _USER_WIDGETS

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['access_profile'].queryset = (
            Group.objects.filter(access_profile__isnull=False).order_by('name')
        )
        self.fields['access_profile'].empty_label = _("— Sem perfil —")


class UserPasswordResetForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['new_password1'].widget.attrs['class'] = 'form-control'
        self.fields['new_password2'].widget.attrs['class'] = 'form-control'


# ---------------------------------------------------------------------------
# Profile form
# ---------------------------------------------------------------------------

class ProfileForm(forms.Form):
    """
    Handles name + description + color for an AccessProfile.
    Permissions are handled separately via raw checkboxes in the template.
    """
    name = forms.CharField(
        label=_("Nome do perfil"),
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    description = forms.CharField(
        label=_("Descrição"),
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
    )
    color = forms.ChoiceField(
        label=_("Cor"),
        choices=AccessProfile._meta.get_field('color').choices,
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
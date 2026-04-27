from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import Group, Permission
from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from django.utils.translation import gettext_lazy as _
from django.db.models import Q

from .models import User, AccessProfile
from .forms import UserCreateForm, UserEditForm, UserPasswordResetForm, ProfileForm
from .permissions import build_matrix


# ---------------------------------------------------------------------------
# Access guard — replaces the old role-based _is_admin check.
# Superusers always pass. Regular users need accounts.view_user permission.
# ---------------------------------------------------------------------------

def _can_manage_users(user):
    return user.is_authenticated and (
        user.is_superuser or user.has_perm('accounts.view_user')
    )


# ---------------------------------------------------------------------------
# User views
# ---------------------------------------------------------------------------

@login_required
@permission_required('accounts.view_user', raise_exception=True)
def user_list(request):
    qs = User.objects.select_related('access_profile__access_profile').all()

    query          = request.GET.get('q', '').strip()
    profile_filter = request.GET.get('profile', '').strip()
    status_filter  = request.GET.get('status', '').strip()

    if query:
        qs = qs.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query)  |
            Q(username__icontains=query)   |
            Q(email__icontains=query)
        )
    if profile_filter:
        qs = qs.filter(access_profile_id=profile_filter)
    if status_filter == 'active':
        qs = qs.filter(is_active=True)
    elif status_filter == 'inactive':
        qs = qs.filter(is_active=False)

    profiles = Group.objects.filter(access_profile__isnull=False).order_by('name')

    return render(request, 'accounts/user_list.html', {
        'users':          qs,
        'profiles':       profiles,
        'query':          query,
        'profile_filter': profile_filter,
        'status_filter':  status_filter,
        'total':          qs.count(),
    })


@login_required
@permission_required('accounts.add_user', raise_exception=True)
def user_create(request):
    form = UserCreateForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        messages.success(
            request,
            _("Utilizador '%(name)s' criado com sucesso.") % {'name': user}
        )
        return redirect('accounts:list')

    return render(request, 'accounts/user_form.html', {
        'form':      form,
        'title':     _("Novo Utilizador"),
        'is_create': True,
    })


@login_required
def user_edit(request, pk):
    user = get_object_or_404(User, pk=pk)
    # Permite editar a si próprio; para editar outros, requer permissão
    if request.user.pk != pk and not (
        request.user.is_superuser or request.user.has_perm('accounts.change_user')
    ):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied

    form = UserEditForm(request.POST or None, instance=user)

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(
            request,
            _("Utilizador '%(name)s' atualizado.") % {'name': user}
        )
        if request.user.pk == pk:
            return redirect('planning:list')
        return redirect('accounts:list')

    return render(request, 'accounts/user_form.html', {
        'form':      form,
        'title':     _("Editar Utilizador"),
        'user_obj':  user,
        'is_create': False,
    })


@login_required
@permission_required('accounts.change_user', raise_exception=True)
def user_toggle_active(request, pk):
    """Activate or deactivate a user account via POST."""
    if request.method != 'POST':
        return redirect('accounts:list')

    user = get_object_or_404(User, pk=pk)

    if user == request.user:
        messages.error(request, _("Não pode desativar a sua própria conta."))
    else:
        user.is_active = not user.is_active
        user.save(update_fields=['is_active'])
        state = _("ativado") if user.is_active else _("desativado")
        messages.success(
            request,
            _("Utilizador '%(name)s' %(state)s.") % {'name': user, 'state': state}
        )

    return redirect('accounts:list')


@login_required
def user_reset_password(request, pk):
    user = get_object_or_404(User, pk=pk)
    # Permite alterar a própria senha; para alterar de outros, requer permissão
    if request.user.pk != pk and not (
        request.user.is_superuser or request.user.has_perm('accounts.change_user')
    ):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied

    form = UserPasswordResetForm(user, request.POST or None)

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(
            request,
            _("Senha de '%(name)s' redefinida com sucesso.") % {'name': user}
        )
        if request.user.pk == pk:
            return redirect('planning:list')
        return redirect('accounts:list')

    return render(request, 'accounts/user_reset_password.html', {
        'form':     form,
        'user_obj': user,
    })


# ---------------------------------------------------------------------------
# Profile (AccessProfile) views
# ---------------------------------------------------------------------------

@login_required
@permission_required('accounts.view_user', raise_exception=True)
def profile_list(request):
    profiles = AccessProfile.objects.select_related('group').all()
    return render(request, 'accounts/profile_list.html', {
        'profiles': profiles,
    })


@login_required
@permission_required('accounts.add_user', raise_exception=True)
def profile_create(request):
    form = ProfileForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        # Create the Django Group
        group = Group.objects.create(name=form.cleaned_data['name'])

        # Create the AccessProfile metadata
        AccessProfile.objects.create(
            group=group,
            description=form.cleaned_data['description'],
            color=form.cleaned_data['color'],
        )

        # Assign selected permissions
        perm_ids = [int(x) for x in request.POST.getlist('perm_ids') if x.isdigit()]
        if perm_ids:
            group.permissions.set(Permission.objects.filter(id__in=perm_ids))

        messages.success(
            request,
            _("Perfil '%(name)s' criado com sucesso.") % {'name': group.name}
        )
        return redirect('accounts:profile_list')

    matrix = build_matrix(group=None)
    return render(request, 'accounts/profile_form.html', {
        'form':      form,
        'matrix':    matrix,
        'title':     _("Novo Perfil"),
        'is_create': True,
    })


@login_required
@permission_required('accounts.change_user', raise_exception=True)
def profile_edit(request, pk):
    profile = get_object_or_404(AccessProfile, pk=pk)
    group   = profile.group

    initial = {
        'name':        group.name,
        'description': profile.description,
        'color':       profile.color,
    }
    form = ProfileForm(request.POST or None, initial=initial)

    if request.method == 'POST' and form.is_valid():
        # Update Group name
        group.name = form.cleaned_data['name']
        group.save()

        # Update AccessProfile metadata
        profile.description = form.cleaned_data['description']
        profile.color       = form.cleaned_data['color']
        profile.save()

        # Replace permissions
        perm_ids = [int(x) for x in request.POST.getlist('perm_ids') if x.isdigit()]
        group.permissions.set(Permission.objects.filter(id__in=perm_ids))

        messages.success(
            request,
            _("Perfil '%(name)s' atualizado.") % {'name': group.name}
        )
        return redirect('accounts:profile_list')

    matrix = build_matrix(group=group)
    return render(request, 'accounts/profile_form.html', {
        'form':      form,
        'matrix':    matrix,
        'profile':   profile,
        'title':     _("Editar Perfil"),
        'is_create': False,
    })


@login_required
@permission_required('accounts.delete_user', raise_exception=True)
def profile_delete(request, pk):
    """Delete a profile via POST — also deletes the underlying Group."""
    if request.method != 'POST':
        return redirect('accounts:profile_list')

    profile = get_object_or_404(AccessProfile, pk=pk)
    name    = profile.group.name

    # Re-assign users with this profile before deleting
    User.objects.filter(access_profile=profile.group).update(access_profile=None)
    profile.group.delete()  # Cascades to AccessProfile

    messages.success(
        request,
        _("Perfil '%(name)s' eliminado.") % {'name': name}
    )
    return redirect('accounts:profile_list')
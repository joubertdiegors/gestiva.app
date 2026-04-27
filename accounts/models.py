from django.contrib.auth.models import AbstractUser, Group
from django.db import models
from django.utils.translation import gettext_lazy as _


class AccessProfile(models.Model):
    """
    Extends Django's built-in Group with display metadata.
    One-to-one with auth.Group: Group holds permissions; this model holds UI label, description, and color.
    """
    group = models.OneToOneField(
        Group,
        on_delete=models.CASCADE,
        related_name='access_profile',
        verbose_name=_('Group'),
    )
    description = models.TextField(_('Description'), blank=True)
    color = models.CharField(
        _('Color'),
        max_length=20,
        default='gray',
        choices=[
            ('accent', _('Orange')),
            ('green', _('Green')),
            ('amber', _('Amber')),
            ('red', _('Red')),
            ('gray', _('Gray')),
        ],
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Access profile')
        verbose_name_plural = _('Access profiles')
        ordering = ['group__name']

    def __str__(self):
        return self.group.name

    def get_badge_class(self):
        return {
            'accent': 'badge-accent',
            'green': 'badge-green',
            'amber': 'badge-amber',
            'red': 'badge-red',
            'gray': 'badge-gray',
        }.get(self.color, 'badge-gray')

    @property
    def user_count(self):
        return self.group.profile_users.filter(is_active=True).count()


class User(AbstractUser):
    phone = models.CharField(_('Phone'), max_length=20, blank=True)

    access_profile = models.ForeignKey(
        Group,
        verbose_name=_('Access profile'),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='profile_users',
    )

    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        ordering = ['first_name', 'last_name']

    def __str__(self):
        return self.get_full_name() or self.username

    def save(self, *args, **kwargs):
        update_fields = kwargs.get('update_fields')
        profile_changed = (
            update_fields is None or 'access_profile' in update_fields
        )
        if self.pk and profile_changed:
            try:
                old = User.objects.values_list('access_profile_id', flat=True).get(pk=self.pk)
                profile_changed = old != self.access_profile_id
            except User.DoesNotExist:
                profile_changed = True
        super().save(*args, **kwargs)
        if profile_changed:
            if self.access_profile_id:
                self.groups.set([self.access_profile_id])
            else:
                self.groups.clear()

    @property
    def is_manager(self):
        return self.is_superuser or self.has_perm('projects.change_project')

    def get_profile_badge_class(self):
        try:
            return self.access_profile.access_profile.get_badge_class()
        except Exception:
            return 'badge-gray'

    def get_profile_name(self):
        try:
            return self.access_profile.name
        except Exception:
            return '—'

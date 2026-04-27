from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError


class WorkRegistrationType(models.Model):
    name = models.CharField(_("Name"), max_length=100)

    class Meta:
        verbose_name = _("Work Registration Type")
        verbose_name_plural = _("Work Registration Types")

    def __str__(self):
        return self.name


class Project(models.Model):

    STATUS_CHOICES = [
        ('planning', _('Planning')),
        ('active', _('Active')),
        ('paused', _('Paused')),
        ('finished', _('Finished')),
    ]

    name = models.CharField(_("Name"), max_length=255)

    client = models.ForeignKey(
        'clients.Client',
        verbose_name=_("Client"),
        on_delete=models.PROTECT,
        related_name='projects'
    )

    contacts = models.ManyToManyField(
        'clients.ClientContact',
        verbose_name=_("Contacts"),
        related_name='projects',
        blank=True
    )

    address = models.TextField(_("Address"), blank=True)

    managers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Managers"),
        related_name='managed_projects',
        blank=True
    )

    start_date = models.DateField(_("Start date"), null=True, blank=True)
    end_date = models.DateField(_("End date"), null=True, blank=True)

    notes = models.TextField(_("Notes"), blank=True, null=True)

    has_work_registration = models.BooleanField(
        _("Has work registration"),
        default=False
    )

    work_registration_type = models.ForeignKey(
        'projects.WorkRegistrationType',
        verbose_name=_("Registration type"),
        on_delete=models.SET_NULL,
        blank=True,
        null=True
    )

    work_registration_number = models.CharField(
        _("Registration number"),
        max_length=100,
        blank=True,
        null=True
    )

    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Created by"),
        on_delete=models.PROTECT,
        related_name='projects_created'
    )

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Updated by"),
        on_delete=models.PROTECT,
        related_name='projects_updated',
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)

    def clean(self):
        if self.start_date and self.end_date:
            if self.end_date < self.start_date:
                raise ValidationError({
                    'end_date': _("End date cannot be before start date.")
                })

        if self.has_work_registration:
            if not self.work_registration_type:
                raise ValidationError({
                    'work_registration_type': _("Select a registration type.")
                })
            if not self.work_registration_number:
                raise ValidationError({
                    'work_registration_number': _("Enter the registration number.")
                })
        else:
            self.work_registration_type = None
            self.work_registration_number = None

    class Meta:
        verbose_name = _("Project")
        verbose_name_plural = _("Projects")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['client']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return self.name
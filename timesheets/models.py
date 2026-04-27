from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from decimal import Decimal


class Timesheet(models.Model):
    """
    Record of actual hours worked by a collaborator on a project on a given day.
    Optionally linked to PlanningWorker for the same day.
    """

    worker = models.ForeignKey(
        'workforce.Collaborator',
        verbose_name=_("Worker"),
        on_delete=models.PROTECT,
        related_name='timesheets',
    )
    project = models.ForeignKey(
        'projects.Project',
        verbose_name=_("Project"),
        on_delete=models.PROTECT,
        related_name='timesheets',
    )

    planning_worker = models.OneToOneField(
        'planning.PlanningWorker',
        verbose_name=_("Planning entry"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='timesheet',
    )

    date = models.DateField(_("Date"))

    start_time = models.TimeField(_("Start time"), null=True, blank=True)
    end_time   = models.TimeField(_("End time"),   null=True, blank=True)

    hours = models.DecimalField(
        _("Hours worked"),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )

    hourly_rate_snapshot = models.DecimalField(
        _("Hourly rate (snapshot)"),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Rate at the time of entry, frozen for audit."),
    )

    is_overtime = models.BooleanField(_("Overtime"), default=False)
    overtime_rate = models.DecimalField(
        _("Overtime multiplier"),
        max_digits=4,
        decimal_places=2,
        default=Decimal('1.50'),
    )

    notes = models.TextField(_("Notes"), blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Timesheet")
        verbose_name_plural = _("Timesheets")
        ordering = ['-date', 'worker__name']
        indexes = [
            models.Index(fields=['date', 'project']),
            models.Index(fields=['worker', 'date']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['worker', 'project', 'date'],
                name='unique_timesheet_per_worker_project_day',
            )
        ]
        permissions = [
            ("view_timesheet_values", _("View timesheet cost values")),
        ]

    def __str__(self):
        return f"{self.worker.name} — {self.project.name} — {self.date}"

    @property
    def computed_hours(self):
        """Hours from start/end times or manual hours field."""
        if self.start_time and self.end_time:
            from datetime import datetime, date
            start = datetime.combine(date.today(), self.start_time)
            end   = datetime.combine(date.today(), self.end_time)
            diff  = end - start
            return round(Decimal(diff.total_seconds()) / 3600, 2)
        return self.hours or Decimal('0')

    @property
    def effective_rate(self):
        """Applied rate (with overtime multiplier when applicable)."""
        rate = self.hourly_rate_snapshot or Decimal('0')
        if self.is_overtime:
            return rate * self.overtime_rate
        return rate

    @property
    def total_cost(self):
        """Total cost for this entry."""
        return round(self.computed_hours * self.effective_rate, 2)

    def clean(self):
        if self.start_time and self.end_time:
            if self.end_time <= self.start_time:
                raise ValidationError({
                    'end_time': _("End time must be after start time.")
                })

        if not self.start_time and not self.hours:
            raise ValidationError(
                _("Enter either start/end times or a number of hours worked.")
            )

    def save(self, *args, **kwargs):
        if not self.hourly_rate_snapshot and self.worker_id:
            rate_obj = self.worker.hourly_rates.filter(
                start_date__lte=self.date,
            ).filter(
                models.Q(end_date__isnull=True) | models.Q(end_date__gte=self.date)
            ).first()
            if rate_obj:
                self.hourly_rate_snapshot = rate_obj.hourly_rate
        super().save(*args, **kwargs)
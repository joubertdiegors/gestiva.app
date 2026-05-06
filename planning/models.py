from django.db import models


class Planning(models.Model):
    date = models.DateField()

    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='plannings'
    )

    # Motorista do veículo neste dia (legado — mantido para compatibilidade)
    vehicle_driver = models.ForeignKey(
        'workforce.Collaborator',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='vehicle_planning_assignments',
    )

    # Extensão de outro Planning (mesma obra, mesmo dia, mais funcionários)
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='extensions',
    )
    is_extension = models.BooleanField(default=False)

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', 'pk']

    def __str__(self):
        suffix = ' [ext]' if self.is_extension else ''
        return f"{self.project} - {self.date}{suffix}"


class PlanningSubcontractor(models.Model):
    planning = models.ForeignKey(
        Planning,
        on_delete=models.CASCADE,
        related_name='planning_subcontractors'
    )

    subcontractor = models.ForeignKey(
        'subcontractors.Subcontractor',
        on_delete=models.CASCADE,
        related_name='planning_assignments'
    )

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('planning', 'subcontractor')
        ordering = ['planning']

    def __str__(self):
        return f"{self.subcontractor} - {self.planning}"


class PlanningWorker(models.Model):

    PERIOD_CHOICES = [
        ('full_day', 'Full Day'),
        ('morning', 'Morning'),
        ('afternoon', 'Afternoon'),
        ('custom', 'Custom'),
    ]

    planning = models.ForeignKey(
        Planning,
        on_delete=models.CASCADE,
        related_name='planning_workers'
    )

    worker = models.ForeignKey(
        'workforce.collaborator',
        on_delete=models.CASCADE,
        related_name='planning_assignments'
    )

    subcontractor = models.ForeignKey(
        'subcontractors.Subcontractor',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='worker_plannings'
    )

    period = models.CharField(
        max_length=20,
        choices=PERIOD_CHOICES,
        default='full_day'
    )

    start_time = models.TimeField(
        null=True,
        blank=True
    )

    end_time = models.TimeField(
        null=True,
        blank=True
    )

    role = models.CharField(
        max_length=100,
        blank=True
    )

    is_present = models.BooleanField(
        default=True
    )

    notes = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['planning__date', 'worker']

    def __str__(self):
        return f"{self.worker} - {self.planning} ({self.period})"


class PlanningDayOff(models.Model):
    """Trabalhador sem obra neste dia (equivalente ao cartão «Não trabalhou»)."""

    date = models.DateField(db_index=True)
    worker = models.ForeignKey(
        'workforce.Collaborator',
        on_delete=models.CASCADE,
        related_name='planning_day_offs',
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('date', 'worker'),
                name='planning_dayoff_unique_date_worker',
            ),
        ]
        ordering = ['date', 'worker__name']

    def __str__(self):
        return f"{self.worker} — {self.date} (off)"


class PlanningVehicle(models.Model):
    """Veículo atribuído a uma obra num dia (M2M — permite múltiplos veículos)."""

    planning = models.ForeignKey(
        Planning,
        on_delete=models.CASCADE,
        related_name='planning_vehicles',
    )
    vehicle = models.ForeignKey(
        'fleet.Vehicle',
        on_delete=models.PROTECT,
        related_name='planning_assignments',
    )
    driver = models.ForeignKey(
        'workforce.Collaborator',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='driven_plannings',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('planning', 'vehicle')
        ordering = ['created_at']

    def __str__(self):
        return f"{self.vehicle.license_plate} → {self.planning}"


class PlanningBlankLine(models.Model):
    """Texto manual numa linha de um cartão vazio da folha (impressão A4)."""

    date = models.DateField(db_index=True)
    slot_index = models.PositiveSmallIntegerField()
    line_index = models.PositiveSmallIntegerField()
    text = models.CharField(max_length=240, blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('date', 'slot_index', 'line_index'),
                name='planning_blankline_unique_date_slot_line',
            ),
        ]
        ordering = ('date', 'slot_index', 'line_index')

    def __str__(self):
        return f"{self.date} slot {self.slot_index} L{self.line_index}"
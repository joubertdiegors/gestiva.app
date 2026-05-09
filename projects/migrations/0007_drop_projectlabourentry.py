"""
Sprint 3 — eliminar duplicação ProjectLabourEntry vs Timesheet.

Estratégia: Timesheet é fonte única. Antes de remover o modelo
ProjectLabourEntry, copiamos cada entrada para Timesheet (quando ainda não
estiver ligada) preservando os campos relevantes (hours, hourly_rate como
hourly_rate_snapshot, is_overtime, overtime_multiplier como overtime_rate,
notes).
"""
from decimal import Decimal

from django.db import migrations


def migrate_labour_entries_to_timesheets(apps, schema_editor):
    ProjectLabourEntry = apps.get_model('projects', 'ProjectLabourEntry')
    Timesheet = apps.get_model('timesheets', 'Timesheet')

    for entry in ProjectLabourEntry.objects.all():
        if entry.timesheet_id:
            ts = Timesheet.objects.filter(pk=entry.timesheet_id).first()
            if ts is None:
                continue
            updated = False
            if (ts.hourly_rate_snapshot or Decimal('0')) == 0 and entry.hourly_rate:
                ts.hourly_rate_snapshot = entry.hourly_rate
                updated = True
            if not ts.is_overtime and entry.is_overtime:
                ts.is_overtime = True
                ts.overtime_rate = entry.overtime_multiplier or ts.overtime_rate
                updated = True
            if not (ts.hours or ts.start_time):
                ts.hours = entry.hours
                updated = True
            if updated:
                ts.save()
            continue

        existing = Timesheet.objects.filter(
            worker_id=entry.worker_id,
            project_id=entry.project_id,
            date=entry.date,
        ).first()
        if existing is not None:
            updated = False
            if (existing.hourly_rate_snapshot or Decimal('0')) == 0 and entry.hourly_rate:
                existing.hourly_rate_snapshot = entry.hourly_rate
                updated = True
            if not existing.is_overtime and entry.is_overtime:
                existing.is_overtime = True
                existing.overtime_rate = entry.overtime_multiplier or existing.overtime_rate
                updated = True
            if updated:
                existing.save()
            continue

        Timesheet.objects.create(
            worker_id=entry.worker_id,
            project_id=entry.project_id,
            date=entry.date,
            hours=entry.hours,
            hourly_rate_snapshot=entry.hourly_rate,
            is_overtime=entry.is_overtime,
            overtime_rate=entry.overtime_multiplier or Decimal('1.50'),
            notes=entry.notes or '',
        )


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0006_project_external_id'),
        ('timesheets', '0002_alter_timesheet_options'),
    ]

    operations = [
        migrations.RunPython(
            migrate_labour_entries_to_timesheets,
            migrations.RunPython.noop,
        ),
        migrations.DeleteModel(name='ProjectLabourEntry'),
    ]

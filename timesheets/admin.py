from django.contrib import admin
from .models import Timesheet


@admin.register(Timesheet)
class TimesheetAdmin(admin.ModelAdmin):
    list_display = ('date', 'worker', 'project', 'computed_hours_display',
                    'hourly_rate_snapshot', 'total_cost_display', 'is_overtime')
    list_filter = ('date', 'project', 'is_overtime', 'worker__company')
    search_fields = ('worker__name', 'project__name')
    ordering = ('-date',)
    date_hierarchy = 'date'

    def computed_hours_display(self, obj):
        return f"{obj.computed_hours}h"
    computed_hours_display.short_description = "Hours"

    def total_cost_display(self, obj):
        return f"€ {obj.total_cost}"
    total_cost_display.short_description = "Cost"
from django.contrib import admin
from .models import Planning, PlanningBlankLine, PlanningDayOff, PlanningSubcontractor, PlanningWorker


@admin.register(PlanningBlankLine)
class PlanningBlankLineAdmin(admin.ModelAdmin):
    list_display = ('date', 'slot_index', 'line_index', 'text')
    list_filter = ('date',)
    search_fields = ('text',)


@admin.register(PlanningDayOff)
class PlanningDayOffAdmin(admin.ModelAdmin):
    list_display = ('date', 'worker')
    list_filter = ('date',)
    autocomplete_fields = ('worker',)


class PlanningWorkerInline(admin.TabularInline):
    model = PlanningWorker
    fk_name = 'planning'
    extra = 1


class PlanningSubcontractorInline(admin.TabularInline):
    model = PlanningSubcontractor
    fk_name = 'planning'
    extra = 1


@admin.register(Planning)
class PlanningAdmin(admin.ModelAdmin):
    list_display = ('project', 'date')
    list_filter = ('date', 'project')
    search_fields = ('project__name',)

    inlines = [
        PlanningSubcontractorInline,
        PlanningWorkerInline,
    ]
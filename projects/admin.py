from django.contrib import admin
from .models import Project, WorkRegistrationType


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):

    # 📋 LISTAGEM
    list_display = (
        'name',
        'client',
        'get_managers',
        'start_date',
        'end_date',
        # 'status',
        'has_work_registration',
    )

    # 🔍 FILTROS
    list_filter = (
        'status',
        'has_work_registration',
        'client',
        'managers',
    )

    # 🔎 BUSCA
    search_fields = (
        'name',
        'client__name',
        'address',
    )

    # 🧩 MANY TO MANY BONITO
    filter_horizontal = (
        'managers',
        'contacts',
    )

    # 📑 ORGANIZAÇÃO DO FORM
    fieldsets = (
        ("General", {
            'fields': (
                'name',
                'client',
                'contacts',
                'address',
            )
        }),
        ("Team", {
            'fields': (
                'managers',
            )
        }),
        ("Dates", {
            'fields': (
                'start_date',
                'end_date',
            )
        }),
        ("Work Registration", {
            'fields': (
                'has_work_registration',
                'work_registration_type',
                'work_registration_number',
            )
        }),
        ("Notes", {
            'fields': (
                'notes',
            )
        }),
        ("Status", {
            'fields': (
                'status',
            )
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related('managers')

    # 👤 EXIBIR MANY TO MANY NA LISTA
    def get_managers(self, obj):
        managers = obj.managers.all()
        return ", ".join(str(user) for user in managers) if managers else "-"

    get_managers.short_description = "Managers"

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        else:
            obj.updated_by = request.user

        super().save_model(request, obj, form, change)


@admin.register(WorkRegistrationType)
class WorkRegistrationTypeAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
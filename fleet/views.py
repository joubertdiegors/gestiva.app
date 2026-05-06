import mimetypes
from pathlib import Path

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.db.models import Sum, Q, Count
from django.http import FileResponse, Http404, JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.template.loader import render_to_string

from accounts.decorators import perm_required
from .models import (
    Vehicle,
    VehicleCategory,
    VehicleDocument,
    VehicleMaintenance,
    VehicleFueling,
    VehicleFine,
    VehicleExpense,
)
from .forms import (
    VehicleForm,
    VehicleCategoryForm,
    VehicleDocumentForm,
    VehicleMaintenanceForm,
    VehicleFuelingForm,
    VehicleFineForm,
    VehicleExpenseForm,
)


def _is_ajax(request):
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


def _protected_fleet_upload_response(file_field):
    if file_field is None or not getattr(file_field, 'name', None):
        raise Http404()
    try:
        path = Path(file_field.path).resolve()
    except ValueError:
        raise Http404()
    media_root = Path(settings.MEDIA_ROOT).resolve()
    try:
        rel = path.relative_to(media_root).as_posix()
    except ValueError:
        raise Http404()
    if not rel.startswith(('fleet/documents/', 'fleet/fines/')):
        raise Http404()
    if not path.is_file():
        raise Http404()
    ctype, _ = mimetypes.guess_type(str(path))
    fh = path.open('rb')
    resp = FileResponse(fh, content_type=ctype or 'application/octet-stream')
    resp['Cache-Control'] = 'private, no-store'
    resp['X-Content-Type-Options'] = 'nosniff'
    return resp


@perm_required('fleet.view_vehicle')
def document_file_serve(request, pk):
    doc = get_object_or_404(VehicleDocument, pk=pk)
    return _protected_fleet_upload_response(doc.file)


@perm_required('fleet.view_vehicle')
def fine_file_serve(request, pk):
    fine = get_object_or_404(VehicleFine, pk=pk)
    return _protected_fleet_upload_response(fine.file)


# ── DASHBOARD ─────────────────────────────────────────────────────────────────
@perm_required('fleet.view_vehicle')
def dashboard(request):
    today = timezone.now().date()
    in_30 = today + timezone.timedelta(days=30)
    in_60 = today + timezone.timedelta(days=60)

    expiring_docs = VehicleDocument.objects.filter(
        expiry_date__gte=today, expiry_date__lte=in_60
    ).select_related("vehicle").order_by("expiry_date")

    expired_docs = VehicleDocument.objects.filter(
        expiry_date__lt=today
    ).select_related("vehicle").order_by("expiry_date")

    pending_fines = VehicleFine.objects.filter(
        status=VehicleFine.STATUS_PENDING
    ).select_related("vehicle", "driver")

    payroll_fines = VehicleFine.objects.filter(
        deduct_from_payroll=True, payroll_deducted=False
    ).select_related("vehicle", "driver")

    scheduled_maintenances = VehicleMaintenance.objects.filter(
        status__in=[VehicleMaintenance.STATUS_SCHEDULED, VehicleMaintenance.STATUS_IN_PROGRESS]
    ).select_related("vehicle").order_by("scheduled_date")[:10]

    vehicles = Vehicle.objects.filter(status=Vehicle.STATUS_ACTIVE).select_related("category")

    context = {
        "expiring_docs": expiring_docs,
        "expired_docs": expired_docs,
        "pending_fines": pending_fines,
        "payroll_fines": payroll_fines,
        "scheduled_maintenances": scheduled_maintenances,
        "vehicles": vehicles,
        "active_count": vehicles.count(),
        "maintenance_count": Vehicle.objects.filter(status=Vehicle.STATUS_MAINTENANCE).count(),
        "today": today,
        "in_30": in_30,
    }
    return render(request, "fleet/dashboard.html", context)


# ── VEÍCULOS ──────────────────────────────────────────────────────────────────
@perm_required('fleet.view_vehicle')
def vehicle_list(request):
    qs = Vehicle.objects.select_related("category", "default_driver").all()
    status_filter = request.GET.get("status", "")
    if status_filter:
        qs = qs.filter(status=status_filter)
    q = request.GET.get("q", "")
    if q:
        qs = qs.filter(
            Q(license_plate__icontains=q) | Q(brand__icontains=q) | Q(model__icontains=q)
        )
    return render(request, "fleet/vehicle_list.html", {
        "vehicles": qs,
        "status_filter": status_filter,
        "q": q,
        "status_choices": Vehicle.STATUS_CHOICES,
    })


@perm_required('fleet.view_vehicle')
def vehicle_detail(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk)
    today = timezone.now().date()
    in_60 = today + timezone.timedelta(days=60)

    docs = vehicle.documents.order_by("expiry_date")
    maintenances = vehicle.maintenances.order_by("-scheduled_date")[:10]
    fuelings = vehicle.fuelings.select_related("driver").order_by("-date")[:20]
    fines = vehicle.fines.select_related("driver").order_by("-date")
    expenses = vehicle.expenses.select_related("driver").order_by("-date")[:20]

    cost_maintenance = (
        vehicle.maintenances.filter(status=VehicleMaintenance.STATUS_DONE)
        .aggregate(s=Sum("cost"))["s"] or 0
    )
    cost_fuel = vehicle.fuelings.aggregate(s=Sum("total_cost"))["s"] or 0
    cost_fines = vehicle.fines.aggregate(s=Sum("amount"))["s"] or 0
    cost_expenses = vehicle.expenses.aggregate(s=Sum("amount"))["s"] or 0
    total_cost = cost_maintenance + cost_fuel + cost_fines + cost_expenses

    return render(request, "fleet/vehicle_detail.html", {
        "vehicle": vehicle,
        "docs": docs,
        "maintenances": maintenances,
        "fuelings": fuelings,
        "fines": fines,
        "expenses": expenses,
        "cost_maintenance": cost_maintenance,
        "cost_fuel": cost_fuel,
        "cost_fines": cost_fines,
        "cost_expenses": cost_expenses,
        "total_cost": total_cost,
        "today": today,
        "in_60": in_60,
    })


@perm_required('fleet.add_vehicle')
def vehicle_create(request):
    if request.method == "POST":
        form = VehicleForm(request.POST)
        if form.is_valid():
            vehicle = form.save()
            return redirect("fleet:vehicle_detail", pk=vehicle.pk)
    else:
        form = VehicleForm()
    return render(request, "fleet/vehicle_form.html", {"form": form, "title": _("New Vehicle")})


@perm_required('fleet.change_vehicle')
def vehicle_edit(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk)
    if request.method == "POST":
        form = VehicleForm(request.POST, instance=vehicle)
        if form.is_valid():
            form.save()
            return redirect("fleet:vehicle_detail", pk=vehicle.pk)
    else:
        form = VehicleForm(instance=vehicle)
    return render(request, "fleet/vehicle_form.html", {
        "form": form, "vehicle": vehicle, "title": _("Edit Vehicle")
    })


# ── CATEGORIAS ────────────────────────────────────────────────────────────────
@perm_required('fleet.view_vehicle')
def category_list(request):
    categories = (
        VehicleCategory.objects
        .annotate(vehicle_count=Count('vehicles'))
        .order_by('name')
    )
    return render(request, "fleet/category_list.html", {"categories": categories})


@perm_required('fleet.change_vehicle')
@require_POST
def category_save(request, pk=None):
    instance = get_object_or_404(VehicleCategory, pk=pk) if pk else None
    form = VehicleCategoryForm(request.POST, instance=instance)
    if form.is_valid():
        cat = form.save()
        return JsonResponse({
            'ok': True,
            'category': {
                'id': cat.pk,
                'name': cat.name,
                'vehicle_count': cat.vehicles.count(),
            },
        })
    return JsonResponse({'ok': False, 'errors': form.errors}, status=400)


@perm_required('fleet.delete_vehicle')
@require_POST
def category_delete(request, pk):
    cat = get_object_or_404(VehicleCategory, pk=pk)
    if cat.vehicles.exists():
        return JsonResponse(
            {'ok': False, 'error': str(_('Esta categoria tem veículos associados.'))},
            status=400,
        )
    cat.delete()
    return JsonResponse({'ok': True})


# ── DOCUMENTOS ────────────────────────────────────────────────────────────────
@perm_required('fleet.change_vehicle')
def document_create(request, vehicle_pk):
    vehicle = get_object_or_404(Vehicle, pk=vehicle_pk)
    if request.method == "POST":
        form = VehicleDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.vehicle = vehicle
            doc.save()
            if _is_ajax(request):
                return JsonResponse({"ok": True})
            return redirect("fleet:vehicle_detail", pk=vehicle.pk)
        if _is_ajax(request):
            html = render_to_string("fleet/partials/document_form.html",
                                    {"form": form, "vehicle": vehicle}, request=request)
            return JsonResponse({"ok": False, "html": html})
    else:
        form = VehicleDocumentForm()
    if _is_ajax(request):
        html = render_to_string("fleet/partials/document_form.html",
                                {"form": form, "vehicle": vehicle}, request=request)
        return HttpResponse(html)
    return render(request, "fleet/document_form.html", {
        "form": form, "vehicle": vehicle, "title": _("Add Document")
    })


@perm_required('fleet.change_vehicle')
def document_edit(request, pk):
    doc = get_object_or_404(VehicleDocument, pk=pk)
    if request.method == "POST":
        form = VehicleDocumentForm(request.POST, request.FILES, instance=doc)
        if form.is_valid():
            form.save()
            if _is_ajax(request):
                return JsonResponse({"ok": True})
            return redirect("fleet:vehicle_detail", pk=doc.vehicle_id)
        if _is_ajax(request):
            html = render_to_string("fleet/partials/document_form.html",
                                    {"form": form, "vehicle": doc.vehicle}, request=request)
            return JsonResponse({"ok": False, "html": html})
    else:
        form = VehicleDocumentForm(instance=doc)
    if _is_ajax(request):
        html = render_to_string("fleet/partials/document_form.html",
                                {"form": form, "vehicle": doc.vehicle}, request=request)
        return HttpResponse(html)
    return render(request, "fleet/document_form.html", {
        "form": form, "doc": doc, "vehicle": doc.vehicle, "title": _("Edit Document")
    })


# ── MANUTENÇÕES ───────────────────────────────────────────────────────────────
@perm_required('fleet.change_vehicle')
def maintenance_create(request, vehicle_pk):
    vehicle = get_object_or_404(Vehicle, pk=vehicle_pk)
    if request.method == "POST":
        form = VehicleMaintenanceForm(request.POST)
        if form.is_valid():
            maint = form.save(commit=False)
            maint.vehicle = vehicle
            maint.save()
            if _is_ajax(request):
                return JsonResponse({"ok": True})
            return redirect("fleet:vehicle_detail", pk=vehicle.pk)
        if _is_ajax(request):
            html = render_to_string("fleet/partials/maintenance_form.html",
                                    {"form": form, "vehicle": vehicle}, request=request)
            return JsonResponse({"ok": False, "html": html})
    else:
        form = VehicleMaintenanceForm()
    if _is_ajax(request):
        html = render_to_string("fleet/partials/maintenance_form.html",
                                {"form": form, "vehicle": vehicle}, request=request)
        return HttpResponse(html)
    return render(request, "fleet/maintenance_form.html", {
        "form": form, "vehicle": vehicle, "title": _("Add Maintenance")
    })


@perm_required('fleet.change_vehicle')
def maintenance_edit(request, pk):
    maint = get_object_or_404(VehicleMaintenance, pk=pk)
    if request.method == "POST":
        form = VehicleMaintenanceForm(request.POST, instance=maint)
        if form.is_valid():
            form.save()
            if _is_ajax(request):
                return JsonResponse({"ok": True})
            return redirect("fleet:vehicle_detail", pk=maint.vehicle_id)
        if _is_ajax(request):
            html = render_to_string("fleet/partials/maintenance_form.html",
                                    {"form": form, "vehicle": maint.vehicle}, request=request)
            return JsonResponse({"ok": False, "html": html})
    else:
        form = VehicleMaintenanceForm(instance=maint)
    if _is_ajax(request):
        html = render_to_string("fleet/partials/maintenance_form.html",
                                {"form": form, "vehicle": maint.vehicle}, request=request)
        return HttpResponse(html)
    return render(request, "fleet/maintenance_form.html", {
        "form": form, "maint": maint, "vehicle": maint.vehicle, "title": _("Edit Maintenance")
    })


# ── ABASTECIMENTOS ────────────────────────────────────────────────────────────
@perm_required('fleet.change_vehicle')
def fueling_create(request, vehicle_pk):
    vehicle = get_object_or_404(Vehicle, pk=vehicle_pk)
    if request.method == "POST":
        form = VehicleFuelingForm(request.POST)
        if form.is_valid():
            fuel = form.save(commit=False)
            fuel.vehicle = vehicle
            fuel.save()
            if fuel.km > vehicle.current_km:
                vehicle.current_km = fuel.km
                vehicle.save(update_fields=["current_km", "updated_at"])
            if _is_ajax(request):
                return JsonResponse({"ok": True})
            return redirect("fleet:vehicle_detail", pk=vehicle.pk)
        if _is_ajax(request):
            html = render_to_string("fleet/partials/fueling_form.html",
                                    {"form": form, "vehicle": vehicle}, request=request)
            return JsonResponse({"ok": False, "html": html})
    else:
        form = VehicleFuelingForm()
    if _is_ajax(request):
        html = render_to_string("fleet/partials/fueling_form.html",
                                {"form": form, "vehicle": vehicle}, request=request)
        return HttpResponse(html)
    return render(request, "fleet/fueling_form.html", {
        "form": form, "vehicle": vehicle, "title": _("Add Fueling")
    })


@perm_required('fleet.change_vehicle')
def fueling_edit(request, pk):
    fuel = get_object_or_404(VehicleFueling, pk=pk)
    if request.method == "POST":
        form = VehicleFuelingForm(request.POST, instance=fuel)
        if form.is_valid():
            form.save()
            if _is_ajax(request):
                return JsonResponse({"ok": True})
            return redirect("fleet:vehicle_detail", pk=fuel.vehicle_id)
        if _is_ajax(request):
            html = render_to_string("fleet/partials/fueling_form.html",
                                    {"form": form, "vehicle": fuel.vehicle}, request=request)
            return JsonResponse({"ok": False, "html": html})
    else:
        form = VehicleFuelingForm(instance=fuel)
    if _is_ajax(request):
        html = render_to_string("fleet/partials/fueling_form.html",
                                {"form": form, "vehicle": fuel.vehicle}, request=request)
        return HttpResponse(html)
    return render(request, "fleet/fueling_form.html", {
        "form": form, "fuel": fuel, "vehicle": fuel.vehicle, "title": _("Edit Fueling")
    })


# ── MULTAS ────────────────────────────────────────────────────────────────────
@perm_required('fleet.view_vehicle')
def fine_list(request):
    fines = VehicleFine.objects.select_related("vehicle", "driver").order_by("-date")
    status_filter = request.GET.get("status", "")
    if status_filter:
        fines = fines.filter(status=status_filter)
    payroll_only = request.GET.get("payroll", "")
    if payroll_only:
        fines = fines.filter(deduct_from_payroll=True, payroll_deducted=False)
    return render(request, "fleet/fine_list.html", {
        "fines": fines,
        "status_filter": status_filter,
        "payroll_only": payroll_only,
        "status_choices": VehicleFine.STATUS_CHOICES,
    })


@perm_required('fleet.change_vehicle')
def fine_create(request, vehicle_pk):
    vehicle = get_object_or_404(Vehicle, pk=vehicle_pk)
    if request.method == "POST":
        form = VehicleFineForm(request.POST, request.FILES)
        if form.is_valid():
            fine = form.save(commit=False)
            fine.vehicle = vehicle
            fine.save()
            if _is_ajax(request):
                return JsonResponse({"ok": True})
            return redirect("fleet:vehicle_detail", pk=vehicle.pk)
        if _is_ajax(request):
            html = render_to_string("fleet/partials/fine_form.html",
                                    {"form": form, "vehicle": vehicle}, request=request)
            return JsonResponse({"ok": False, "html": html})
    else:
        form = VehicleFineForm()
    if _is_ajax(request):
        html = render_to_string("fleet/partials/fine_form.html",
                                {"form": form, "vehicle": vehicle}, request=request)
        return HttpResponse(html)
    return render(request, "fleet/fine_form.html", {
        "form": form, "vehicle": vehicle, "title": _("Add Fine")
    })


@perm_required('fleet.change_vehicle')
def fine_edit(request, pk):
    fine = get_object_or_404(VehicleFine, pk=pk)
    if request.method == "POST":
        form = VehicleFineForm(request.POST, request.FILES, instance=fine)
        if form.is_valid():
            form.save()
            if _is_ajax(request):
                return JsonResponse({"ok": True})
            return redirect("fleet:vehicle_detail", pk=fine.vehicle_id)
        if _is_ajax(request):
            html = render_to_string("fleet/partials/fine_form.html",
                                    {"form": form, "vehicle": fine.vehicle}, request=request)
            return JsonResponse({"ok": False, "html": html})
    else:
        form = VehicleFineForm(instance=fine)
    if _is_ajax(request):
        html = render_to_string("fleet/partials/fine_form.html",
                                {"form": form, "vehicle": fine.vehicle}, request=request)
        return HttpResponse(html)
    return render(request, "fleet/fine_form.html", {
        "form": form, "fine": fine, "vehicle": fine.vehicle, "title": _("Edit Fine")
    })


# ── DESPESAS ──────────────────────────────────────────────────────────────────
@perm_required('fleet.change_vehicle')
def expense_create(request, vehicle_pk):
    vehicle = get_object_or_404(Vehicle, pk=vehicle_pk)
    if request.method == "POST":
        form = VehicleExpenseForm(request.POST)
        if form.is_valid():
            exp = form.save(commit=False)
            exp.vehicle = vehicle
            exp.save()
            if _is_ajax(request):
                return JsonResponse({"ok": True})
            return redirect("fleet:vehicle_detail", pk=vehicle.pk)
        if _is_ajax(request):
            html = render_to_string("fleet/partials/expense_form.html",
                                    {"form": form, "vehicle": vehicle}, request=request)
            return JsonResponse({"ok": False, "html": html})
    else:
        form = VehicleExpenseForm()
    if _is_ajax(request):
        html = render_to_string("fleet/partials/expense_form.html",
                                {"form": form, "vehicle": vehicle}, request=request)
        return HttpResponse(html)
    return render(request, "fleet/expense_form.html", {
        "form": form, "vehicle": vehicle, "title": _("Add Expense")
    })


@perm_required('fleet.change_vehicle')
def expense_edit(request, pk):
    exp = get_object_or_404(VehicleExpense, pk=pk)
    if request.method == "POST":
        form = VehicleExpenseForm(request.POST, instance=exp)
        if form.is_valid():
            form.save()
            if _is_ajax(request):
                return JsonResponse({"ok": True})
            return redirect("fleet:vehicle_detail", pk=exp.vehicle_id)
        if _is_ajax(request):
            html = render_to_string("fleet/partials/expense_form.html",
                                    {"form": form, "vehicle": exp.vehicle}, request=request)
            return JsonResponse({"ok": False, "html": html})
    else:
        form = VehicleExpenseForm(instance=exp)
    if _is_ajax(request):
        html = render_to_string("fleet/partials/expense_form.html",
                                {"form": form, "vehicle": exp.vehicle}, request=request)
        return HttpResponse(html)
    return render(request, "fleet/expense_form.html", {
        "form": form, "exp": exp, "vehicle": exp.vehicle, "title": _("Edit Expense")
    })

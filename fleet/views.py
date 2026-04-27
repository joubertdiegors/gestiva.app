from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.db.models import Sum, Q

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


# ── DASHBOARD ─────────────────────────────────────────────────────────────────
@login_required
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
@login_required
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


@login_required
def vehicle_detail(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk)
    today = timezone.now().date()
    in_60 = today + timezone.timedelta(days=60)

    docs = vehicle.documents.order_by("expiry_date")
    maintenances = vehicle.maintenances.order_by("-scheduled_date")[:10]
    fuelings = vehicle.fuelings.select_related("driver").order_by("-date")[:20]
    fines = vehicle.fines.select_related("driver").order_by("-date")
    expenses = vehicle.expenses.select_related("driver").order_by("-date")[:20]

    total_cost = (
        (vehicle.maintenances.filter(status=VehicleMaintenance.STATUS_DONE)
         .aggregate(s=Sum("cost"))["s"] or 0)
        + (vehicle.fuelings.aggregate(s=Sum("total_cost"))["s"] or 0)
        + (vehicle.fines.aggregate(s=Sum("amount"))["s"] or 0)
        + (vehicle.expenses.aggregate(s=Sum("amount"))["s"] or 0)
    )

    return render(request, "fleet/vehicle_detail.html", {
        "vehicle": vehicle,
        "docs": docs,
        "maintenances": maintenances,
        "fuelings": fuelings,
        "fines": fines,
        "expenses": expenses,
        "total_cost": total_cost,
        "today": today,
        "in_60": in_60,
    })


@login_required
def vehicle_create(request):
    if request.method == "POST":
        form = VehicleForm(request.POST)
        if form.is_valid():
            vehicle = form.save()
            return redirect("fleet:vehicle_detail", pk=vehicle.pk)
    else:
        form = VehicleForm()
    return render(request, "fleet/vehicle_form.html", {"form": form, "title": _("New Vehicle")})


@login_required
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
@login_required
def category_list(request):
    categories = VehicleCategory.objects.all()
    return render(request, "fleet/category_list.html", {"categories": categories})


@login_required
def category_create(request):
    if request.method == "POST":
        form = VehicleCategoryForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("fleet:category_list")
    else:
        form = VehicleCategoryForm()
    return render(request, "fleet/category_form.html", {"form": form, "title": _("New Category")})


@login_required
def category_edit(request, pk):
    category = get_object_or_404(VehicleCategory, pk=pk)
    if request.method == "POST":
        form = VehicleCategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            return redirect("fleet:category_list")
    else:
        form = VehicleCategoryForm(instance=category)
    return render(request, "fleet/category_form.html", {
        "form": form, "category": category, "title": _("Edit Category")
    })


# ── DOCUMENTOS ────────────────────────────────────────────────────────────────
@login_required
def document_create(request, vehicle_pk):
    vehicle = get_object_or_404(Vehicle, pk=vehicle_pk)
    if request.method == "POST":
        form = VehicleDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.vehicle = vehicle
            doc.save()
            return redirect("fleet:vehicle_detail", pk=vehicle.pk)
    else:
        form = VehicleDocumentForm()
    return render(request, "fleet/document_form.html", {
        "form": form, "vehicle": vehicle, "title": _("Add Document")
    })


@login_required
def document_edit(request, pk):
    doc = get_object_or_404(VehicleDocument, pk=pk)
    if request.method == "POST":
        form = VehicleDocumentForm(request.POST, request.FILES, instance=doc)
        if form.is_valid():
            form.save()
            return redirect("fleet:vehicle_detail", pk=doc.vehicle_id)
    else:
        form = VehicleDocumentForm(instance=doc)
    return render(request, "fleet/document_form.html", {
        "form": form, "doc": doc, "vehicle": doc.vehicle, "title": _("Edit Document")
    })


# ── MANUTENÇÕES ───────────────────────────────────────────────────────────────
@login_required
def maintenance_create(request, vehicle_pk):
    vehicle = get_object_or_404(Vehicle, pk=vehicle_pk)
    if request.method == "POST":
        form = VehicleMaintenanceForm(request.POST)
        if form.is_valid():
            maint = form.save(commit=False)
            maint.vehicle = vehicle
            maint.save()
            return redirect("fleet:vehicle_detail", pk=vehicle.pk)
    else:
        form = VehicleMaintenanceForm()
    return render(request, "fleet/maintenance_form.html", {
        "form": form, "vehicle": vehicle, "title": _("Add Maintenance")
    })


@login_required
def maintenance_edit(request, pk):
    maint = get_object_or_404(VehicleMaintenance, pk=pk)
    if request.method == "POST":
        form = VehicleMaintenanceForm(request.POST, instance=maint)
        if form.is_valid():
            form.save()
            return redirect("fleet:vehicle_detail", pk=maint.vehicle_id)
    else:
        form = VehicleMaintenanceForm(instance=maint)
    return render(request, "fleet/maintenance_form.html", {
        "form": form, "maint": maint, "vehicle": maint.vehicle, "title": _("Edit Maintenance")
    })


# ── ABASTECIMENTOS ────────────────────────────────────────────────────────────
@login_required
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
            return redirect("fleet:vehicle_detail", pk=vehicle.pk)
    else:
        form = VehicleFuelingForm()
    return render(request, "fleet/fueling_form.html", {
        "form": form, "vehicle": vehicle, "title": _("Add Fueling")
    })


@login_required
def fueling_edit(request, pk):
    fuel = get_object_or_404(VehicleFueling, pk=pk)
    if request.method == "POST":
        form = VehicleFuelingForm(request.POST, instance=fuel)
        if form.is_valid():
            form.save()
            return redirect("fleet:vehicle_detail", pk=fuel.vehicle_id)
    else:
        form = VehicleFuelingForm(instance=fuel)
    return render(request, "fleet/fueling_form.html", {
        "form": form, "fuel": fuel, "vehicle": fuel.vehicle, "title": _("Edit Fueling")
    })


# ── MULTAS ────────────────────────────────────────────────────────────────────
@login_required
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


@login_required
def fine_create(request, vehicle_pk):
    vehicle = get_object_or_404(Vehicle, pk=vehicle_pk)
    if request.method == "POST":
        form = VehicleFineForm(request.POST, request.FILES)
        if form.is_valid():
            fine = form.save(commit=False)
            fine.vehicle = vehicle
            fine.save()
            return redirect("fleet:vehicle_detail", pk=vehicle.pk)
    else:
        form = VehicleFineForm()
    return render(request, "fleet/fine_form.html", {
        "form": form, "vehicle": vehicle, "title": _("Add Fine")
    })


@login_required
def fine_edit(request, pk):
    fine = get_object_or_404(VehicleFine, pk=pk)
    if request.method == "POST":
        form = VehicleFineForm(request.POST, request.FILES, instance=fine)
        if form.is_valid():
            form.save()
            return redirect("fleet:vehicle_detail", pk=fine.vehicle_id)
    else:
        form = VehicleFineForm(instance=fine)
    return render(request, "fleet/fine_form.html", {
        "form": form, "fine": fine, "vehicle": fine.vehicle, "title": _("Edit Fine")
    })


# ── DESPESAS ──────────────────────────────────────────────────────────────────
@login_required
def expense_create(request, vehicle_pk):
    vehicle = get_object_or_404(Vehicle, pk=vehicle_pk)
    if request.method == "POST":
        form = VehicleExpenseForm(request.POST)
        if form.is_valid():
            exp = form.save(commit=False)
            exp.vehicle = vehicle
            exp.save()
            return redirect("fleet:vehicle_detail", pk=vehicle.pk)
    else:
        form = VehicleExpenseForm()
    return render(request, "fleet/expense_form.html", {
        "form": form, "vehicle": vehicle, "title": _("Add Expense")
    })


@login_required
def expense_edit(request, pk):
    exp = get_object_or_404(VehicleExpense, pk=pk)
    if request.method == "POST":
        form = VehicleExpenseForm(request.POST, instance=exp)
        if form.is_valid():
            form.save()
            return redirect("fleet:vehicle_detail", pk=exp.vehicle_id)
    else:
        form = VehicleExpenseForm(instance=exp)
    return render(request, "fleet/expense_form.html", {
        "form": form, "exp": exp, "vehicle": exp.vehicle, "title": _("Edit Expense")
    })

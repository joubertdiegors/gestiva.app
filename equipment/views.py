from django.shortcuts import render, get_object_or_404, redirect
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.db.models import Q, Count
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST

from accounts.decorators import perm_required
from .models import Equipment, EquipmentCategory, EquipmentLoan, EquipmentSale
from .forms import (
    EquipmentForm,
    EquipmentCategoryForm,
    EquipmentLoanForm,
    EquipmentReturnForm,
    EquipmentSaleForm,
)


# ── LISTA DE EQUIPAMENTOS ─────────────────────────────────────────────────────
@perm_required('equipment.view_equipment')
def equipment_list(request):
    qs = Equipment.objects.select_related("category").all()
    status_filter = request.GET.get("status", "")
    if status_filter:
        qs = qs.filter(status=status_filter)
    category_filter = request.GET.get("category", "")
    if category_filter:
        qs = qs.filter(category_id=category_filter)
    q = request.GET.get("q", "")
    if q:
        qs = qs.filter(
            Q(name__icontains=q)
            | Q(brand__icontains=q)
            | Q(model__icontains=q)
            | Q(serial_number__icontains=q)
            | Q(internal_code__icontains=q)
        )
    categories = EquipmentCategory.objects.all()
    return render(request, "equipment/equipment_list.html", {
        "equipments": qs,
        "status_filter": status_filter,
        "category_filter": category_filter,
        "q": q,
        "status_choices": Equipment.STATUS_CHOICES,
        "categories": categories,
    })


# ── DETALHE DO EQUIPAMENTO ────────────────────────────────────────────────────
@perm_required('equipment.view_equipment')
def equipment_detail(request, pk):
    equipment = get_object_or_404(Equipment, pk=pk)
    loans = equipment.loans.select_related("collaborator").order_by("-loaned_at")
    active_loan = equipment.active_loan
    sale = getattr(equipment, "sale", None)
    return render(request, "equipment/equipment_detail.html", {
        "equipment": equipment,
        "loans": loans,
        "active_loan": active_loan,
        "sale": sale,
        "today": timezone.now().date(),
    })


# ── CRIAR EQUIPAMENTO ─────────────────────────────────────────────────────────
@perm_required('equipment.add_equipment')
def equipment_create(request):
    if request.method == "POST":
        form = EquipmentForm(request.POST)
        if form.is_valid():
            eq = form.save()
            return redirect("equipment:detail", pk=eq.pk)
    else:
        form = EquipmentForm()
    return render(request, "equipment/equipment_form.html", {
        "form": form, "title": _("New Equipment")
    })


# ── EDITAR EQUIPAMENTO ────────────────────────────────────────────────────────
@perm_required('equipment.change_equipment')
def equipment_edit(request, pk):
    equipment = get_object_or_404(Equipment, pk=pk)
    if request.method == "POST":
        form = EquipmentForm(request.POST, instance=equipment)
        if form.is_valid():
            form.save()
            return redirect("equipment:detail", pk=equipment.pk)
    else:
        form = EquipmentForm(instance=equipment)
    return render(request, "equipment/equipment_form.html", {
        "form": form, "equipment": equipment, "title": _("Edit Equipment")
    })


# ── CATEGORIAS ────────────────────────────────────────────────────────────────
@perm_required('equipment.view_equipment')
def category_list(request):
    categories = (
        EquipmentCategory.objects
        .annotate(equipment_count=Count("equipments"))
        .order_by("name")
    )
    return render(request, "equipment/category_list.html", {"categories": categories})


@perm_required('equipment.change_equipment')
@require_POST
def category_save(request, pk=None):
    instance = get_object_or_404(EquipmentCategory, pk=pk) if pk else None
    form = EquipmentCategoryForm(request.POST, instance=instance)
    if form.is_valid():
        cat = form.save()
        return JsonResponse({
            "ok": True,
            "category": {
                "id": cat.pk,
                "name": cat.name,
                "equipment_count": cat.equipments.count(),
            },
        })
    return JsonResponse({"ok": False, "errors": form.errors}, status=400)


@perm_required('equipment.delete_equipment')
@require_POST
def category_delete(request, pk):
    cat = get_object_or_404(EquipmentCategory, pk=pk)
    if cat.equipments.exists():
        return JsonResponse(
            {"ok": False, "error": str(_("This category has associated equipment."))},
            status=400,
        )
    cat.delete()
    return JsonResponse({"ok": True})


# ── EMPRÉSTIMO ────────────────────────────────────────────────────────────────
@perm_required('equipment.change_equipment')
def loan_create(request, equipment_pk):
    equipment = get_object_or_404(Equipment, pk=equipment_pk)
    if equipment.status != Equipment.STATUS_AVAILABLE:
        return redirect("equipment:detail", pk=equipment.pk)

    if request.method == "POST":
        form = EquipmentLoanForm(request.POST)
        if form.is_valid():
            loan = form.save(commit=False)
            loan.equipment = equipment
            loan.save()
            # Atualiza status do equipamento
            equipment.status = Equipment.STATUS_LOANED
            equipment.save(update_fields=["status", "updated_at"])
            return redirect("equipment:loan_ticket", pk=loan.pk)
    else:
        form = EquipmentLoanForm(initial={"loaned_at": timezone.now().strftime("%Y-%m-%dT%H:%M")})
    return render(request, "equipment/loan_form.html", {
        "form": form, "equipment": equipment, "title": _("Loan Equipment")
    })


# ── DEVOLUÇÃO ─────────────────────────────────────────────────────────────────
@perm_required('equipment.change_equipment')
def loan_return(request, pk):
    loan = get_object_or_404(EquipmentLoan, pk=pk)
    if not loan.is_active:
        return redirect("equipment:detail", pk=loan.equipment_id)

    if request.method == "POST":
        form = EquipmentReturnForm(request.POST, instance=loan)
        if form.is_valid():
            form.save()
            loan.equipment.status = Equipment.STATUS_AVAILABLE
            loan.equipment.save(update_fields=["status", "updated_at"])
            return redirect("equipment:detail", pk=loan.equipment_id)
    else:
        form = EquipmentReturnForm(
            instance=loan,
            initial={"returned_at": timezone.now().strftime("%Y-%m-%dT%H:%M")},
        )
    return render(request, "equipment/loan_return_form.html", {
        "form": form, "loan": loan, "equipment": loan.equipment
    })


# ── TICKET DE EMPRÉSTIMO (impressão térmica) ──────────────────────────────────
@perm_required('equipment.view_equipment')
def loan_ticket(request, pk):
    loan = get_object_or_404(EquipmentLoan.objects.select_related("equipment", "collaborator"), pk=pk)
    if not loan.ticket_printed:
        EquipmentLoan.objects.filter(pk=pk).update(ticket_printed=True)
        loan.ticket_printed = True
    return render(request, "equipment/loan_ticket.html", {"loan": loan})


# ── VENDA A FUNCIONÁRIO ───────────────────────────────────────────────────────
@perm_required('equipment.change_equipment')
def sale_create(request, equipment_pk):
    equipment = get_object_or_404(Equipment, pk=equipment_pk)
    if hasattr(equipment, "sale"):
        return redirect("equipment:detail", pk=equipment.pk)

    if request.method == "POST":
        form = EquipmentSaleForm(request.POST)
        if form.is_valid():
            sale = form.save(commit=False)
            sale.equipment = equipment
            sale.save()
            equipment.status = Equipment.STATUS_SOLD
            equipment.save(update_fields=["status", "updated_at"])
            return redirect("equipment:detail", pk=equipment.pk)
    else:
        form = EquipmentSaleForm(initial={
            "sale_date": timezone.now().date(),
            "sale_price": equipment.purchase_price,
        })
    return render(request, "equipment/sale_form.html", {
        "form": form, "equipment": equipment, "title": _("Sell to Collaborator")
    })


@perm_required('equipment.change_equipment')
def sale_edit(request, pk):
    sale = get_object_or_404(EquipmentSale, pk=pk)
    if request.method == "POST":
        form = EquipmentSaleForm(request.POST, instance=sale)
        if form.is_valid():
            form.save()
            return redirect("equipment:detail", pk=sale.equipment_id)
    else:
        form = EquipmentSaleForm(instance=sale)
    return render(request, "equipment/sale_form.html", {
        "form": form, "sale": sale, "equipment": sale.equipment, "title": _("Edit Sale")
    })


# ── LISTA DE EMPRÉSTIMOS ATIVOS ───────────────────────────────────────────────
@perm_required('equipment.view_equipment')
def loan_list(request):
    loans = (
        EquipmentLoan.objects
        .filter(returned_at__isnull=True)
        .select_related("equipment", "equipment__category", "collaborator")
        .order_by("-loaned_at")
    )
    overdue = [l for l in loans if l.is_overdue]
    return render(request, "equipment/loan_list.html", {
        "loans": loans,
        "overdue": overdue,
        "today": timezone.now().date(),
    })

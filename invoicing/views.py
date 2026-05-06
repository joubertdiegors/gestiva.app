import datetime
import re
from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.db import transaction
from django.db.models import Max
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from catalog.models import UnitOfMeasure
from clients.models import Client
from projects.models import Project

from accounts.decorators import perm_required
from .models import Invoice, InvoiceLine


# ── LIST ──────────────────────────────────────────────────────────────────────
@perm_required('invoicing.view_invoice')
def invoice_list(request):
    qs = (
        Invoice.objects
        .select_related('client', 'project')
        .prefetch_related('lines')
        .order_by('-issue_date', '-number')
    )
    status_filter = request.GET.get('status', '')
    if status_filter:
        qs = qs.filter(status=status_filter)

    invoices = list(qs)
    for inv in invoices:
        inv.total_ttc_cached = inv.total_ttc

    clients  = Client.objects.filter(is_active=True).order_by('name')
    projects = list(Project.objects.order_by('name').values('id', 'name', 'client_id', 'status'))

    return render(request, 'invoicing/invoice_list.html', {
        'invoices':       invoices,
        'status_filter':  status_filter,
        'status_choices': Invoice.Status.choices,
        'clients':        clients,
        'projects':       projects,
    })


# ── CREATE ────────────────────────────────────────────────────────────────────
@perm_required('invoicing.add_invoice')
def invoice_create(request):
    clients    = Client.objects.filter(is_active=True).order_by('name')
    projects   = Project.objects.select_related('client').order_by('-created_at')
    units      = list(UnitOfMeasure.objects.order_by('symbol').values('symbol', 'name'))

    # Pre-fill from wizard query params
    pre_type       = request.GET.get('type', Invoice.InvoiceType.DIRECT)
    pre_client_id  = request.GET.get('client', '')
    pre_project_id = request.GET.get('project', '')

    pre_client = None
    pre_project = None
    pre_client_contacts = []
    pre_client_address  = None
    if pre_client_id:
        try:
            pre_client = Client.objects.prefetch_related('addresses', 'contacts').get(pk=pre_client_id)
            pre_client_address  = pre_client.addresses.first()
            pre_client_contacts = list(pre_client.contacts.all()[:3])
        except Client.DoesNotExist:
            pass
    if pre_project_id:
        try:
            pre_project = Project.objects.get(pk=pre_project_id)
        except Project.DoesNotExist:
            pass

    if request.method == 'POST':
        data = request.POST
        errors = {}

        client_id  = data.get('client_id', '').strip()
        issue_date = data.get('issue_date', '').strip()
        if not client_id:
            errors['client_id'] = 'Selecione um cliente.'
        if not issue_date:
            errors['issue_date'] = 'Informe a data de emissão.'

        if not errors:
            inv = Invoice(
                number               = Invoice.next_number(),
                title                = data.get('title', '').strip(),
                client_id            = client_id,
                issue_date           = issue_date,
                due_date             = data.get('due_date') or None,
                status               = Invoice.Status.DRAFT,
                invoice_type         = data.get('invoice_type', Invoice.InvoiceType.DIRECT),
                bon_de_facturation   = data.get('bon_de_facturation', '').strip(),
                authorization_date   = data.get('authorization_date') or None,
                authorization_contact = data.get('authorization_contact', '').strip(),
                work_start_date      = data.get('work_start_date') or None,
                work_end_date        = data.get('work_end_date') or None,
                execution_notes      = data.get('execution_notes', '').strip(),
                billing_name         = data.get('billing_name', '').strip(),
                billing_address      = data.get('billing_address', '').strip(),
                billing_vat          = data.get('billing_vat', '').strip(),
                payment_terms        = data.get('payment_terms', '').strip(),
                notes_internal       = data.get('notes_internal', '').strip(),
                notes_client         = data.get('notes_client', '').strip(),
                created_by           = request.user,
            )
            project_id = data.get('project_id', '').strip()
            if project_id:
                inv.project_id = project_id
            try:
                inv.discount_percent = Decimal(data.get('discount_percent') or '0')
                inv.vat_rate         = Decimal(data.get('vat_rate') or '21')
            except InvalidOperation:
                pass
            inv.save()
            return redirect('invoicing:detail', pk=inv.pk)

    return render(request, 'invoicing/invoice_form.html', {
        'clients':              clients,
        'projects':             projects,
        'units':                units,
        'today':                datetime.date.today().isoformat(),
        'pre_type':             pre_type,
        'pre_client_id':        pre_client_id,
        'pre_project_id':       pre_project_id,
        'pre_client':           pre_client,
        'pre_project':          pre_project,
        'pre_client_address':   pre_client_address,
        'pre_client_contacts':  pre_client_contacts,
        'type_choices':         Invoice.InvoiceType.choices,
    })


# ── DETAIL ────────────────────────────────────────────────────────────────────
@perm_required('invoicing.view_invoice')
def invoice_detail(request, pk):
    invoice = get_object_or_404(
        Invoice.objects.select_related('client', 'project', 'budget', 'created_by'),
        pk=pk,
    )
    lines = list(invoice.lines.order_by('order'))
    units = list(UnitOfMeasure.objects.order_by('symbol').values('symbol', 'name'))

    # Compute hierarchical numbering
    _assign_line_numbers(lines)

    # Try to load receivable if it exists
    try:
        receivable = invoice.receivable
    except Exception:
        receivable = None

    return render(request, 'invoicing/invoice_detail.html', {
        'invoice':    invoice,
        'lines':      lines,
        'units':      units,
        'receivable': receivable,
        'can_send':   invoice.status == Invoice.Status.DRAFT,
        'can_cancel': invoice.status not in (Invoice.Status.PAID, Invoice.Status.CANCELLED),
    })


# ── UPDATE (header only) ──────────────────────────────────────────────────────
@perm_required('invoicing.change_invoice')
def invoice_update(request, pk):
    invoice  = get_object_or_404(Invoice, pk=pk)
    clients  = Client.objects.filter(is_active=True).order_by('name')
    projects = Project.objects.select_related('client').order_by('-created_at')
    units    = list(UnitOfMeasure.objects.order_by('symbol').values('symbol', 'name'))

    if request.method == 'POST':
        data = request.POST
        invoice.title                = data.get('title', '').strip()
        invoice.client_id            = data.get('client_id')
        invoice.issue_date           = data.get('issue_date')
        invoice.due_date             = data.get('due_date') or None
        invoice.invoice_type         = data.get('invoice_type', invoice.invoice_type)
        invoice.bon_de_facturation   = data.get('bon_de_facturation', '').strip()
        invoice.authorization_date   = data.get('authorization_date') or None
        invoice.authorization_contact = data.get('authorization_contact', '').strip()
        invoice.work_start_date      = data.get('work_start_date') or None
        invoice.work_end_date        = data.get('work_end_date') or None
        invoice.execution_notes      = data.get('execution_notes', '').strip()
        invoice.billing_name         = data.get('billing_name', '').strip()
        invoice.billing_address      = data.get('billing_address', '').strip()
        invoice.billing_vat          = data.get('billing_vat', '').strip()
        invoice.payment_terms        = data.get('payment_terms', '').strip()
        invoice.notes_internal       = data.get('notes_internal', '').strip()
        invoice.notes_client         = data.get('notes_client', '').strip()
        project_id = data.get('project_id', '').strip()
        invoice.project_id = project_id or None
        try:
            invoice.discount_percent = Decimal(data.get('discount_percent') or '0')
            invoice.vat_rate         = Decimal(data.get('vat_rate') or '21')
        except InvalidOperation:
            pass
        invoice.save()
        return redirect('invoicing:detail', pk=invoice.pk)

    return render(request, 'invoicing/invoice_form.html', {
        'invoice':        invoice,
        'clients':        clients,
        'projects':       projects,
        'units':          units,
        'today':          datetime.date.today().isoformat(),
        'type_choices':   Invoice.InvoiceType.choices,
        'pre_type':       invoice.invoice_type,
        'pre_client_id':  str(invoice.client_id),
        'pre_project_id': str(invoice.project_id) if invoice.project_id else '',
    })


# ── ACTION: MARK SENT ─────────────────────────────────────────────────────────
@perm_required('invoicing.change_invoice')
@require_POST
def invoice_mark_sent(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    if invoice.status == Invoice.Status.DRAFT:
        invoice.status  = Invoice.Status.SENT
        invoice.sent_at = timezone.now()
        invoice.save(update_fields=['status', 'sent_at', 'updated_at'])
        _ensure_receivable(invoice)
    return redirect('invoicing:detail', pk=pk)


# ── ACTION: CANCEL ────────────────────────────────────────────────────────────
@perm_required('invoicing.change_invoice')
@require_POST
def invoice_cancel(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    if invoice.status not in (Invoice.Status.PAID, Invoice.Status.CANCELLED):
        invoice.status = Invoice.Status.CANCELLED
        invoice.save(update_fields=['status', 'updated_at'])
    return redirect('invoicing:detail', pk=pk)


# ── AJAX: AJAX projects by client ─────────────────────────────────────────────
@perm_required('invoicing.view_invoice')
def ajax_projects_by_client(request):
    client_id = request.GET.get('client_id', '')
    projects  = Project.objects.filter(client_id=client_id).values('id', 'name')
    return JsonResponse(list(projects), safe=False)


# ── AJAX: LINE SAVE ───────────────────────────────────────────────────────────
@perm_required('invoicing.change_invoice')
@require_POST
def line_save(request, pk):
    invoice  = get_object_or_404(Invoice, pk=pk)
    data     = request.POST
    entry_pk = data.get('entry_pk') or None
    line_type = data.get('line_type', InvoiceLine.LineType.LINE)

    errors = {}
    description = data.get('description', '').strip()
    # Page break doesn't need description
    if not description and line_type != InvoiceLine.LineType.PAGE_BREAK:
        errors['description'] = ['Campo obrigatório.']

    is_numeric = line_type in (InvoiceLine.LineType.LINE,)

    def _dec(key, default='0'):
        try:
            return Decimal(data.get(key, default) or default)
        except InvalidOperation:
            errors[key] = ['Número inválido.']
            return Decimal(default)

    quantity         = _dec('quantity', '1') if is_numeric else Decimal('0')
    unit_price       = _dec('unit_price', '0') if is_numeric else Decimal('0')
    discount_percent = _dec('discount_percent', '0') if is_numeric else Decimal('0')
    vat_rate         = _dec('vat_rate', str(invoice.vat_rate)) if is_numeric else Decimal('0')

    if errors:
        return JsonResponse({'ok': False, 'errors': errors})

    if entry_pk:
        line = get_object_or_404(InvoiceLine, pk=entry_pk, invoice=invoice)
    else:
        last_order = invoice.lines.aggregate(m=Max('order'))['m'] or 0
        line = InvoiceLine(invoice=invoice, order=last_order + 10)

    line.line_type        = line_type
    line.description      = description
    line.detail           = data.get('detail', '').strip() if is_numeric else ''
    line.quantity         = quantity
    line.unit             = data.get('unit', '').strip() if is_numeric else ''
    line.unit_price       = unit_price
    line.discount_percent = discount_percent
    line.vat_rate         = vat_rate
    line.save()

    return JsonResponse({'ok': True, 'line': _line_json(line), 'totals': _invoice_totals(invoice)})


# ── AJAX: LINE DELETE ─────────────────────────────────────────────────────────
@perm_required('invoicing.change_invoice')
@require_POST
def line_delete(request, pk, line_pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    line    = get_object_or_404(InvoiceLine, pk=line_pk, invoice=invoice)
    line.delete()
    return JsonResponse({'ok': True, 'totals': _invoice_totals(invoice)})


# ── AJAX: LINE DUPLICATE ──────────────────────────────────────────────────────
@perm_required('invoicing.change_invoice')
@require_POST
def line_duplicate(request, pk, line_pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    src     = get_object_or_404(InvoiceLine, pk=line_pk, invoice=invoice)
    last_order = invoice.lines.aggregate(m=Max('order'))['m'] or 0
    new_line = InvoiceLine(
        invoice          = invoice,
        order            = last_order + 10,
        line_type        = src.line_type,
        description      = src.description,
        detail           = src.detail,
        quantity         = src.quantity,
        unit             = src.unit,
        unit_price       = src.unit_price,
        discount_percent = src.discount_percent,
        vat_rate         = src.vat_rate,
    )
    new_line.save()
    return JsonResponse({'ok': True, 'line': _line_json(new_line), 'totals': _invoice_totals(invoice)})


# ── AJAX: LINE REORDER ────────────────────────────────────────────────────────
@perm_required('invoicing.change_invoice')
@require_POST
def line_reorder(request, pk):
    import json
    invoice = get_object_or_404(Invoice, pk=pk)
    try:
        order_list = json.loads(request.body)  # [{id, order}, ...]
    except (ValueError, KeyError):
        return JsonResponse({'ok': False, 'error': 'Invalid payload'})
    with transaction.atomic():
        for item in order_list:
            invoice.lines.filter(pk=item['id']).update(order=item['order'])
    return JsonResponse({'ok': True})


# ── Helpers ───────────────────────────────────────────────────────────────────
def _invoice_totals(invoice):
    inv_lines    = list(invoice.lines.all())
    subtotal_ht  = sum(l.total_ht for l in inv_lines)
    discount_amt = (subtotal_ht * invoice.discount_percent / Decimal('100')).quantize(Decimal('0.01'))
    total_ht     = subtotal_ht - discount_amt
    total_vat    = sum(l.vat_amount for l in inv_lines)
    total_ttc    = total_ht + total_vat
    return {
        'subtotal_ht':  str(subtotal_ht),
        'discount_amt': str(discount_amt),
        'total_ht':     str(total_ht),
        'total_vat':    str(total_vat),
        'total_ttc':    str(total_ttc),
    }


def _line_json(line):
    return {
        'id':               line.pk,
        'order':            line.order,
        'line_type':        line.line_type,
        'description':      line.description,
        'detail':           line.detail,
        'quantity':         str(line.quantity),
        'unit':             line.unit,
        'unit_price':       str(line.unit_price),
        'discount_percent': str(line.discount_percent),
        'vat_rate':         str(line.vat_rate),
        'total_ht':         str(line.total_ht),
        'vat_amount':       str(line.vat_amount),
        'total_ttc':        str(line.total_ttc),
    }


def _assign_line_numbers(lines):
    """Compute hierarchical display numbers in-place (stored in line.display_number)."""
    # c[0]=title, c[1]=h2, c[2]=h3, c[3]=h4
    c = [0, 0, 0, 0]
    for line in lines:
        lt = line.line_type
        if lt == 'title':
            c[0] += 1; c[1] = c[2] = c[3] = 0
            line.display_number = str(c[0])
        elif lt == 'h2':
            c[1] += 1; c[2] = c[3] = 0
            line.display_number = f'{c[0]}.{c[1]}' if c[0] else str(c[1])
        elif lt == 'h3':
            c[2] += 1; c[3] = 0
            parts = []
            if c[0]: parts.append(str(c[0]))
            parts.append(str(c[1])); parts.append(str(c[2]))
            line.display_number = '.'.join(parts)
        elif lt == 'h4':
            c[3] += 1
            parts = []
            if c[0]: parts.append(str(c[0]))
            parts.append(str(c[1])); parts.append(str(c[2])); parts.append(str(c[3]))
            line.display_number = '.'.join(parts)
        else:
            line.display_number = ''


def _ensure_receivable(invoice):
    """Create or update the Receivable when an invoice is sent."""
    from finance.models import Receivable
    rec, _ = Receivable.objects.get_or_create(
        invoice=invoice,
        defaults={
            'client':     invoice.client,
            'project':    invoice.project,
            'amount':     invoice.total_ttc,
            'issue_date': invoice.issue_date,
            'due_date':   invoice.due_date,
            'status':     Receivable.Status.PENDING,
        },
    )
    # Always refresh amount in case lines changed before sending
    if rec.amount != invoice.total_ttc:
        rec.amount = invoice.total_ttc
        rec.save(update_fields=['amount', 'updated_at'])


# ── PRINT ─────────────────────────────────────────────────────────────────────

@perm_required('invoicing.view_invoice')
def invoice_print(request, pk):
    invoice = get_object_or_404(
        Invoice.objects.select_related('client', 'project').prefetch_related(
            'lines', 'client__addresses', 'client__contacts',
        ),
        pk=pk,
    )

    # Load requested template or fall back to default invoice template
    tmpl = None
    tmpl_pk = request.GET.get('template')
    if tmpl_pk:
        try:
            from document_templates.models import DocumentTemplate
            tmpl = DocumentTemplate.objects.get(pk=tmpl_pk, document_type=DocumentTemplate.TYPE_INVOICE)
        except Exception:
            pass
    if tmpl is None:
        try:
            from document_templates.models import DocumentTemplate
            tmpl = (
                DocumentTemplate.objects.filter(
                    document_type=DocumentTemplate.TYPE_INVOICE,
                    status=DocumentTemplate.STATUS_ACTIVE,
                    is_default=True,
                ).first()
                or DocumentTemplate.objects.filter(
                    document_type=DocumentTemplate.TYPE_INVOICE,
                    status=DocumentTemplate.STATUS_ACTIVE,
                ).first()
            )
        except Exception:
            pass

    # Available invoice templates for selector
    try:
        from document_templates.models import DocumentTemplate
        tmpl_choices = list(
            DocumentTemplate.objects.filter(
                document_type=DocumentTemplate.TYPE_INVOICE,
                status=DocumentTemplate.STATUS_ACTIVE,
            ).values('pk', 'name', 'is_default')
        )
    except Exception:
        tmpl_choices = []

    # Build variable substitution dict
    client = invoice.client
    billing_addr = client.addresses.filter(is_default=True).first() or client.addresses.first()
    billing_contact = client.contacts.first()

    project = invoice.project
    company_name    = getattr(settings, 'COMPANY_NAME', 'Construart')
    company_address = getattr(settings, 'COMPANY_ADDRESS', '')
    company_postal  = getattr(settings, 'COMPANY_POSTAL_CODE', '')
    company_city    = getattr(settings, 'COMPANY_CITY', '')
    company_phone   = getattr(settings, 'COMPANY_PHONE', '')
    company_email   = getattr(settings, 'COMPANY_EMAIL', '')
    company_vat     = getattr(settings, 'COMPANY_VAT', '')
    company_legal   = getattr(settings, 'COMPANY_LEGAL_STATUS', '')

    subtotal_ht     = invoice.subtotal_ht
    discount_amount = invoice.discount_amount
    total_ht        = invoice.total_ht
    total_vat       = invoice.total_vat
    total_ttc       = invoice.total_ttc

    discount_row = ''
    if invoice.discount_percent:
        discount_row = (
            f'<tr><td>Desconto ({invoice.discount_percent}%)</td>'
            f'<td>- {discount_amount:,.2f} €</td></tr>'
        )

    totals_with_vat = (
        f'<table class="totals-tbl">'
        f'<tr><td>Subtotal HT</td><td>{subtotal_ht:,.2f} €</td></tr>'
        f'{discount_row}'
        f'<tr><td>Total HT</td><td>{total_ht:,.2f} €</td></tr>'
        f'<tr><td>IVA</td><td>{total_vat:,.2f} €</td></tr>'
        f'<tr class="grand-total"><td>Total TTC</td><td>{total_ttc:,.2f} €</td></tr>'
        f'</table>'
    )
    totals_without_vat = (
        f'<table class="totals-tbl">'
        f'<tr><td>Subtotal HT</td><td>{subtotal_ht:,.2f} €</td></tr>'
        f'{discount_row}'
        f'<tr class="grand-total"><td>Total HT</td><td>{total_ht:,.2f} €</td></tr>'
        f'</table>'
    )

    contact_name = ''
    if billing_contact:
        parts = []
        if hasattr(billing_contact, 'first_name') and billing_contact.first_name:
            parts.append(billing_contact.first_name)
        if hasattr(billing_contact, 'last_name') and billing_contact.last_name:
            parts.append(billing_contact.last_name)
        contact_name = ' '.join(parts)

    contact_email = getattr(billing_contact, 'email', '') or '' if billing_contact else ''
    contact_phone = getattr(billing_contact, 'phone', '') or '' if billing_contact else ''

    addr_street = ''
    addr_postal = ''
    addr_city   = ''
    if billing_addr:
        street = billing_addr.street or ''
        number = billing_addr.number or ''
        addr_street = f'{street}, {number}' if number else street
        addr_postal = billing_addr.postal_code or ''
        addr_city   = billing_addr.city or ''
    elif invoice.billing_address:
        addr_street = invoice.billing_address

    variables = {
        'numDocument':       invoice.number,
        'dateCreation':      invoice.issue_date.strftime('%d/%m/%Y') if invoice.issue_date else '',
        'dateRevision':      invoice.updated_at.strftime('%d/%m/%Y') if invoice.updated_at else '',
        'validiteOffre':     invoice.due_date.strftime('%d/%m/%Y') if invoice.due_date else '',
        'conditionsReglement': invoice.payment_terms or '',
        'acompte':           '',
        'estAvenant':        '',
        'numPage':           '1',
        'nombrePages':       '1',
        'blocTotauxAvecTVA':  totals_with_vat,
        'blocTotauxSansTVA':  totals_without_vat,
        'nomEntreprise':     company_name,
        'adresseEntreprise': company_address,
        'CPEntreprise':      company_postal,
        'villeEntreprise':   company_city,
        'telEntreprise':     company_phone,
        'emailEntreprise':   company_email,
        'numTVA':            company_vat,
        'statusJuridique':   company_legal,
        'logoEntreprise':    '',
        'nomTiers':          client.name,
        'civilite':          '',
        'nomComTiers':       contact_name,
        'civiliteTiers':     '',
        'adresseTiers':      addr_street,
        'CPTiers':           addr_postal,
        'villeTiers':        addr_city,
        'numTVATiers':       client.vat_number or invoice.billing_vat or '',
        'emailTiers':        contact_email,
        'telTiers':          contact_phone,
        'nomChantier':       project.name if project else '',
        'adresseChantier':   getattr(project, 'address', '') or '' if project else '',
        'CPChantier':        getattr(project, 'postal_code', '') or '' if project else '',
        'villeChantier':     getattr(project, 'city', '') or '' if project else '',
        'refChantier':       getattr(project, 'reference', '') or '' if project else '',
        'chefProjet':        '',
    }

    def substitute(html):
        if not html:
            return ''
        for key, val in variables.items():
            html = html.replace(f'@{key}', str(val) if val else '')
        html = re.sub(r'@[a-zA-Z][a-zA-Z0-9_]*', '', html)
        return html

    sections = {}
    if tmpl:
        sections = {
            'page_header':     substitute(tmpl.section_page_header),
            'header_generic':  substitute(tmpl.section_header_generic),
            'header_document': substitute(tmpl.section_header_document),
            'footer_document': substitute(tmpl.section_footer_document),
            'page_footer':     substitute(tmpl.section_page_footer),
            'custom_css':      tmpl.custom_css or '',
        }

    lines = invoice.lines.all().order_by('order')

    # Build hierarchical line numbering
    counters = [0, 0, 0, 0]
    numbered_lines = []
    for line in lines:
        lt = line.line_type
        num = ''
        if lt == 'title':
            counters[0] += 1
            counters[1] = counters[2] = counters[3] = 0
            num = str(counters[0])
        elif lt == 'h2':
            counters[1] += 1
            counters[2] = counters[3] = 0
            num = f'{counters[0]}.{counters[1]}'
        elif lt == 'h3':
            counters[2] += 1
            counters[3] = 0
            num = f'{counters[0]}.{counters[1]}.{counters[2]}'
        elif lt == 'h4':
            counters[3] += 1
            num = f'{counters[0]}.{counters[1]}.{counters[2]}.{counters[3]}'
        numbered_lines.append((line, num))

    return render(request, 'invoicing/invoice_print.html', {
        'invoice':      invoice,
        'lines':        numbered_lines,
        'sections':     sections,
        'tmpl':         tmpl,
        'tmpl_choices': tmpl_choices,
        'has_template': bool(tmpl),
    })

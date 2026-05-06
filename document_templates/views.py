import json
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST
from django.http import JsonResponse

from accounts.decorators import perm_required
from .models import DocumentTemplate, VARIABLES
from .forms import DocumentTemplateCreateForm, DocumentTemplateForm


# ── List ──────────────────────────────────────────────────────────────────────

@perm_required('document_templates.view_documenttemplate')
def template_list(request):
    doc_type = request.GET.get('type', '').strip()
    qs = DocumentTemplate.objects.all()
    if doc_type:
        qs = qs.filter(document_type=doc_type)
    return render(request, 'document_templates/template_list.html', {
        'templates':    qs,
        'type_choices': DocumentTemplate.TYPE_CHOICES,
        'filter_type':  doc_type,
    })


# ── Create ────────────────────────────────────────────────────────────────────

@perm_required('document_templates.add_documenttemplate')
def template_create(request):
    doc_type = request.GET.get('type', DocumentTemplate.TYPE_QUOTE)
    if request.method == 'POST':
        form = DocumentTemplateCreateForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.created_by = request.user
            obj.status = DocumentTemplate.STATUS_ACTIVE
            obj.save()
            return redirect('document_templates:editor', pk=obj.pk)
    else:
        form = DocumentTemplateCreateForm(initial={'document_type': doc_type})
    return render(request, 'document_templates/template_create.html', {
        'form': form,
        'type_choices': DocumentTemplate.TYPE_CHOICES,
        'selected_type': doc_type,
    })


# ── Editor ────────────────────────────────────────────────────────────────────

@perm_required('document_templates.change_documenttemplate')
def template_editor(request, pk):
    tmpl = get_object_or_404(DocumentTemplate, pk=pk)

    if request.method == 'POST':
        # Auto-save via AJAX — receives JSON body
        if request.content_type and 'application/json' in request.content_type:
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({'ok': False, 'error': 'Invalid JSON'}, status=400)

            allowed = [
                'section_page_header', 'section_page_footer',
                'section_header_generic', 'section_header_document',
                'section_footer_document', 'custom_css',
            ]
            for field in allowed:
                if field in data:
                    setattr(tmpl, field, data[field])
            tmpl.save()
            return JsonResponse({'ok': True})

        # Full form save (params panel)
        params_form = DocumentTemplateForm(request.POST, instance=tmpl)
        if params_form.is_valid():
            params_form.save()
        return redirect('document_templates:editor', pk=pk)

    params_form = DocumentTemplateForm(instance=tmpl)

    sections = [
        {'key': 'section_page_header',     'label': 'Cabeçalho de página (repetido)',    'icon': '↑', 'value': tmpl.section_page_header,     'hint': 'Repetido no topo de cada página'},
        {'key': 'section_header_generic',  'label': 'Cabeçalho genérico',                'icon': '🏢', 'value': tmpl.section_header_generic,  'hint': 'Logo, dados da empresa e do cliente'},
        {'key': 'section_header_document', 'label': 'Cabeçalho do documento',            'icon': '📄', 'value': tmpl.section_header_document, 'hint': 'Texto introdutório do documento'},
        {'key': 'section_footer_document', 'label': 'Rodapé do documento',               'icon': '📋', 'value': tmpl.section_footer_document, 'hint': 'Totais, condições gerais, assinaturas'},
        {'key': 'section_page_footer',     'label': 'Rodapé de página (repetido)',       'icon': '↓', 'value': tmpl.section_page_footer,     'hint': 'Repetido no rodapé de cada página'},
    ]

    return render(request, 'document_templates/editor.html', {
        'tmpl':        tmpl,
        'params_form': params_form,
        'sections':    sections,
        'variables':   VARIABLES,
    })


# ── Delete ────────────────────────────────────────────────────────────────────

@perm_required('document_templates.delete_documenttemplate')
@require_POST
def template_delete(request, pk):
    tmpl = get_object_or_404(DocumentTemplate, pk=pk)
    if not tmpl.is_system:
        tmpl.delete()
    return redirect('document_templates:list')


# ── Duplicate ─────────────────────────────────────────────────────────────────

@perm_required('document_templates.add_documenttemplate')
@require_POST
def template_duplicate(request, pk):
    tmpl = get_object_or_404(DocumentTemplate, pk=pk)
    tmpl.pk        = None
    tmpl.name      = f'{tmpl.name} (cópia)'
    tmpl.is_system = False
    tmpl.is_default = False
    tmpl.created_by = request.user
    tmpl.save()
    return redirect('document_templates:editor', pk=tmpl.pk)

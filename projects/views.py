from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required

from .models import Project
from .forms import ProjectForm


# 📋 LIST
@login_required
def project_list(request):
    projects = Project.objects.all().order_by('-created_at')

    return render(request, 'projects/project_list.html', {
        'projects': projects
    })


# ➕ CREATE
@login_required
def project_create(request):
    form = ProjectForm(request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            project = form.save(commit=False)
            project.created_by = request.user
            project.save()
            form.save_m2m()

            return redirect('project_list')

    return render(request, 'projects/project_form.html', {
        'form': form,
        'title': 'Create Project'
    })


# ✏️ UPDATE
@login_required
def project_update(request, pk):
    project = get_object_or_404(Project, pk=pk)
    form = ProjectForm(request.POST or None, instance=project)

    if request.method == 'POST':
        if form.is_valid():
            project = form.save(commit=False)
            project.updated_by = request.user
            project.save()
            form.save_m2m()

            return redirect('project_list')

    return render(request, 'projects/project_form.html', {
        'form': form,
        'title': 'Edit Project'
    })

from django.http import JsonResponse
from clients.models import ClientContact


@login_required
def get_contacts_by_client(request):
    client_id = request.GET.get('client_id')
    contacts = ClientContact.objects.filter(client_id=client_id).values('id', 'name')
    return JsonResponse(list(contacts), safe=False)
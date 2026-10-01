from django.contrib import messages
from django.db.models import Count
from django.shortcuts import redirect, render

from core.decorators import require_super_admin

from .forms import BranchForm
from .models import Branch
from .services import create_branch


@require_super_admin
def list_view(request):
    form = BranchForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        branch = create_branch(**form.cleaned_data, user=request.user)
        messages.success(request, f"Cabang {branch.name} ({branch.code}) dibuat: konfigurasi SPI dari template, tanpa data operasional.")
        return redirect("branches:list")
    branches = Branch.objects.annotate(n_users=Count("memberships")).order_by("code")
    return render(request, "branches/list.html", {"form": form, "branches": branches})

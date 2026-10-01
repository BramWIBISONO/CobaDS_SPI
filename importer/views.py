from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.capabilities import Cap
from core.decorators import require_cap

from .commit import ImportBlocked, branch_has_data
from .forms import UploadForm
from .models import ImportRun
from .services import commit_run, create_run, existing_counts, grouped_counts


@require_cap(Cap.BRANCH_ADMIN)
def upload(request):
    form = UploadForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        run = create_run(form.cleaned_data["file"], request.branch, request.user)
        return redirect("importer:preview", pk=run.pk)
    runs = ImportRun.objects.filter(branch=request.branch).select_related("created_by")[:10]
    return render(request, "importer/upload.html", {"form": form, "runs": runs})


@require_cap(Cap.BRANCH_ADMIN)
def preview(request, pk):
    run = get_object_or_404(ImportRun.objects.select_related("created_by", "committed_by"), pk=pk, branch=request.branch)
    report = dict(run.report)
    if run.status == "PREVIEW":
        report["existing"] = existing_counts(request.branch)            # keadaan cabang saat ini, bukan saat unggah
    groups = grouped_counts(report) if report.get("counts") else []
    return render(request, "importer/preview.html", {"run": run, "report": report, "groups": groups,
                                                     "has_data": branch_has_data(request.branch)})


@require_POST
@require_cap(Cap.BRANCH_ADMIN)
def commit(request, pk):
    run = get_object_or_404(ImportRun, pk=pk, branch=request.branch)
    try:
        counts = commit_run(run, request.user, replace=request.POST.get("replace") == "on")
    except ImportBlocked as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, f"Tersimpan ke {request.branch.name}: {sum(counts.values())} baris dari {run.original_name}.")
    return redirect("importer:preview", pk=run.pk)

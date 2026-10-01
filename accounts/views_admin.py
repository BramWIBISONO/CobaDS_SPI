from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from branches.models import Membership
from core import audit
from core.capabilities import Cap
from core.decorators import require_cap

from .forms import GrantAccessForm
from .models import User


@require_cap(Cap.BRANCH_ADMIN)
def users_view(request):
    branch = request.branch
    form = GrantAccessForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user, role = form.user, form.cleaned_data["role"]
        old = Membership.objects.filter(user=user, branch=branch).first()
        with transaction.atomic():
            Membership.objects.update_or_create(user=user, branch=branch, defaults={
                "role": role, "teacher_name": form.cleaned_data["teacher_name"], "created_by": request.user})
            audit.log(branch=branch, user=request.user, action="ACCESS", entity="PENGGUNA", entity_id=user.email,
                      field="Peran", old=old.role if old else "", new=role)
        messages.success(request, f"Akses {user.email} di {branch.name}: {role}.")
        return redirect("accounts:users")
    members = branch.memberships.select_related("user").order_by("user__full_name")
    pending = User.objects.filter(is_active=True, is_super_admin=False, memberships__isnull=True).order_by("date_joined")
    return render(request, "accounts/users.html", {"form": form, "members": members, "pending": pending})


@require_POST
@require_cap(Cap.BRANCH_ADMIN)
def revoke_view(request, membership_id):
    member = get_object_or_404(Membership.objects.select_related("user"), pk=membership_id, branch=request.branch)
    with transaction.atomic():
        audit.log(branch=request.branch, user=request.user, action="ACCESS", entity="PENGGUNA", entity_id=member.user.email,
                  field="Peran", old=member.role, new="(dicabut)")
        member.delete()
    messages.success(request, f"Akses {member.user.email} dicabut.")
    return redirect("accounts:users")

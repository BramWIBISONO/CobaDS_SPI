"""Pencarian global di topbar: murid, orang tua, kelas, guru - hanya cabang aktif dan hanya modul yang boleh dibuka pengguna."""
from urllib.parse import urlencode

from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

MIN_LEN = 2
LIMIT = {"students": 6, "parents": 4, "classes": 4, "teachers": 4}


def global_search(branch, perms, q):
    """{'q', 'groups': [{'key', 'label', 'icon', 'items': [{'title', 'sub', 'url', 'status'?}]}], 'all_url'} (q < 2 huruf: kosong)."""
    q = (q or "").strip()[:60]
    out = {"q": q, "groups": [], "all_url": ""}
    if branch is None or len(q) < MIN_LEN:
        return out
    if "student.view" in perms:
        from dashboards.calc.base import BranchData, fold
        from dashboards.calc.status import semua_status_sekarang
        from students.models import StudentMaster
        from students.services import dipakai

        found = list(StudentMaster.objects.for_branch(branch).filter(Q(nama__icontains=q) | Q(std__icontains=q))
                     .order_by("nama")[:LIMIT["students"]])
        if found:
            st = semua_status_sekarang(BranchData(branch, timezone.localdate()))
            items = []
            for s in found:
                d = dipakai(s)
                sub = " · ".join(x for x in (s.std, d["kode"], d["guru"]) if x)
                items.append({"title": s.nama or s.std, "sub": sub, "url": reverse("students:detail", args=[s.std]),
                              "status": st.get(fold(s.std), ""), "avatar": True})
            out["groups"].append({"key": "students", "label": "Murid", "icon": "users", "items": items})
        out["all_url"] = f"{reverse('students:list')}?{urlencode({'q': q})}"
    if "parent.view" in perms:
        from students.models import ParentMaster

        rows = ParentMaster.objects.for_branch(branch).filter(Q(nama__icontains=q) | Q(pid__icontains=q)).order_by("nama")[:LIMIT["parents"]]
        items = [{"title": p.nama or p.pid, "sub": p.pid, "url": reverse("students:parent_detail", args=[p.pid]), "avatar": True} for p in rows]
        if items:
            out["groups"].append({"key": "parents", "label": "Orang tua", "icon": "users-group", "items": items})
    if "class.view" in perms:
        from classes.models import ClassMaster

        rows = ClassMaster.objects.for_branch(branch).filter(code__icontains=q).exclude(code="").order_by("code")[:LIMIT["classes"]]
        items = [{"title": c.code, "sub": " · ".join(x for x in (c.tipe, c.guru) if x), "url": reverse("classes:detail", args=[c.code]),
                  "icon": "school"} for c in rows]
        if items:
            out["groups"].append({"key": "classes", "label": "Kelas", "icon": "school", "items": items})
    if "teacher.view" in perms:
        from masterdata.models import TeacherMaster

        rows = TeacherMaster.objects.for_branch(branch).filter(Q(name__icontains=q) | Q(tid__icontains=q)).order_by("name")[:LIMIT["teachers"]]
        items = [{"title": t.name or t.tid, "sub": t.tid, "url": reverse("masterdata:teacher", args=[t.tid]), "icon": "user-star"} for t in rows]
        if items:
            out["groups"].append({"key": "teachers", "label": "Guru", "icon": "user-star", "items": items})
    return out

import datetime

from django.conf import settings
from django.db import models


class Branch(models.Model):
    STATUS_CHOICES = [("NEW_BRANCH", "NEW_BRANCH (belum beroperasi)"), ("ACTIVE", "ACTIVE"), ("INACTIVE", "INACTIVE")]
    code = models.CharField("Branch ID", max_length=20, unique=True, help_text="mis. SPI-AS")
    name = models.CharField("Nama cabang", max_length=100)
    city = models.CharField("Kota", max_length=100, blank=True)
    address = models.TextField("Alamat", blank=True)
    status = models.CharField("Status cabang", max_length=12, choices=STATUS_CHOICES, default="NEW_BRANCH")
    language = models.CharField("Bahasa utama", max_length=40, default="Indonesia")
    currency = models.CharField("Mata uang", max_length=8, default="IDR")
    opening_date = models.DateField("Tanggal buka cabang", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Cabang"
        verbose_name_plural = "Cabang"

    def __str__(self):
        return self.name

    @property
    def unit_id(self):
        """UNIT- + Branch ID tanpa 'SPI-' (SPI-AS -> UNIT-AS), sama dengan rumus SETTINGS 'Unit cabang ini' di Excel"""
        code = self.code or ""
        return "UNIT-" + (code[4:] if code.upper().startswith("SPI-") else code)


class Membership(models.Model):
    ROLE_CHOICES = [("BRANCH_ADMIN", "Branch Admin"), ("MANAGER", "Manager"), ("CSO", "CSO"),
                    ("FINANCE", "Finance"), ("ACADEMIC", "Academic"), ("TEACHER", "Teacher")]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships")
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="memberships")
    role = models.CharField("Peran", max_length=20, choices=ROLE_CHOICES)
    teacher_name = models.CharField("Nama guru (seperti di jadwal)", max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "branch"], name="uq_membership_user_branch")]

    def __str__(self):
        return f"{self.user} · {self.branch.code} · {self.role}"


class BranchSetting(models.Model):
    """Parameter SETTINGS Excel yang boleh diubah orang (kapasitas, batas OFF / cuti, jatuh tempo, teks nota, ...)."""
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="settings")
    key = models.CharField("Kunci", max_length=40)
    label = models.CharField("Parameter", max_length=200, blank=True)
    value_text = models.TextField(blank=True, default="")
    value_number = models.FloatField(null=True, blank=True)
    value_date = models.DateField(null=True, blank=True)
    note = models.TextField("Keterangan", blank=True, default="")
    row_no = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["row_no", "key"]
        constraints = [models.UniqueConstraint(fields=["branch", "key"], name="uq_branch_setting_key")]

    def __str__(self):
        return f"{self.branch.code} · {self.key}"

    @property
    def value(self):
        if self.value_number is not None:
            return self.value_number
        if self.value_date is not None:
            return self.value_date
        return self.value_text or None

    @staticmethod
    def split_value(v):
        if isinstance(v, bool):
            return {"value_text": "TRUE" if v else "FALSE", "value_number": None, "value_date": None}
        if isinstance(v, (int, float)):
            return {"value_text": "", "value_number": float(v), "value_date": None}
        if isinstance(v, datetime.datetime):
            return {"value_text": "", "value_number": None, "value_date": v.date()}
        if isinstance(v, datetime.date):
            return {"value_text": "", "value_number": None, "value_date": v}
        return {"value_text": "" if v is None else str(v), "value_number": None, "value_date": None}

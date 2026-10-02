"""Membuat baris tabel Excel untuk uji: make_rows(Model, branch, {...}, {...}) -> row_no berurutan mulai 6."""


def make_rows(model, branch, *rows):
    return [model.objects.create(branch=branch, row_no=6 + i, **r) for i, r in enumerate(rows)]

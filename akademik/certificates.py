"""Sertifikat dari template SPI (folder settings.CERT_TEMPLATE_DIR; berisi tanda tangan - tidak disimpan di Git).

Template per kode level:
  1.0 / 1.1  PNG 3508×2480 (A4 landscape 300 dpi) - nama di ruang kosong bawah judul, nomor di panel biru kanan bawah.
  2.1 / 2.2  PPTX - gambar latar + kotak teks 'nama', 'nomor', 'tanggal…'; posisi, ukuran, dan font dibaca dari file .pptx.
Font: Arimo / Montserrat / Libre Baskerville (lisensi terbuka, akademik/fonts).
"""
import io
import re
import zipfile
from pathlib import Path

from django.conf import settings
from PIL import Image, ImageDraw, ImageFont

FONTS = Path(__file__).resolve().parent / "fonts"
EMU_PER_PT = 12700
MAROON = (65, 25, 39)

TEMPLATES = {
    "1.0": {"file": "sertifikat training 1.0.png", "kind": "png", "judul": "Block-Based Programming (Foundation to Programming)"},
    "1.1": {"file": "sertifikat training 1.1.png", "kind": "png", "judul": "Block-Based Robotics with Arduino Uno"},
    "2.1": {"file": "2.1 Python.pptx", "kind": "pptx", "judul": "2.1 Python Programming"},
    "2.2": {"file": "2.2.pptx", "kind": "pptx", "judul": "2.2 Web Programming"},
}
# Template PNG 1.x: tidak punya kotak teks; posisi diukur dari gambar (ruang kosong y 940-1330, teks kiri x 347, panel nomor x 2687).
PNG_LAYOUT = {"nama": {"x": 347, "y_mid": 1135, "w": 2150, "size": 150, "font": "montserrat-latin-700-normal.woff", "color": MAROON},
              "nomor": {"x": 2687, "y": 2160, "w": 720, "size": 66, "font": "montserrat-latin-600-normal.woff", "color": (255, 255, 255)}}
PPTX_FONT = {"nama": "arimo-latin-700-normal.woff", "nomor": "libre-baskerville-latin-400-normal.woff",
             "tanggal": "libre-baskerville-latin-700-normal.woff"}
BULAN_EN = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]


def template_dir():
    return Path(getattr(settings, "CERT_TEMPLATE_DIR", settings.BASE_DIR / "sertif"))


def template_for(kode):
    t = TEMPLATES.get(kode)
    if not t:
        return None
    path = template_dir() / t["file"]
    return {**t, "path": path} if path.exists() else None


def tanggal_en(d):
    return f"{d.day} {BULAN_EN[d.month - 1]} {d.year}"


def _font(name, size):
    return ImageFont.truetype(str(FONTS / name), size)


def _fit(draw, text, font_name, size, max_w, min_size=40):
    """Ukuran font terbesar (≤ size) yang membuat teks muat di lebar max_w."""
    s = size
    while s > min_size:
        f = _font(font_name, s)
        if draw.textlength(text, font=f) <= max_w:
            return f
        s -= 4
    return _font(font_name, min_size)


def _pptx(path):
    """Gambar latar terbesar + kotak teks bertanda (nama/nomor/tanggal) dari slide pertama, dalam piksel gambar."""
    with zipfile.ZipFile(path) as z:
        media = max((n for n in z.namelist() if n.startswith("ppt/media/")), key=lambda n: z.getinfo(n).file_size)
        bg = Image.open(io.BytesIO(z.read(media))).convert("RGB")
        pres = z.read("ppt/presentation.xml").decode("utf-8")
        slide = z.read("ppt/slides/slide1.xml").decode("utf-8")
    slide_w = int(re.search(r'<p:sldSz[^>]*cx="(\d+)"', pres).group(1))
    k = bg.width / slide_w                                         # piksel per EMU
    boxes = {}
    for sp in re.findall(r"<p:sp>.*?</p:sp>", slide, re.S):
        teks = "".join(re.findall(r"<a:t>([^<]*)</a:t>", sp)).strip().lower()
        key = next((n for n in ("nama", "nomor", "tanggal") if teks.startswith(n)), None)
        if not key:
            continue
        x, y = (int(v) for v in re.search(r'<a:off x="(-?\d+)" y="(-?\d+)"', sp).groups())
        w, h = (int(v) for v in re.search(r'<a:ext cx="(\d+)" cy="(\d+)"', sp).groups())
        sz = int((re.search(r'<a:rPr[^>]*sz="(\d+)"', sp) or re.search(r'sz="(\d+)"', sp)).group(1))
        lins = re.search(r'lIns="(\d+)"', sp)
        tins = re.search(r'tIns="(\d+)"', sp)
        boxes[key] = {"x": round((x + int(lins.group(1) if lins else 91440)) * k), "y": round((y + int(tins.group(1) if tins else 45720)) * k),
                      "w": round(w * k), "size": round(sz / 100 * EMU_PER_PT * k)}
    return bg, boxes


def render(kode, nama, nomor, tanggal):
    """Gambar sertifikat (PIL RGB, resolusi template). Melempar ValueError bila template level ini belum ada."""
    t = template_for(kode)
    if t is None:
        raise ValueError(f"Template sertifikat level {kode} belum tersedia.")
    if t["kind"] == "png":
        img = Image.open(t["path"]).convert("RGB")
        d = ImageDraw.Draw(img)
        n = PNG_LAYOUT["nama"]
        f = _fit(d, nama, n["font"], n["size"], n["w"])
        d.text((n["x"], n["y_mid"]), nama, font=f, fill=n["color"], anchor="lm")
        m = PNG_LAYOUT["nomor"]
        d.text((m["x"], m["y"]), nomor, font=_fit(d, nomor, m["font"], m["size"], m["w"]), fill=m["color"], anchor="la")
        return img
    img, boxes = _pptx(t["path"])
    d = ImageDraw.Draw(img)
    for key, text in (("nama", nama), ("nomor", nomor), ("tanggal", tanggal_en(tanggal))):
        b = boxes.get(key)
        if b:
            d.text((b["x"], b["y"]), text, font=_fit(d, text, PPTX_FONT[key], b["size"], b["w"]), fill=(0, 0, 0), anchor="la")
    return img


def simpan(img, folder, nama_file):
    """JPG resolusi penuh (kualitas 90), PDF A4 landscape 300 dpi, pratinjau JPG 1600 px. Path relatif terhadap MEDIA_ROOT.
    (PNG tidak dipakai: tekstur latar template membuat PNG ±22 MB.)"""
    root = Path(settings.MEDIA_ROOT)
    out = root / folder
    out.mkdir(parents=True, exist_ok=True)
    png, pdf, jpg = out / f"{nama_file}.jpg", out / f"{nama_file}.pdf", out / f"{nama_file}-preview.jpg"
    img.save(png, quality=90, optimize=True, dpi=(300, 300))
    img.save(pdf, "PDF", resolution=300.0, quality=92)
    prev = img.copy()
    prev.thumbnail((1600, 1600))
    prev.save(jpg, quality=85)
    return {k: str(p.relative_to(root)).replace("\\", "/") for k, p in (("png", png), ("pdf", pdf), ("preview", jpg))}

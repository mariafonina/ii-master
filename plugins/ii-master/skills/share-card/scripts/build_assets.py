#!/usr/bin/env python3
"""Сборка самодостаточного шаблона карточки: встраивает шрифты (base64 woff2) и QR (base64 PNG)
в assets/share-card-template.html между маркерами /*FONTS*/ … /*FONTS*/ и /*QR*/ … /*QR*/.
Идемпотентно: можно запускать повторно.

Запуск:  python3 build_assets.py            — шрифты + QR
         python3 build_assets.py --no-fonts — только QR (например, без сети)
         python3 build_assets.py --no-qr    — только шрифты

Шрифты: сабсеты cyrillic + latin с Google Fonts (Bitter 700, Golos Text 400–600 переменный;
JetBrains Mono убран по дизайн-фидбеку — служебные подписи карточки набраны Golos Text).
Оба под SIL OFL 1.1 — встраивание разрешено. Скачанные файлы кэшируются в системной temp-папке.
Нужна сеть (или кэш). Без сети шрифты не встраиваются, блок остаётся пустым, страница работает на системном стеке.

QR: библиотека qrcode (pip install qrcode pillow). Если её нет — блок остаётся пустым, карточка выходит без QR.
"""
import base64, io, os, re, sys, tempfile, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "..", "assets", "share-card-template.html")

CSS_URL = ("https://fonts.googleapis.com/css2?family=Bitter:wght@700"
           "&family=Golos+Text:wght@400;500;600&display=swap")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/126.0.0.0 Safari/537.36")  # с таким UA Google Fonts отдаёт woff2 и unicode-range
SUBSETS = ("cyrillic", "latin")
CONFIG = os.path.join(HERE, "..", "..", "ii-master", "config.md")  # источник ссылки и метки (контракт 5)
QR_URL_FALLBACK = "https://labsme.ru/ai?utm_source=share_card"
CACHE = os.path.join(tempfile.gettempdir(), "ii-master-fonts")


def qr_url_from_config():
    """test_url + share_utm_source из config.md ядра; без config — прежняя константа."""
    try:
        text = open(CONFIG, encoding="utf-8").read()
        url = re.search(r"^test_url:\s*(\S+)\s*$", text, re.M).group(1).strip().strip('"')
        m = re.search(r"^share_utm_source:\s*(\S+)\s*$", text, re.M)
        if m:
            sep = "&" if "?" in url else "?"
            url += f"{sep}utm_source={m.group(1).strip().strip(chr(34))}"
        return url
    except Exception as e:
        print(f"  config.md не прочитан ({e}) — QR по умолчанию {QR_URL_FALLBACK}", file=sys.stderr)
        return QR_URL_FALLBACK


def fetch(url, binary=False):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = r.read()
    return data if binary else data.decode("utf-8")


def build_fonts():
    os.makedirs(CACHE, exist_ok=True)
    css = fetch(CSS_URL)
    blocks = re.findall(r"/\* ([\w-]+) \*/\s*@font-face \{(.*?)\}", css, re.S)
    faces, seen = [], set()
    for subset, body in blocks:
        if subset not in SUBSETS:
            continue
        fam = re.search(r"font-family: '([^']+)'", body).group(1)
        url = re.search(r"url\((\S+?)\)", body).group(1)
        urange = re.search(r"unicode-range: ([^;]+);", body).group(1)
        if (fam, url) in seen:  # переменный шрифт: один файл на все веса
            continue
        seen.add((fam, url))
        weights = sorted({int(m.group(1)) for s2, b2 in blocks if s2 == subset
                          for m in [re.search(r"font-weight: (\d+)", b2)] if m and url in b2})
        weight = f"{weights[0]} {weights[-1]}" if len(weights) > 1 else str(weights[0])
        fn = os.path.join(CACHE, url.rsplit("/", 1)[-1])
        if not os.path.exists(fn):
            open(fn, "wb").write(fetch(url, binary=True))
        b64 = base64.b64encode(open(fn, "rb").read()).decode("ascii")
        faces.append(
            f"@font-face{{font-family:'{fam}';font-style:normal;font-weight:{weight};font-display:block;"
            f"src:url(data:font/woff2;base64,{b64}) format('woff2');unicode-range:{urange};}}"
        )
        print(f"  {fam:15s} {weight:8s} {subset:9s} {os.path.getsize(fn):6d} байт")
    return "\n".join(faces)


def build_qr(url):
    import qrcode  # noqa
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=6, border=3)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    print(f"  QR {url} → {qr.modules_count} модулей, {len(buf.getvalue())} байт PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def replace_between(text, marker, payload):
    first = text.index(marker)
    second = text.index(marker, first + len(marker))
    return text[:first] + marker + payload + text[second:]


def main():
    args = set(sys.argv[1:])
    html = open(TEMPLATE, encoding="utf-8").read()
    if "--no-fonts" not in args:
        try:
            print("Шрифты:")
            html = replace_between(html, "/*FONTS*/", "\n" + build_fonts() + "\n")
        except Exception as e:  # без сети — оставляем как есть
            print(f"  шрифты не встроены: {e}", file=sys.stderr)
    if "--no-qr" not in args:
        try:
            print("QR:")
            url = qr_url_from_config()
            html = replace_between(html, "/*QR*/", '"' + build_qr(url) + '"')
            html = replace_between(html, "/*QRURL*/", '"' + url + '"')
        except ImportError:
            print("  библиотека qrcode не найдена — карточка без QR (pip install qrcode pillow)", file=sys.stderr)
    open(TEMPLATE, "w", encoding="utf-8").write(html)
    print(f"Готово: {os.path.normpath(TEMPLATE)} ({os.path.getsize(TEMPLATE) // 1024} КБ)")


if __name__ == "__main__":
    main()

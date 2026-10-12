#!/usr/bin/env python3
"""t.me/kwert_wear kanalidagi barcha postlarni o'qib, rasmlarni images/ ga yuklaydi
va mahsulot ma'lumotlarini products.json ga yozadi.

GitHub Actions ichida ishlaydi (.github/workflows/sync.yml). Qo'lda ham ishga tushirsa bo'ladi:
    python scripts/sync_telegram.py
"""
import html
import io
import json
import os
import re
import sys
import time
import urllib.request

CHANNEL = os.environ.get("TG_CHANNEL", "kwert_wear")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG_DIR = os.path.join(ROOT, "images")
OUT = os.path.join(ROOT, "products.json")
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
MAX_SIDE = 1080

try:
    from PIL import Image
except Exception:  # Pillow bo'lmasa, rasm o'zgartirilmasdan saqlanadi
    Image = None


def get(url, binary=False, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "uz,ru;q=0.8,en;q=0.6"})
            with urllib.request.urlopen(req, timeout=40) as r:
                data = r.read()
                return data if binary else data.decode("utf-8", "replace")
        except Exception as e:
            print(f"  retry {i+1} {url}: {e}", file=sys.stderr)
            time.sleep(2 + i * 3)
    raise RuntimeError(f"Yuklab bo'lmadi: {url}")


MSG_RE = re.compile(r'<div class="tgme_widget_message_wrap[^"]*"[^>]*>(.*?)(?=<div class="tgme_widget_message_wrap|<div class="tgme_widget_messages_helper|\Z)', re.S)
POST_RE = re.compile(r'data-post="[^/"]+/(\d+)"')
PHOTO_RE = re.compile(r'<a class="tgme_widget_message_photo_wrap[^"]*"[^>]*href="https://t\.me/[^/]+/(\d+)[^"]*"[^>]*style="[^"]*background-image:url\(\'([^\']+)\'\)', re.S)
PHOTO_RE2 = re.compile(r'<a class="tgme_widget_message_photo_wrap[^"]*"[^>]*style="[^"]*background-image:url\(\'([^\']+)\'\)[^"]*"[^>]*href="https://t\.me/[^/]+/(\d+)', re.S)
VIDEO_THUMB_RE = re.compile(r'tgme_widget_message_video_thumb"[^>]*background-image:url\(\'([^\']+)\'\)')
TEXT_RE = re.compile(r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', re.S)
DATE_RE = re.compile(r'<time datetime="([^"]+)"')


def clean_text(raw):
    t = re.sub(r"<br\s*/?>", "\n", raw)
    t = re.sub(r"<[^>]+>", "", t)
    t = html.unescape(t)
    t = re.sub(r"[ \t ]+", " ", t)
    return "\n".join(l.strip() for l in t.split("\n")).strip()


def parse_page(page):
    posts = []
    for block in MSG_RE.findall(page):
        m = POST_RE.search(block)
        if not m:
            continue
        pid = int(m.group(1))
        photos = [(int(i), u) for i, u in PHOTO_RE.findall(block)]
        if not photos:
            photos = [(int(i), u) for u, i in PHOTO_RE2.findall(block)]
        if not photos:
            # bitta rasmli post: href bo'lmasligi mumkin
            photos = [(pid, u) for u in re.findall(r'tgme_widget_message_photo_wrap[^>]*background-image:url\(\'([^\']+)\'\)', block)]
        vthumbs = VIDEO_THUMB_RE.findall(block)
        tm = TEXT_RE.search(block)
        dm = DATE_RE.search(block)
        posts.append({
            "id": pid,
            "text": clean_text(tm.group(1)) if tm else "",
            "photos": photos,
            "video_thumbs": vthumbs,
            "has_video": "tgme_widget_message_video" in block,
            "date": dm.group(1) if dm else "",
        })
    return posts


def num(s):
    d = re.sub(r"\D", "", s)
    if not d:
        return None
    n = int(d)
    if n < 1000:  # "299" yoki "100" -> ming so'm
        n *= 1000
    return n


SKIP = re.compile(r"narx|cargo|kargo|kun\b|buyurtma|otziv|kwert|razmer|oldindan|@|yetkaz|uzs|so'm|som\b|#", re.I)
EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿⬀-⯿️‍••]+")
CAT_WORDS = [
    ("hoodie", r"xudi|hudi|hoodie|худи"),
    ("jacket", r"kurtka|koja|vetrovka|vedrofka|jacket|куртк"),
    ("pants", r"jeans|jinsi|shim|baggy|buggy|джинс"),
    ("shoes", r"krossov|shoes|jordan|aj1|skate|кросс"),
    ("acc", r"soat|watch|sumka|bag|кепк|cap"),
    ("top", r"futbolka|t-shirt|tee|ko'ylak|brocade|y2k"),
]


def parse_prices(text):
    out = []
    # ko'p narxli post: "👕200.000\n👖180.000"
    for em, val in re.findall(r"(👕|👖|👟|🧢|👜|🧥|⌚)\s*\**\s*([\d][\d .]*\d)", text):
        n = num(val)
        if n:
            out.append({"emoji": em, "price": n})
    if out:
        return out
    m = re.search(r"narx[^\d\n]*([\d][\d .,]*)", text, re.I)
    if m:
        n = num(m.group(1))
        if n:
            return [{"emoji": "", "price": n}]
    m = re.search(r"([\d]{2,3}[ .,]?000)\s*(uzs|so'm|som|сум|\+)", text, re.I)
    if m:
        return [{"emoji": "", "price": num(m.group(1))}]
    return []


def guess(text):
    name = ""
    for line in text.split("\n"):
        l = EMOJI.sub("", line).strip(" *-–:•")
        if len(l) >= 3 and re.search(r"[A-Za-zА-Яа-яЎўҚқҒғҲҳ]", l) and not SKIP.search(l):
            name = l[:60]
            break
    cat = "drop"
    low = text.lower()
    for c, rx in CAT_WORDS:
        if re.search(rx, low):
            cat = c
            break
    return name, cat


def save_image(url, path):
    if os.path.exists(path):
        return True
    try:
        data = get(url, binary=True)
    except Exception as e:
        print("  rasm yuklanmadi:", e, file=sys.stderr)
        return False
    if Image:
        try:
            im = Image.open(io.BytesIO(data)).convert("RGB")
            im.thumbnail((MAX_SIDE, MAX_SIDE))
            im.save(path, "JPEG", quality=84, optimize=True, progressive=True)
            return True
        except Exception as e:
            print("  rasm o'zgartirilmadi:", e, file=sys.stderr)
    with open(path, "wb") as f:
        f.write(data)
    return True


def main():
    os.makedirs(IMG_DIR, exist_ok=True)
    seen, posts, before = set(), [], None
    for _ in range(200):
        url = f"https://t.me/s/{CHANNEL}" + (f"?before={before}" if before else "")
        print("sahifa:", url)
        page = get(url)
        got = [p for p in parse_page(page) if p["id"] not in seen]
        if not got:
            break
        for p in got:
            seen.add(p["id"])
        posts += got
        low = min(p["id"] for p in got)
        if low <= 1:
            break
        before = low
        time.sleep(1.2)
    posts.sort(key=lambda p: -p["id"])
    print("postlar:", len(posts))

    products = []
    for p in posts:
        prices = parse_prices(p["text"])
        imgs = []
        for i, (sid, url) in enumerate(p["photos"]):
            rel = f"images/{sid}.jpg"
            if save_image(url, os.path.join(ROOT, rel)):
                imgs.append(rel)
        if not imgs and p["video_thumbs"]:
            rel = f"images/{p['id']}_v.jpg"
            if save_image(p["video_thumbs"][0], os.path.join(ROOT, rel)):
                imgs.append(rel)
        if not prices:  # narxsiz postlar (look, new zakas, e'lonlar) mahsulot emas
            continue
        name, cat = guess(p["text"])
        products.append({
            "post": p["id"],
            "name": name,
            "cat": cat,
            "prices": prices,
            "price": prices[0]["price"],
            "photos": imgs,
            "video": p["has_video"],
            "text": p["text"],
            "date": p["date"],
            "url": f"https://t.me/{CHANNEL}/{p['id']}",
        })

    meta = {"channel": CHANNEL, "updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "count": len(products)}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"meta": meta, "products": products}, f, ensure_ascii=False, indent=1)
    n_img = sum(len(p["photos"]) for p in products)
    print(f"tayyor: {len(products)} mahsulot, {n_img} rasm")
    if not products:
        sys.exit("Mahsulot topilmadi — Telegram sahifa tuzilishi o'zgargan bo'lishi mumkin")


if __name__ == "__main__":
    main()

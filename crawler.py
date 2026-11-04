"""Google Maps search crawler: wedding-related businesses near Ciamis."""

import datetime as dt
import html
import json
import random
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import http.cookiejar
from pathlib import Path

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36",
]

PHONE_RE = re.compile(r"^\+?[\d][\d\s\-().]{6,17}$")
DIGITS_ONLY = re.compile(r"\D")
PB_QUERY_SEGMENT = re.compile(r"^!1s[^!]*")
TEMPLATE_FILE = Path(__file__).with_name("gmaps-pb-template.txt")
_TEMPLATE = None



def _template():
    """Template segmen `pb` Google Maps, diambil dari halaman shell bila belum ada."""
    global _TEMPLATE
    if _TEMPLATE:
        return _TEMPLATE
    if TEMPLATE_FILE.exists():
        stored = TEMPLATE_FILE.read_text(encoding="utf-8").strip()
        if stored.startswith("!1s"):
            _TEMPLATE = stored
            return _TEMPLATE
    page = _http_get(search_page_url("jasa wedding ciamis", None, None, None))
    pb = urllib.parse.parse_qs(urllib.parse.urlparse(extract_xhr_path(page)).query)["pb"][0]
    TEMPLATE_FILE.write_text(pb + "\n", encoding="utf-8")
    _TEMPLATE = pb
    return _TEMPLATE


def build_results_url(query, lat, lon, zoom, template):
    pb = "!1s" + query + PB_QUERY_SEGMENT.sub("", template)
    params = f"tbm=map&authuser=0&hl=id&gl=id&q={urllib.parse.quote_plus(query)}"
    if lat is not None and lon is not None:
        params += f"&ll={lat}%2C{lon}&z={zoom}"
    return f"https://www.google.com/search?{params}&pb={urllib.parse.quote(pb, safe='!*')}"

_SESSION_UA = random.choice(USER_AGENTS)
_OPENER = urllib.request.build_opener(
    urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()),
)


def _headers():
    return {
        "User-Agent": _SESSION_UA,
        "Accept-Language": "id-ID,id;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }


def _http_get(url, retries=3, base_wait=8.0):
    last_error = None
    for attempt in range(retries):
        try:
            request = urllib.request.Request(url, headers=_headers())
            with _OPENER.open(request, timeout=30) as response:
                return response.read().decode("utf-8", "replace")
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as error:
            last_error = error
            if attempt < retries - 1:
                wait = base_wait * (2 ** attempt) + random.uniform(1, 4)
                print(f"    ...jaringan {type(error).__name__}, coba lagi dalam {wait:.0f}s")
                time.sleep(wait)
    raise last_error


def search_page_url(query, lat, lon, zoom):
    encoded = urllib.parse.quote(query.replace(" ", "+"))
    if lat is not None and lon is not None:
        return (f"https://www.google.com/maps/search/{encoded}"
                f"?hl=id&gl=id&ll={lat}%2C{lon}&z={zoom}")
    return f"https://www.google.com/maps/search/{encoded}?hl=id&gl=id"


def extract_xhr_path(page_html):
    match = re.search(r'<link href="(/search\?tbm=map[^"]+)"', page_html)
    if not match:
        raise RuntimeError("Google Maps tidak mengembalikan endpoint hasil (mungkin diblokir/rate-limit).")
    return html.unescape(match.group(1))


def fetch_results(query, lat, lon, zoom, retries=3):
    last_error = None
    for attempt in range(retries):
        try:
            body = _http_get(build_results_url(query, lat, lon, zoom, _template()), retries=1)
            if body.startswith(")]}'"):
                body = body[body.index("\n") + 1:]
            return json.loads(body)
        except Exception as error:
            last_error = error
            if attempt < retries - 1:
                wait = 12 * (attempt + 1) + random.uniform(2, 6)
                print(f"    ...hasil kosong/terblokir, segarkan template & tunggu {wait:.0f}s")
                time.sleep(wait)
                _TEMPLATE = None
    raise last_error


def business_arrays(data):
    found = []

    def walk(node, depth=0):
        if depth > 14 or len(found) > 500:
            return
        if isinstance(node, list):
            if (len(node) > 100 and isinstance(node[11], str)
                    and len(node[11]) > 2 and node[11] not in ("", "null")):
                found.append(node)
                return
            for child in node:
                walk(child, depth + 1)

    walk(data)
    return found


def _contact_value(contact, pattern):
    """Best display string from a Google contact cell (phone/email/url)."""
    stack = [contact]
    while stack:
        value = stack.pop(0)
        if isinstance(value, str) and pattern(value):
            return value
        if isinstance(value, list):
            stack[:0] = value
    return None


def _is_phone(text):
    if not text or "@" in text or text.startswith(("http", "www")):
        return False
    digits = DIGITS_ONLY.sub("", text)
    return 8 <= len(digits) <= 15 and digits[0] in ("0", "6", "8")


def _is_website(text):
    return isinstance(text, str) and text.startswith(("http://", "https://")) and not any(
        host in text for host in ("google.com/maps", "search.google.com", "googleusercontent.com"))


def phone_of(business):
    contacts = business[178] if len(business) > 178 and isinstance(business[178], list) else None
    if contacts:
        for contact in contacts:
            if isinstance(contact, list) and contact:
                phone = _contact_value(contact, _is_phone)
                if phone:
                    return phone
    # fallback: scan for the first phone-like string anywhere in the record
    stack = [business]
    while stack:
        value = stack.pop(0)
        if isinstance(value, str) and _is_phone(value):
            return value
        if isinstance(value, list):
            stack[:0] = value
    return None


def _match_index(business, pattern):
    """First top-level cell in the business array best matching a pattern."""
    stack = list(business)
    while stack:
        value = stack.pop(0)
        if isinstance(value, str) and pattern(value):
            return value
        if isinstance(value, list):
            stack[:0] = value
    return None


def address_of(business):
    parts = business[2] if len(business) > 2 and isinstance(business[2], list) else None
    if parts:
        cleaned = [part for part in parts if isinstance(part, str) and part]
        if cleaned:
            return ", ".join(cleaned)
    for index in (39, 18):
        if len(business) > index and isinstance(business[index], str):
            value = business[index].strip()
            name = business[11]
            if value.startswith(name):
                value = value[len(name):].strip(" ,-")
            if value:
                return value
    return None


def place_id_of(business):
    if len(business) > 78 and isinstance(business[78], str) and business[78].startswith("ChIJ"):
        return business[78]
    entry = business[227] if len(business) > 227 and isinstance(business[227], list) else None
    if entry and isinstance(entry[0], list):
        for cell in entry[0]:
            if isinstance(cell, str) and cell.startswith("ChIJ"):
                return cell
    return None


def maps_url_for(place_id, name):
    if place_id:
        return (f"https://www.google.com/maps/search/?api=1&query="
                f"{urllib.parse.quote(name)}&query_place_id={place_id}")
    return (f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(name)}")


def parse_business(business, checked_on):
    name = business[11]
    place_id = place_id_of(business)
    category_cell = business[13][0] if (len(business) > 13 and isinstance(business[13], list)
                                        and business[13] and isinstance(business[13][0], str)) else None
    ratings_cell = business[4] if len(business) > 4 and isinstance(business[4], list) else None
    coords_cell = business[9] if len(business) > 9 and isinstance(business[9], list) else None
    website = None
    if len(business) > 7 and isinstance(business[7], list) and business[7]:
        candidate = business[7][0]
        if _is_website(candidate):
            website = candidate
    if not website:
        website = _match_index(business, _is_website)

    plus_code = None
    if place_id:
        query = urllib.parse.quote(name)
        maps_url = (f"https://www.google.com/maps/search/?api=1&query={query}"
                    + (f"&query_place_id={place_id}" if place_id else ""))
    else:
        maps_url = maps_url_for(None, name)
    locality = business[14] if len(business) > 14 and isinstance(business[14], str) else None

    record = {
        "id_sumber": f"gmaps:{place_id}" if place_id else "gmaps:unknown",
        "nama": name,
        "alamat": address_of(business),
        "telepon_bisnis": phone_of(business),
        "wilayah_layanan": None,
        "situs_web": website,
        "status_situs": "tercantum" if website else "tidak_tercantum",
        "tanggal_dicek_situs": checked_on if website else None,
        "sumber": {"nama": "Google Maps", "url": "https://www.google.com/maps"},
        "dicek_pada": checked_on,
        # bonus Google Maps fields
        "kategori": category_cell,
        "vanity_id": business[89] if (len(business) > 89 and isinstance(business[89], str)) else None,
        "rating": ratings_cell[7] if ratings_cell and len(ratings_cell) > 7 else None,
        "jumlah_ulasan": ratings_cell[8] if ratings_cell and len(ratings_cell) > 8 else None,
        "koordinat": {"lat": coords_cell[2], "lon": coords_cell[3]} if coords_cell and len(coords_cell) > 3 else None,
        "nama_daerah": locality,
        "google_maps_url": maps_url,
    }
    return record


def crawl(keywords, lat=None, lon=None, zoom=12, delay=(6, 12)):
    checked_on = dt.date.today().isoformat()
    records = []
    seen = set()
    for keyword in keywords:
        try:
            data = fetch_results(keyword, lat, lon, zoom)
            businesses = business_arrays(data)
        except Exception as error:
            print(f"[skip] {keyword}: {error}")
            businesses = []
        fresh = 0
        for business in businesses:
            if not (len(business) > 11 and isinstance(business[11], str)):
                continue
            if business[11].casefold().strip() == keyword.casefold().strip():
                continue
            record = parse_business(business, checked_on)
            key = (record["nama"].casefold().strip(), (record["alamat"] or record["google_maps_url"]).casefold().strip())
            if record["id_sumber"] in seen or key in seen:
                continue
            seen.add(record["id_sumber"])
            seen.add(key)
            records.append(record)
            fresh += 1
        print(f"[ok] {keyword}: {len(businesses)} hasil, {fresh} baru")
        if keyword is not keywords[-1]:
            time.sleep(random.uniform(*delay))
    records.sort(key=lambda r: r["nama"].casefold())
    return records
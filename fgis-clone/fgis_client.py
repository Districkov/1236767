#!/usr/bin/env python3


import gzip
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://fgis.gost.ru"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


REGISTRIES = {
    "1": "Аттестация методик (аттестаты)",
    "2": "Средства измерений (госреестр СИ)",
    "3": "Испытания СИ (утверждение типа)",
    "4": "Поверки СИ",
    "5": "Калибровка СИ",
}

FIELD_LABELS = {
    "vri_id": "ID записи",
    "id": "ID",
    "mit_number": "Номер в госреестре",
    "mit_title": "Наименование СИ",
    "mit_notation": "Обозначение типа",
    "mit_factory_num": "Заводской номер",
    "mit_modification": "Модификация",
    "mit_manufacturer": "Изготовитель",
    "verification_date": "Дата поверки",
    "vrf_date": "Дата сведений",
    "valid_date": "Действительно до",
    "calibration_date": "Дата калибровки",
    "org_title": "Организация",
    "structure_title": "Подразделение",
    "vri_title": "Вид работ",
    "method_title": "Методика поверки",
    "doc_title": "Документ",
    "doc_num": "Номер документа",
    "sign_cipher": "Клеймо",
    "applicability": "Пригодность",
    "status": "Статус",
    "year": "Год",
}


LIST_PATHS = [
    "/fundmetrology/api/registry/{n}",
    "/api/registry/{n}",
]


LIST_VARIANTS = [
    ("GET", "query"),        
    ("POST", "filters"),     
    ("POST", "flat"),        
]

CARD_PATHS = [
    "/fundmetrology/api/registry/{n}/{id}",
    "/fundmetrology/api/registry/{n}/items/{id}",
    "/api/registry/{n}/{id}",
    "/fundmetrology/registry/{n}/items/{id}",
]

_ssl_ctx = None
_ssl_verified = True


_down_until = 0.0
_last_error = ""
DOWN_COOLDOWN = 90


def _ctx():
    global _ssl_ctx
    if _ssl_ctx is None:
        _ssl_ctx = ssl.create_default_context()
    return _ssl_ctx


def _unverified_ctx():
    c = ssl.create_default_context()
    c.check_hostname = False
    c.verify_mode = ssl.CERT_NONE
    return c


def http(url, method="GET", payload=None, timeout=30, referer=None, retries=2, mark_down=True):
    
    global _down_until, _last_error
    if mark_down and time.time() < _down_until:
        return 0, "ERR %s (повтор через %d с)" % (_last_error or "сайт не отвечает",
                                                  int(_down_until - time.time())), {}

    data = None
    headers = {
        "User-Agent": UA,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "ru-RU,ru;q=0.9",
        "Accept-Encoding": "gzip",
        "Connection": "close",
    }
    if referer:
        headers["Referer"] = referer
        headers["X-Requested-With"] = "XMLHttpRequest"
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json;charset=UTF-8"

    last_err = ""
    for attempt in range(retries + 1):
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=_ctx()) as r:
                raw = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    raw = gzip.decompress(raw)
                return r.status, raw.decode("utf-8", "replace"), dict(r.headers)
        except urllib.error.HTTPError as e:
            raw = b""
            try:
                raw = e.read()
                if e.headers.get("Content-Encoding") == "gzip":
                    raw = gzip.decompress(raw)
            except Exception:
                pass
            return e.code, raw.decode("utf-8", "replace"), dict(e.headers or {})
        except ssl.SSLCertVerificationError as e:
            
            global _ssl_verified
            if _ssl_verified:
                _ssl_verified = False
                _ssl_ctx = _unverified_ctx()
                last_err = "CERT: %s" % e
                continue
            last_err = str(e)
        except Exception as e:  
            last_err = "%s: %s" % (type(e).__name__, e)
        time.sleep(0.7 * (attempt + 1))
    _last_error = last_err
    if mark_down:
        _down_until = time.time() + DOWN_COOLDOWN
    return 0, "ERR " + last_err, {}


def _maybe_json(text):
    t = (text or "").strip()
    if not t or t[0] not in "{[":
        return None
    try:
        return json.loads(t)
    except Exception:
        return None


def _pick_items(obj):
    
    if obj is None:
        return None, 0
    if isinstance(obj, list):
        return obj, len(obj)
    if isinstance(obj, dict):
        for key in ("result", "data", "payload"):
            if key in obj:
                items, total = _pick_items(obj[key])
                if items is not None:
                    total = total or obj.get("count") or obj.get("total") or 0
                    return items, total
        for key in ("items", "rows", "records", "list", "content"):
            if isinstance(obj.get(key), list):
                total = 0
                for tk in ("count", "total", "totalCount", "totalElements", "recordsTotal", "size"):
                    if isinstance(obj.get(tk), int):
                        total = obj[tk]
                        break
                return obj[key], total or len(obj[key])
    return None, 0


def _host_ok(timeout=8):
    
    global _host_state
    now = time.time()
    if _host_state and now - _host_state[1] < 300:
        return _host_state[0]
    status, text, _ = http(BASE + "/", "GET", None, timeout, None, retries=0)
    ok = status != 0
    _host_state = (ok, now)
    return ok


_host_state = None


HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(HERE, "api_config.json")


CONFIG_VERSION = 2


def load_config():
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception:
        return {}
    
    return cfg if cfg.get("v") == CONFIG_VERSION else {}


def save_config(cfg):
    cfg = dict(cfg)
    cfg["v"] = CONFIG_VERSION
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def _qs_for(params, rows, page, query, filters):
    
    qs = {}
    if params.get("rows"):
        qs[params["rows"]] = rows
    if params.get("page"):
        qs[params["page"]] = page
    if query and params.get("search"):
        qs[params["search"]] = query
    qs.update(filters)
    return qs


CTX = "/fundmetrology"


def api_url(path):
    return BASE + CTX + path


def api_json(path, timeout=15, mark_down=True):
    status, text, _ = http(api_url(path), "GET", None, timeout, None, retries=1, mark_down=mark_down)
    return status, _maybe_json(text), text


def _result(obj):
    if isinstance(obj, dict) and isinstance(obj.get("result"), (dict, list)):
        return obj["result"]
    return obj


def tree_registries(timeout=15):
    
    status, obj, text = api_json("/api/tree", timeout)
    out = []

    def walk(node):
        if isinstance(node, dict):
            rid = node.get("id")
            title = node.get("title") or node.get("name")
            if rid is not None and title and str(rid).isdigit():
                if not any(r["id"] == str(rid) for r in out):
                    out.append({"id": str(rid), "title": str(title)})
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(obj)
    return out


def resolve_registry(keyword="оверк", timeout=15):
    
    best = None
    for reg in tree_registries(timeout):
        title = reg["title"].lower()
        if "шифр" in title or "клейм" in title:
            continue
        if keyword.lower() in title:
            if title.startswith("сведения о поверк") or title.startswith("результаты поверок"):
                return reg["id"]
            best = best or reg["id"]
    return best


def registry_fields(registry, timeout=15):
    status, obj, text = api_json("/api/registry/%s/fields" % registry, timeout)
    res = _result(obj)
    if isinstance(res, list):
        return res
    if isinstance(res, dict):
        for key in ("fields", "items", "properties"):
            if isinstance(res.get(key), list):
                return res[key]
    return []


def search_data(registry, query="", page=1, rows=20, filters=None, sort=None,
                timeout=15, verbose=False):
    
    pairs = [("pageNumber", page), ("pageSize", rows), ("orgID", "unset")]
    for key, value in (filters or {}).items():
        if value in (None, ""):
            continue
        pairs.append(("filterBy", key))
        pairs.append(("filterValues", value))
    if query:
        pairs.append(("filterBy", "search"))
        pairs.append(("filterValues", query))
    if sort and sort.get("key"):
        pairs += [("sortBy", sort["key"]), ("sortValues", sort.get("dir") or "asc")]

    url = api_url("/api/registry/%s/data" % registry) + "?" + urllib.parse.urlencode(pairs)
    status, text, _ = http(url, "GET", None, timeout,
                           "%s%s/registry/%s" % (BASE, CTX, registry), retries=1)
    obj = _maybe_json(text)
    items, total = _pick_items(obj)
    if verbose:
        print("  GET %-96s -> %s%s" % (url.replace(BASE, ""), status,
                                       (" items=%d" % len(items)) if items else ""))
    return {"items": items or [], "total": total, "endpoint": url, "method": "GET",
            "mode": "data", "raw": obj,
            "error": None if items else _short(text)}


def card_plain(registry, rec_id, timeout=15):
    
    path = "/api/registry/%s/items/%s/plaindata" % (registry, rec_id)
    status, obj, text = api_json(path, timeout)
    res = _result(obj)
    props = None
    if isinstance(res, dict):
        props = res.get("properties") or res.get("data") or res
    if isinstance(props, dict) and props:
        return {"data": props, "endpoint": api_url(path), "raw": obj, "error": None}
    return None


LIST_SOURCES = [
    {"name": "registry_data", "path": "/api/registry/{reg}/data", "org": True},
    {"name": "povregistry_data", "path": "/api/povregistry/data", "org": True},
    {"name": "povdata", "path": "/api/povdata", "org": False},
    {"name": "povdata_data", "path": "/api/povdata/data", "org": False},
    {"name": "povregistry", "path": "/api/povregistry", "org": True},
]


def source_url(source, registry, page, rows, filters=None, query="", sort=None):
    path = source["path"].format(reg=registry)
    pairs = [("pageNumber", page), ("pageSize", rows)]
    if source.get("org"):
        pairs.append(("orgID", "unset"))
    for key, value in (filters or {}).items():
        if value not in (None, ""):
            pairs += [("filterBy", key), ("filterValues", value)]
    if query:
        pairs += [("filterBy", "search"), ("filterValues", query)]
    if sort and sort.get("key"):
        pairs += [("sortBy", sort["key"]), ("sortValues", sort.get("dir") or "asc")]
    return api_url(path) + "?" + urllib.parse.urlencode(pairs)


def try_source(source, registry, query, page, rows, filters=None, sort=None,
               timeout=15, verbose=False):
    url = source_url(source, registry, page, rows, filters, query, sort)
    status, text, _ = http(url, "GET", None, timeout,
                           "%s%s/registry/%s" % (BASE, CTX, registry), retries=1)
    obj = _maybe_json(text)
    items, total = _pick_items(obj)
    if verbose:
        print("  %-16s %s -> %s%s" % (source["name"], url.replace(BASE, ""), status,
                                      (" items=%d" % len(items)) if items else ""))
    return {"items": items or [], "total": total, "endpoint": url, "method": "GET",
            "mode": source["name"], "raw": obj,
            "error": None if items else _short(text, 200)}


def search(registry, query="", page=1, rows=20, filters=None, timeout=15, verbose=False):
    
    n = str(registry)
    filters = {k: v for k, v in (filters or {}).items() if v not in (None, "")}
    if not _host_ok():
        return {"items": [], "total": 0, "endpoint": None, "method": None, "mode": None,
                "raw": None, "error": "хост fgis.gost.ru недоступен с этой машины "
                                      "(таймаут TCP/TLS — нужен российский IP или VPN)"}

    cfg = load_config()
    reg = n
    preferred = cfg.get("source_name")
    sources = list(LIST_SOURCES)
    if preferred:
        sources.sort(key=lambda item: 0 if item["name"] == preferred else 1)

    errors = []
    for source in sources:
        res = try_source(source, reg, query, page, rows, filters, timeout=timeout, verbose=verbose)
        if res["items"]:
            if cfg.get("source_name") != source["name"] or cfg.get("registry") != reg:
                save_config({"registry": reg, "source_name": source["name"], "source": "auto"})
            return res
        errors.append("%s -> %s" % (source["name"], str(res["error"])[:120]))

    return {"items": [], "total": 0, "endpoint": None, "method": None, "mode": None,
            "raw": None, "error": "ни один источник не ответил: " + " | ".join(errors[-3:])}


def card(registry, rec_id, timeout=15, verbose=False):
    
    n = str(registry)
    cfg = load_config()
    if n == "4" and cfg.get("registry"):
        n = str(cfg["registry"])
    for path in ("/api/registry/%s/items/%s/plaindata" % (n, rec_id),
                 "/api/povdata/%s" % rec_id,
                 "/api/povregistry/items/%s/plaindata" % rec_id):
        status, obj, text = api_json(path, timeout)
        res = _result(obj)
        props = None
        if isinstance(res, dict):
            props = res.get("properties") or res.get("data") or res
        if isinstance(props, dict) and props and not res.get("error"):
            return {"data": props, "endpoint": api_url(path), "raw": obj, "error": None}

    referer = "%s/fundmetrology/registry/%s" % (BASE, n)
    errors = []
    for tpl in CARD_PATHS:
        url = BASE + tpl.format(n=n, id=rec_id)
        status, text, _ = http(url, "GET", None, timeout, referer, retries=1)
        if verbose:
            print("  GET %-70s -> %s" % (url, status))
        obj = _maybe_json(text)
        if obj is not None:
            items, _ = _pick_items(obj)
            data = items[0] if items else obj
            if isinstance(data, dict) and data:
                return {"data": data, "endpoint": url, "raw": obj, "error": None}
        if status == 200 and "<html" in text.lower():
            data = parse_html_card(text)
            if data:
                return {"data": data, "endpoint": url, "raw": None, "error": None,
                        "source": "html"}
        errors.append("%s -> %s" % (url, status))
    return {"data": None, "endpoint": None, "raw": None,
            "error": "карточка не получена: " + " | ".join(errors)}


def parse_html_card(html):
    
    out = {}
    m = re.search(r"window\.__(?:INITIAL_STATE|NUXT|DATA)__\s*=\s*(\{.*?\});?\s*</script>",
                  html, re.S)
    if m:
        try:
            blob = json.loads(m.group(1))
            items, _ = _pick_items(blob)
            if items:
                return items[0]
            if isinstance(blob, dict):
                out.update({k: v for k, v in blob.items() if not isinstance(v, (dict, list))})
        except Exception:
            pass
    
    for label, value in re.findall(
            r"<t[dh][^>]*>\s*([^<>]{3,60}?)\s*:?\s*</t[dh]>\s*<t[dh][^>]*>\s*([^<>]{1,200}?)\s*</t[dh]>",
            html):
        key = re.sub(r"\s+", " ", label).strip()
        val = re.sub(r"\s+", " ", value).strip()
        if key and val:
            out[key] = val
    return out or None


def norm_key(key):
    
    key = str(key).split(":")[-1]
    key = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", key)
    return key.lower()


def flatten(item):
    if not isinstance(item, dict):
        return {}, {}
    props = item.get("properties")
    if not isinstance(props, list):
        return {norm_key(k): v for k, v in item.items()}, {}

    data, titles = {}, {}
    for prop in props:
        if not isinstance(prop, dict):
            continue
        name = prop.get("name") or prop.get("title") or ""
        key = norm_key(name)
        value = prop.get("value")
        if value in (None, ""):
            value = prop.get("longValue")
        data[key] = value
        if prop.get("title"):
            titles[key] = prop["title"]
    if item.get("id") is not None:
        data["id"] = item["id"]
    return data, titles


TITLE_KEYS = ("mit_title", "name_si", "vri_title", "doc_title", "title", "name", "cm_name")


def normalize(item):
    
    if not isinstance(item, dict):
        return {"title": str(item)[:200], "subtitle": "", "fields": []}

    data, titles = flatten(item)
    title = "Запись"
    for key in TITLE_KEYS:
        if data.get(key):
            title = data[key]
            break

    parts = []
    for key, prefix in (("mit_notation", ""), ("mit_number", "рег. № "),
                        ("number_si", "рег. № "), ("mit_factory_num", "зав. № ")):
        if data.get(key):
            parts.append(prefix + str(data[key]))

    fields, cells, cols = [], {}, []
    for key, value in data.items():
        if value in (None, "", [], {}):
            continue
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False)
        label = titles.get(key) or FIELD_LABELS.get(key) or key
        text = str(value)
        fields.append((label, text))
        cells[key] = text
        if key not in ("id",):
            cols.append({"key": key, "title": label})

    return {"title": str(title), "subtitle": " · ".join(parts), "fields": fields,
            "cells": cells, "cols": cols, "raw": item}


POV_PATH = "/fundmetrology/cm/results"

POV_KEYS = {
    "Организация-поверитель": "org_title",
    "Регистрационный номер типа СИ": "mit_number",
    "Наименование типа СИ": "mit_title",
    "Обозначение типа СИ": "mit_notation",
    "Модификация СИ": "mit_modification",
    "Заводской номер/ Буквенно-цифровое обозначение": "mit_factory_num",
    "Дата поверки": "verification_date",
    "Действительна до": "valid_date",
    "Номер свидетельства/ Номер извещения": "sign_cipher",
    "Пригодность": "applicability",
}


def pov_list(page=1, rows=20, year=None, query="", sort=None, timeout=25, verbose=False):
    
    import pov as pov_html

    pairs = []
    if page and int(page) > 1:
        pairs.append(("page", page))
    if rows and int(rows) != 20:
        pairs.append(("pageSize", rows))
    if year and str(year) not in ("all", ""):
        pairs.append(("activeYear", year))
    if sort and sort.get("key"):
        pairs.append(("sort", "%s|%s" % (sort["key"], sort.get("dir") or "asc")))
    if query:
        pairs.append(("search", query))

    url = BASE + POV_PATH + ("?" + urllib.parse.urlencode(pairs) if pairs else "")
    status, text, _ = http(url, "GET", None, timeout, BASE + POV_PATH, retries=1)
    if verbose:
        print("  GET %-70s -> %s" % (url.replace(BASE, ""), status))
    if status != 200:
        return {"columns": [], "items": [], "total": 0, "pages": 0, "url": url,
                "error": "HTTP %s: %s" % (status, _short(text, 160))}

    data = pov_html.parse_list(text)
    if not data["items"]:
        reason = ("страница %d байт без таблицы — это оболочка приложения, "
                  "данные подгружаются отдельным запросом" % len(text))
        if len(text) > 20000:
            reason = "таблица не найдена в HTML (%d байт), разметка изменилась" % len(text)
        return {"columns": [], "items": [], "total": 0, "pages": 0, "url": url,
                "error": reason, "size": len(text), "snippet": _short(text, 200)}

    columns = [{"key": POV_KEYS.get(title, norm_key(title)), "title": title}
               for title in data["columns"]]

    items = []
    for row in data["items"]:
        cells = {}
        for index, value in enumerate(row["cells"]):
            if index < len(columns):
                cells[columns[index]["key"]] = value
        items.append({
            "title": cells.get("mit_title") or cells.get("org_title") or "Запись",
            "subtitle": cells.get("mit_number", ""),
            "cells": cells,
            "cols": columns,
            "url": row["url"],
            "raw": {"id": row["id"], "cells": cells},
        })

    return {"columns": columns, "items": items, "total": data["total"],
            "pages": data["pages"], "url": url, "error": None}


def pov_card(rec_id, timeout=25):
    
    import pov as pov_html

    url = "%s%s/%s" % (BASE, POV_PATH, rec_id)
    status, text, _ = http(url, "GET", None, timeout, BASE + POV_PATH, retries=1)
    if status != 200:
        return {"sections": [], "url": url, "error": "HTTP %s" % status}
    return {"sections": pov_html.parse_card(text)["sections"], "url": url, "error": None}


def pov_check(page=1, rows=20, year=None, query=""):
    print("Проверяю раздел поверок: %s%s" % (BASE, POV_PATH))
    res = pov_list(page, rows, year, query, verbose=True)
    print("  запрошенный url:", res.get("url"))
    print("  размер ответа: %s байт" % res.get("size", "?"))
    print("  строк: %d | всего: %s | колонок: %d"
          % (len(res["items"]), res["total"], len(res["columns"])))
    if res.get("snippet"):
        print("  начало ответа:", res["snippet"][:160])
    if res["items"]:
        print("  первая строка:", " | ".join(res["items"][0]["cells"])[:220])
    if res["error"]:
        print("  ОШИБКА:", str(res["error"])[:500])
    return res


def probe(registry=None):
    
    global _down_until
    _down_until = 0.0
    print("ФГИС probe: %s" % BASE)
    print("Проверка корня сайта...")
    status, text, hdrs = http(BASE + "/", "GET", None, 25)
    print("  GET / -> %s (%d байт, server=%s)" % (status, len(text), hdrs.get("Server", "?")))
    if status == 0:
        print("  !! Сайт недоступен с этой машины: %s" % text[:200])
        print("     Проверьте VPN/прокси: fgis.gost.ru отдаёт данные только части адресов.")
        return {"root": status, "registries": {}}

    regs = [str(registry)] if registry else list(REGISTRIES)
    report = {"root": status, "registries": {}}
    for n in regs:
        print("\nРеестр %s - %s" % (n, REGISTRIES.get(n, "?")))
        res = search(n, "", 1, 3, verbose=True)
        report["registries"][n] = {
            "ok": bool(res["items"]),
            "endpoint": res["endpoint"],
            "method": res["method"],
            "mode": res["mode"],
            "count": res["total"],
            "sample_keys": sorted(res["items"][0].keys())[:25] if res["items"] else [],
            "error": res["error"],
        }
        if res["items"]:
            print("  OK: %s %s (%s), записей ~%s" % (res["method"], res["endpoint"],
                                                     res["mode"], res["total"] or "?"))
            print("  поля: %s" % ", ".join(report["registries"][n]["sample_keys"]))
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "probe_report.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("\nОтчёт сохранён: %s" % out)
    return report


def _short(text, limit=300):
    t = " ".join((text or "").split())
    return t[:limit]


def probe_deep(registry="4"):
    
    global _down_until, _host_state
    _down_until = 0.0
    _host_state = None

    n = str(registry)
    referer = "%s/fundmetrology/registry/%s" % (BASE, n)
    report = {"root": None, "api_variants": [], "card_variants": [],
              "bundle_endpoints": [], "page_scripts": []}

    page_url = "%s/fundmetrology/registry/%s" % (BASE, n)
    status, html, _ = http(page_url, "GET", None, 25, retries=0, mark_down=False)
    report["root"] = status
    print("GET %s -> %s (%d байт)\n" % (page_url, status, len(html)))
    if status == 0:
        print("!! сайт недоступен:", _short(html))
        return report

    
    scripts = re.findall(r'<script[^>]+src="([^"]+\.js[^"]*)"', html)
    report["page_scripts"] = scripts
    print("Скриптов на странице: %d" % len(scripts))

    patterns = [
        r'["\'](/[A-Za-z0-9_\-./]*api[A-Za-z0-9_\-./]*)["\']',
        r'["\'](/fundmetrology/[A-Za-z0-9_\-./]*)["\']',
        r'registry/\d+/[A-Za-z0-9_\-]+',
        r'["\']([A-Za-z0-9_\-./]*registry[A-Za-z0-9_\-./]*)["\']',
        r'["\']([A-Za-z0-9_\-./]*api/[A-Za-z0-9_\-./]*)["\']',
    ]
    found = []
    for src in scripts[:4]:
        
        candidates = [urllib.parse.urljoin(page_url, src), urllib.parse.urljoin(BASE + "/", src)]
        url, st, js = "", 0, ""
        for candidate in dict.fromkeys(candidates):
            st, js, _ = http(candidate, "GET", None, 40, mark_down=False)
            url = candidate
            if st == 200 and len(js) > 1000:
                break
        print("  скрипт %s -> %s (%d КБ)" % (url, st, len(js) // 1024))
        if st != 200 or len(js) < 1000:
            continue
        for pat in patterns:
            for m in re.findall(pat, js):
                if m not in found and len(m) < 120:
                    found.append(m)
    found = sorted(set(found))[:60]
    report["bundle_endpoints"] = found
    if found:
        print("\nПути API, найденные в JS сайта:")
        for f in found:
            print("  ", f)

    
    print("\nИсточники списка записей:")
    working = None
    for source in LIST_SOURCES:
        res = try_source(source, n, "", 1, 3, verbose=False)
        ok = bool(res["items"])
        print("  %-16s %-42s items=%d %s" % (source["name"], source["path"],
                                             len(res["items"]), "" if ok else _short(str(res["error"]), 120)))
        report["api_variants"].append({"title": source["name"], "url": res["endpoint"],
                                       "status": 200 if ok else 0,
                                       "items": len(res["items"]), "body": _short(str(res["error"]))})
        if ok and not working:
            working = (source, res)

    if working:
        save_config({"source_name": working[0]["name"], "source": "probe --deep"})
        print("\nРабочий источник: %s" % working[0]["name"])
        print("  url: %s" % working[1]["endpoint"].replace(BASE, ""))
        print("  total: %s" % working[1]["total"])
        print("  первый элемент: %s" % _short(json.dumps(working[1]["items"][0], ensure_ascii=False), 1500))
        rid = str(working[1]["items"][0].get("id") or "")
        if rid:
            for path in ("/api/registry/%s/items/%s/plaindata" % (n, rid),
                         "/api/povdata/%s" % rid):
                st, obj, text = api_json(path, 15)
                print("  карточка %s -> %s %s" % (path, st, _short(text, 300)))
                report["card_variants"].append({"url": path, "status": st, "body": _short(text, 400)})
    else:
        print("  ни один источник не отдал записи")

    
    base = "%s/fundmetrology/api/registry/%s" % (BASE, n)
    cases = [
        ("без параметров", "", {}),
        ("rows/page", "", {"rows": 5, "page": 1}),
        ("rows/page/year", "", {"rows": 5, "page": 1, "year": 2025}),
        ("page/size", "", {"page": 1, "size": 5}),
        ("limit/offset", "", {"limit": 5, "offset": 0}),
        ("rows/page/sort", "", {"rows": 5, "page": 1, "sort": "verification_date", "order": "desc"}),
        ("items", "/items", {"rows": 5, "page": 1}),
        ("items-list", "/items", {"registryId": n, "rows": 5, "page": 1}),
        ("v1 rows/page", "/v1", {"rows": 5, "page": 1}),
        ("records", "/records", {"rows": 5, "page": 1}),
        ("search", "/search", {"q": "тахограф", "rows": 5, "page": 1}),
    ]
    if working:
        cases = []  
    print("\nОтветы эндпоинта (старые варианты):")
    good = None
    good_items = []
    for title, suffix, params in cases:
        url = base + suffix + ("?" + urllib.parse.urlencode(params) if params else "")
        st, body, _ = http(url, "GET", None, 15, referer, retries=0, mark_down=False)
        obj = _maybe_json(body)
        items, total = _pick_items(obj)
        print("  [%s] %s -> %s%s" % (title, url.replace(BASE, ""), st,
                                     ("  items=%d" % len(items)) if items else ""))
        print("      %s" % _short(body))
        report["api_variants"].append({"title": title, "url": url, "status": st,
                                       "body": _short(body, 600),
                                       "items": len(items) if items else 0})
        if items and good is None:
            good = (title, base + suffix, params)
            good_items = items

    
    if good:
        keys = good[2]
        rows_key = "rows" if "rows" in keys else ("size" if "size" in keys else "limit")
        cfg = {
            "registry": n,
            "url": good[1],
            "params": {"rows": rows_key, "page": "page", "search": "search"},
            "source": "probe --deep",
        }
        save_config(cfg)
        print("\nРабочий вариант: %s" % good[0])
        print("Сохранён в api_config.json — server.py теперь будет использовать его.")
    elif not working:
        print("\nРаботающий вариант не найден. Пришлите вывод выше и probe_deep.json.")


    
    if good_items:
        first = good_items[0]
        rid = str(first.get("vri_id") or first.get("id") or "")
        if rid:
            print("\nКарточка записи %s:" % rid)
            for tpl in CARD_PATHS:
                url = BASE + tpl.format(n=n, id=rid)
                st, body, _ = http(url, "GET", None, 15, referer, retries=0, mark_down=False)
                obj = _maybe_json(body)
                print("  %s -> %s%s" % (url.replace(BASE, ""), st, "  JSON" if obj else ""))
                report["card_variants"].append({"url": url, "status": st, "json": bool(obj),
                                                "body": _short(body, 300)})
                if obj:
                    break

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "probe_deep.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("\nОтчёт сохранён: %s" % out)
    return report


def probe_url(url, timeout=25):
    
    print("Страница: %s" % url)
    st, html, _ = http(url, "GET", None, timeout, retries=0, mark_down=False)
    print("  -> %s (%d байт)" % (st, len(html)))
    if st != 200:
        print("  ответ: %s" % _short(html, 200))
        return {}

    scripts = re.findall(r'<script[^>]+src="([^"]+\.js[^"]*)"', html)
    links = re.findall(r'<link[^>]+href="([^"]+\.js[^"]*)"', html)
    print("  скриптов: %d, modulepreload: %d" % (len(scripts), len(links)))

    loose_pat = re.compile(r'[/A-Za-z0-9_\-.]{0,60}/api[/A-Za-z0-9_\-./]{0,80}')
    found = []
    for src in (scripts + links)[:6]:
        for candidate in dict.fromkeys([urllib.parse.urljoin(url, src),
                                        urllib.parse.urljoin(BASE + "/", src)]):
            st2, js, _ = http(candidate, "GET", None, 40, mark_down=False)
            if st2 != 200 or len(js) < 1000:
                continue
            print("  бандл %s -> %s (%d КБ)" % (candidate, st2, len(js) // 1024))
            for m in loose_pat.findall(js):
                m = m.strip(".")
                if len(m) > 6 and m not in found:
                    found.append(m)
            
            for kw in ("povregistry", "povdata", "pageNumber"):
                for m in list(re.finditer(kw, js))[:2]:
                    print("      …%s…" % _short(js[max(0, m.start() - 90):m.start() + 90], 190))
            break

    found = sorted(set(found))
    print("\nПути с /api/ в бандлах (%d):" % len(found))
    for f in found[:80]:
        print("  ", f)

    
    parts = [p for p in urllib.parse.urlparse(url).path.strip("/").split("/") if p]
    prefix = "/" + "/".join(parts[:-1]) if len(parts) > 1 else ""
    candidates = [
        prefix + "/api/povregistry/data",
        prefix + "/api/povregistry",
        prefix + "/api/povdata",
        prefix + "/api/registry/4/data",
        prefix + "/api/data",
        prefix + "/api/vri",
        prefix + "/api/records",
        "/fundmetrology/api/registry/4/data",
    ]
    print("\nПроверяю кандидатов (pageNumber=1&pageSize=2):")
    for path in dict.fromkeys(candidates):
        test = BASE + path + "?pageNumber=1&pageSize=2&orgID=unset"
        st3, body, _ = http(test, "GET", None, 12, url, retries=0, mark_down=False)
        items, total = _pick_items(_maybe_json(body))
        print("  %-46s -> %s%s" % (path, st3, ("  items=%d total=%s" % (len(items), total)) if items else ""))
        if not items:
            print("      %s" % _short(body, 150))
    return {"url": url, "scripts": scripts, "paths": found}


def _main(argv):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if len(argv) < 2:
        print(__doc__)
        return
    cmd = argv[1]
    if cmd == "probe":
        if "--url" in argv:
            idx = argv.index("--url")
            probe_url(argv[idx + 1])
        elif "--deep" in argv:
            args = [a for a in argv[2:] if not a.startswith("-")]
            probe_deep(args[0] if args else "4")
        else:
            probe(argv[2] if len(argv) > 2 else None)
    elif cmd == "search" and len(argv) > 2:
        q = " ".join(argv[3:])
        res = search(argv[2], q, 1, 10, verbose=True)
        print(json.dumps(res["raw"], ensure_ascii=False, indent=2)[:4000] if res["raw"]
              else res["error"])
    elif cmd == "pov":
        pov_check(int(argv[2]) if len(argv) > 2 else 1)
    elif cmd == "card" and len(argv) > 3:
        res = card(argv[2], argv[3], verbose=True)
        print(json.dumps(res["data"], ensure_ascii=False, indent=2)[:6000] if res["data"]
              else res["error"])
    else:
        print(__doc__)


if __name__ == "__main__":
    _main(sys.argv)

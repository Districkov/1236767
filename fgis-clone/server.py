#!/usr/bin/env python3


import argparse
import csv
import hashlib
import io
import json
import os
import re
import sys
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fgis_client as fc  

HERE = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(HERE, "static")
CACHE = os.path.join(HERE, "cache")
USE_CACHE = True
CACHE_TTL = 6 * 3600


def _cache_path(key):
    h = hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]
    return os.path.join(CACHE, h + ".json")


def cache_get(key):
    if not USE_CACHE:
        return None
    p = _cache_path(key)
    if not os.path.exists(p):
        return None
    if time.time() - os.path.getmtime(p) > CACHE_TTL:
        return None
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def cache_put(key, value):
    if not USE_CACHE:
        return
    os.makedirs(CACHE, exist_ok=True)
    try:
        with open(_cache_path(key), "w", encoding="utf-8") as f:
            json.dump(value, f, ensure_ascii=False)
    except Exception:
        pass


FILTER_MAP = {
    "org": "org_title",
    "number": "mit_number",
    "title": "mit_title",
    "notation": "mit_notation",
    "modification": "mit_modification",
    "factory": "mit_factory_num",
    "dateFrom": "verification_date_from",
    "dateTo": "verification_date_to",
    "validFrom": "valid_date_from",
    "validTo": "valid_date_to",
    "cert": "sign_cipher",
    "sticker": "sticker_num",
    "applicability": "applicability",
}

DATE_FIELDS = ("dateFrom", "dateTo", "validFrom", "validTo")


def _iso_date(value):
    
    m = re.match(r"^(\d{2})\.(\d{2})\.(\d{4})$", str(value).strip())
    return "%s-%s-%s" % (m.group(3), m.group(2), m.group(1)) if m else value


def _filters(q):
    
    raw = (q.get("filters") or ["{}"])[0]
    try:
        ui = json.loads(raw) if raw else {}
    except Exception:
        ui = {}
    if not isinstance(ui, dict):
        ui = {}

    filters = {}
    for key, value in ui.items():
        if value in (None, ""):
            continue
        if key in DATE_FIELDS:
            value = _iso_date(value)
        filters[FILTER_MAP.get(key, key)] = value

    year = (q.get("year") or [""])[0]
    if year == "before":
        filters["year_to"] = "2010"
    elif year and year != "all":
        filters["year"] = year
    return filters


class Handler(BaseHTTPRequestHandler):
    server_version = "fgis-clone/1.0"

    def log_message(self, fmt, *args):
        sys.stderr.write("[%s] %s\n" % (time.strftime("%H:%M:%S"), fmt % args))

    
    def _send(self, code, body, ctype="application/json; charset=utf-8", extra=None):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj, ensure_ascii=False))

    def _file(self, path, ctype):
        try:
            with open(path, "rb") as f:
                self._send(200, f.read(), ctype)
        except FileNotFoundError:
            self._send(404, "not found", "text/plain; charset=utf-8")

    
    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        p = u.path

        if p in ("/", "/index.html"):
            return self._file(os.path.join(STATIC, "index.html"), "text/html; charset=utf-8")
        if p.startswith("/static/"):
            rel = urllib.parse.unquote(p[len("/static/"):]).replace("\\", "/")
            full = os.path.normpath(os.path.join(STATIC, rel))
            if not full.startswith(STATIC):  
                return self._send(403, "forbidden", "text/plain; charset=utf-8")
            ext = os.path.splitext(full)[1].lower()
            ctype = {
                ".css": "text/css; charset=utf-8",
                ".js": "application/javascript; charset=utf-8",
                ".html": "text/html; charset=utf-8",
                ".woff2": "font/woff2",
                ".woff": "font/woff",
                ".ttf": "font/ttf",
                ".svg": "image/svg+xml",
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".ico": "image/x-icon",
            }.get(ext, "application/octet-stream")
            return self._file(full, ctype)

        if p == "/api/registries":
            return self._json({"registries": fc.REGISTRIES})

        if p == "/api/tree":
            cached = cache_get("tree")
            if cached:
                return self._json(cached)
            regs = fc.tree_registries()
            out = {"registries": regs}
            if regs:
                cache_put("tree", out)
            return self._json(out)

        if p == "/api/health":
            out = {"server": True, "pov": {}, "site": None}
            try:
                res = fc.pov_list(1, 5, None, "", timeout=15)
                out["pov"] = {"items": len(res["items"]), "total": res["total"],
                              "columns": len(res["columns"]), "error": res["error"],
                              "url": res.get("url")}
                out["site"] = "ERR" not in str(res["error"] or "")
            except Exception as e:
                out["pov"] = {"error": "%s: %s" % (type(e).__name__, e)}
                out["site"] = False
            return self._json(out)

        if p == "/api/probe":
            return self._json(fc.probe())

        if p == "/api/search":
            reg = (q.get("reg") or ["4"])[0]
            query = (q.get("q") or [""])[0]
            page = int((q.get("page") or ["1"])[0] or 1)
            rows = min(int((q.get("rows") or ["20"])[0] or 20), 100)
            filters = _filters(q)

            if reg == "pov":
                year = (q.get("year") or [""])[0]
                sort_key = (q.get("sort") or [""])[0]
                sort_dir = (q.get("dir") or [""])[0]
                sort = {"key": sort_key, "dir": sort_dir} if sort_key else None
                key = "pov|%s|%s|%s|%s|%s" % (page, rows, year, query, sort_key)
                cached = cache_get(key)
                if cached:
                    cached["cached"] = True
                    return self._json(cached)
                try:
                    res = fc.pov_list(page, rows, year, query, sort)
                except Exception as e:
                    return self._json({"registry": "pov", "items": [], "columns": [],
                                       "total": 0, "error": "сбой на сервере: %s: %s"
                                       % (type(e).__name__, e)}, 200)
                out = {
                    "registry": "pov",
                    "registry_title": "Результаты поверок СИ",
                    "page": page,
                    "rows": rows,
                    "total": res["total"],
                    "columns": res["columns"],
                    "items": res["items"],
                    "endpoint": res.get("url"),
                    "error": res["error"],
                    "cached": False,
                }
                if res["items"]:
                    cache_put(key, out)
                return self._json(out)

            key = "search|%s|%s|%s|%s|%s" % (reg, query, page, rows, json.dumps(filters, sort_keys=True))
            cached = cache_get(key)
            if cached:
                cached["cached"] = True
                return self._json(cached)
            res = fc.search(reg, query, page, rows, filters=filters)
            items = [fc.normalize(i) for i in res["items"]]
            columns = items[0]["cols"] if items else []
            out = {
                "registry": reg,
                "registry_title": fc.REGISTRIES.get(reg, ""),
                "page": page,
                "rows": rows,
                "total": res["total"],
                "endpoint": res["endpoint"],
                "method": res["method"],
                "error": res["error"],
                "items": items,
                "columns": columns,
                "cached": False,
            }
            if res["items"]:
                cache_put(key, out)
            return self._json(out)

        if p == "/api/card":
            reg = (q.get("reg") or ["4"])[0]
            rid = (q.get("id") or [""])[0]
            if not rid:
                return self._json({"error": "не передан id"}, 400)
            if reg == "pov":
                res = fc.pov_card(rid)
                if res.get("error"):
                    return self._json({"error": res["error"], "id": rid}, 502)
                fields, title = [], rid
                for section in res["sections"]:
                    for label, value in section["rows"]:
                        fields.append([label, value])
                        if label == "Наименование типа СИ":
                            title = value
                return self._json({
                    "registry": "pov",
                    "id": rid,
                    "endpoint": res.get("url"),
                    "card": {"title": title, "fields": fields,
                             "sections": res["sections"], "raw": None},
                    "cached": False,
                })

            key = "card|%s|%s" % (reg, rid)
            cached = cache_get(key)
            if cached:
                cached["cached"] = True
                return self._json(cached)
            res = fc.card(reg, rid)
            if not res["data"]:
                return self._json({"error": res["error"], "id": rid}, 502)
            out = {
                "registry": reg,
                "id": rid,
                "endpoint": res["endpoint"],
                "source": res.get("source", "api"),
                "card": fc.normalize(res["data"]),
                "raw": res["raw"],
                "cached": False,
            }
            cache_put(key, out)
            return self._json(out)

        if p == "/api/export":
            reg = (q.get("reg") or ["4"])[0]
            query = (q.get("q") or [""])[0]
            pages = min(int((q.get("pages") or ["3"])[0] or 3), 20)

            if reg == "pov":
                year = (q.get("year") or [""])[0]
                buf = io.StringIO()
                writer = csv.writer(buf, delimiter=";")
                columns = []
                got = 0
                for page in range(1, pages + 1):
                    res = fc.pov_list(page, 20, year, query)
                    if not res["items"]:
                        break
                    if not columns:
                        columns = [c["title"] for c in res["columns"]]
                        writer.writerow(columns)
                    for item in res["items"]:
                        writer.writerow([item["cells"].get(c["key"], "") for c in res["columns"]])
                        got += 1
                    time.sleep(0.3)
                if not got:
                    return self._json({"error": "нет данных для выгрузки"}, 502)
                data = "\ufeff" + buf.getvalue()
                fname = "fgis_pov_%s.csv" % time.strftime("%Y%m%d_%H%M")
                return self._send(200, data, "text/csv; charset=utf-8",
                                  {"Content-Disposition": 'attachment; filename="%s"' % fname})

            filters = _filters(q)
            rows = 100
            buf = io.StringIO()
            w = csv.writer(buf, delimiter=";")
            header_written = False
            got = 0
            for page in range(1, pages + 1):
                res = fc.search(reg, query, page, rows, filters=filters)
                if not res["items"]:
                    break
                for it in res["items"]:
                    if not header_written:
                        keys = list(it.keys())
                        w.writerow(keys)
                        header_written = True
                    w.writerow([it.get(k, "") if not isinstance(it.get(k), (dict, list))
                                else json.dumps(it.get(k), ensure_ascii=False) for k in keys])
                    got += 1
                if len(res["items"]) < rows:
                    break
                time.sleep(0.3)
            if not header_written:
                return self._json({"error": "нет данных для выгрузки"}, 502)
            data = "\ufeff" + buf.getvalue()  
            fname = "fgis_reg%s_%s.csv" % (reg, time.strftime("%Y%m%d_%H%M"))
            return self._send(200, data, "text/csv; charset=utf-8",
                              {"Content-Disposition": 'attachment; filename="%s"' % fname})

        return self._send(404, "not found", "text/plain; charset=utf-8")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="Локальное зеркало ФГИС")
    ap.add_argument("--port", type=int, default=8017)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--no-cache", action="store_true")
    a = ap.parse_args()
    global USE_CACHE
    USE_CACHE = not a.no_cache

    srv = ThreadingHTTPServer((a.host, a.port), Handler)
    print("ФГИС-зеркало: http://%s:%d  (Ctrl+C — остановить)" % (a.host, a.port))
    print("Данные: %s | кэш: %s" % (fc.BASE, CACHE if USE_CACHE else "выключен"))
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nостановлено")


if __name__ == "__main__":
    main()

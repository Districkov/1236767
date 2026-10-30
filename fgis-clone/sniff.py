#!/usr/bin/env python3


import os
import re
import subprocess
import sys

BROWSERS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]


def find_browser():
    for path in BROWSERS:
        if os.path.exists(path):
            return path
    return None


def main(url, out_name=None):
    browser = find_browser()
    if not browser:
        print("Не нашёл Edge/Chrome. Запустите вручную с --log-net-log.")
        return

    here = os.path.dirname(os.path.abspath(__file__))
    netlog = os.path.join(here, "netlog.json")
    profile = os.path.join(here, "_browser_profile")
    dom_path = os.path.join(here, out_name or "dom.html")

    for old in (netlog, dom_path):
        if os.path.exists(old):
            os.remove(old)

    cmd = [
        browser,
        "--headless=new",
        "--disable-gpu",
        "--no-first-run",
        "--no-default-browser-check",
        "--user-data-dir=" + profile,
        "--log-net-log=" + netlog,
        "--net-log-capture-mode=Everything",
        "--virtual-time-budget=20000",
        "--dump-dom",
        url,
    ]
    print("Запускаю браузер: %s" % os.path.basename(browser))
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120,
                                encoding="utf-8", errors="replace")
        dom = result.stdout or ""
    except Exception as e:
        print("Не удалось запустить браузер: %s" % e)
        return

    if dom:
        with open(dom_path, "w", encoding="utf-8") as f:
            f.write(dom)
    print("DOM: %d байт, сохранён в %s" % (len(dom), os.path.basename(dom_path)))
    print("  таблица отрендерилась:", "да" if ("поверк" in dom.lower()) else "нет")

    if not os.path.exists(netlog):
        print("Сетевой лог не создан (браузер не успел?). Попробуйте ещё раз.")
        return

    with open(netlog, encoding="utf-8", errors="replace") as f:
        text = f.read()
    print("netlog: %.1f МБ" % (len(text) / 1024 / 1024))

    urls = set()
    for match in re.findall(r'https?://[^\s"\\,<>]{10,300}', text):
        urls.add(match.rstrip("\\"))
    urls = sorted(urls)
    urls_name = (out_name or "dom.html").replace(".html", "") + "_urls.txt"
    with open(os.path.join(here, urls_name), "w", encoding="utf-8") as f:
        f.write("\n".join(urls))

    noise = ("bing.com", "microsoft.com", "office.net", "office.com", "googleapis.com",
             "gstatic.com", "msn.com", "live.com", "smartscreen", "google.com",
             "windowsupdate", "msedge", "skype", "xboxlive")
    interesting = [u for u in urls
                   if ("/api/" in u or "json" in u.lower() or "/results" in u
                       or "pov" in u.lower())
                   and not any(n in u for n in noise)]
    static = (".css", ".js", ".png", ".jpg", ".svg", ".woff", ".woff2", ".ttf",
              ".ico", ".gif", ".webp", ".map")
    dynamic = [u for u in urls
               if not any(u.split("?")[0].endswith(ext) for ext in static)
               and not any(n in u for n in noise)]
    print("\nВсе НЕстатичные запросы (%d):" % len(dynamic))
    for u in dynamic[:40]:
        print("  ", u[:220])

    print("\nИнтересных URL: %d (все %d в netlog_urls.txt)" % (len(interesting), len(urls)))
    for u in interesting[:60]:
        print("  ", u[:220])

    print("\nПараметры пагинации/фильтров, которые встретились:")
    params = set()
    for u in interesting:
        for name in re.findall(r'[?&]([A-Za-z_][A-Za-z0-9_]{2,20})=', u):
            params.add(name)
    print("  ", ", ".join(sorted(params)) or "—")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    target = sys.argv[1] if len(sys.argv) > 1 else "https://fgis.gost.ru/fundmetrology/cm/results"
    out = None
    if "--save" in sys.argv:
        out = sys.argv[sys.argv.index("--save") + 1]
    main(target, out)

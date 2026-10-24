#!/usr/bin/env python3
"""readme-forge: the tools behind a good repo front page.

  python3 rf.py shoot https://example.com -o docs/assets/readme/hero.png
  python3 rf.py shoot ./dist -o hero.png --size 1280x800 --wait 4000 --stable 5000
  python3 rf.py term "mycli --help" -o docs/assets/readme/cli.png --cwd ../mycli
  python3 rf.py check README.md
  python3 rf.py sidebar owner/repo --description "..." --homepage https://... --topics a,b,c
  python3 rf.py audit ~/projects

shoot/term need Playwright (pip install playwright). Everything else is stdlib.
Run rf.py with the python that has Playwright, not a project's venv.
"""
import argparse
import contextlib
import functools
import html
import http.server
import json
import mimetypes
import os
import re
import socketserver
import subprocess
import sys
import threading
from pathlib import Path

ASSET_DIR = "docs/assets/readme"
MAX_IMAGE_KB = 600


# ---------------------------------------------------------------- shoot

@contextlib.contextmanager
def serve(directory: Path):
    """Serve a static folder on a free localhost port."""
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    handler = functools.partial(Quiet, directory=str(directory))
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as httpd:
        t = threading.Thread(target=httpd.serve_forever, daemon=True)
        t.start()
        try:
            yield f"http://127.0.0.1:{httpd.server_address[1]}/"
        finally:
            httpd.shutdown()


def browser():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise SystemExit("shoot/term need Playwright: pip install playwright && playwright install chromium")
    return sync_playwright()


def parse_size(s: str) -> tuple[int, int]:
    w, h = s.lower().split("x")
    return int(w), int(h)


def capture(page, out: Path, full: bool, selector: str | None, clip: dict | None = None):
    out.parent.mkdir(parents=True, exist_ok=True)
    kind = "jpeg" if out.suffix.lower() in (".jpg", ".jpeg") else "png"
    opts = {"path": str(out), "type": kind}
    if kind == "jpeg":
        opts["quality"] = 85
    if selector:
        page.locator(selector).first.screenshot(**opts)
    else:
        page.screenshot(full_page=full and not clip, clip=clip, **opts)
    while kind == "jpeg" and out.stat().st_size > MAX_IMAGE_KB * 1024 and opts["quality"] > 55:
        opts["quality"] -= 10
        if selector:
            page.locator(selector).first.screenshot(**opts)
        else:
            page.screenshot(full_page=full and not clip, clip=clip, **opts)
    kb = out.stat().st_size // 1024
    note = f"  (over {MAX_IMAGE_KB}KB: use .jpg, --scale 1.5 or a smaller --size)" if kb > MAX_IMAGE_KB else ""
    print(f"{out}  {kb}KB{note}")


def cmd_shoot(a):
    target = a.target
    w, h = parse_size(a.size)
    with contextlib.ExitStack() as stack:
        if not re.match(r"https?://", target):
            p = Path(target).resolve()
            root, page_name = (p, "") if p.is_dir() else (p.parent, p.name)
            target = stack.enter_context(serve(root)) + page_name
        early = a.load in ("domcontentloaded", "commit") and not a.idle
        if early:
            # Playwright's screenshot waits for document.fonts.ready, which never settles while the page
            # is still loading; skip that wait and do a bounded one ourselves before capture.
            os.environ["PW_TEST_SCREENSHOT_NO_FONTS_READY"] = "1"
        pw = stack.enter_context(browser())
        b = pw.chromium.launch()
        ctx = b.new_context(
            viewport={"width": w, "height": h},
            device_scale_factor=a.scale,
            color_scheme="dark" if a.dark else "light",
            is_mobile=a.mobile, has_touch=a.mobile,
        )
        if a.seed is not None:
            ctx.add_init_script(SEED_JS % a.seed)
        for js in a.init_js or []:
            ctx.add_init_script(Path(js).read_text() if js.endswith(".js") and Path(js).is_file() else js)
        for spec in a.mock or []:
            pattern, _, path = spec.rpartition("=")  # globs may contain "=", file names rarely do
            if not pattern or not Path(path).is_file():
                raise SystemExit(f"--mock {spec!r}: expected url-glob=existing-file")
            body = Path(path).read_bytes()
            ctype = mimetypes.guess_type(path)[0] or "text/plain"
            ctx.route(pattern, fulfiller(body, ctype))
        page = ctx.new_page()
        page.goto(target, wait_until="networkidle" if a.idle else a.load, timeout=60000)
        if a.dark:
            page.evaluate(DARK_JS)
        for css in a.hide or []:
            page.add_style_tag(content=f"{css} {{ visibility: hidden !important; }}")
        page.wait_for_timeout(a.wait)
        if a.click or a.js or a.drag or a.wheel or a.type:
            for xy in a.click or []:
                x, y = (int(v) for v in xy.split(","))
                page.mouse.click(x, y)
                page.wait_for_timeout(300)
            for spec in a.type or []:
                sel, _, text = spec.partition("=")
                page.locator(sel).first.click()
                page.keyboard.type(text, delay=40)
                page.wait_for_timeout(300)
            for spec in a.drag or []:
                x1, y1, x2, y2 = (float(v) for v in spec.split(","))
                page.mouse.move(x1, y1)
                page.mouse.down()
                for i in range(1, 21):
                    page.mouse.move(x1 + (x2 - x1) * i / 20, y1 + (y2 - y1) * i / 20)
                    page.wait_for_timeout(15)
                page.mouse.up()
                page.wait_for_timeout(300)
            if a.wheel:
                page.mouse.move(w / 2, h / 2)
                page.mouse.wheel(0, a.wheel)
                page.wait_for_timeout(300)
            if a.js:
                js = a.js
                if re.search(r"\bawait\b", js) and not re.match(r"\s*(async\b|\()", js):
                    js = f"(async () => {{ {js} }})()"
                page.evaluate(js)  # a returned promise is awaited
            page.wait_for_timeout(a.settle)
        if a.dark:
            page.evaluate(DARK_JS)  # again, in case the app re-applied its saved theme
        if early:
            page.evaluate("Promise.race([document.fonts.ready, new Promise(r => setTimeout(r, 3000))]).then(() => 0)")
        if a.stable:
            wait_stable(page, a.stable)
        clip = None
        if a.clip:
            x, y, cw, ch = (float(v) for v in a.clip.split(","))
            clip = {"x": x, "y": y, "width": cw, "height": ch}
        if clip and a.full:
            page.set_viewport_size({"width": w, "height": max(h, int(clip["y"] + clip["height"]) + 1)})
            page.wait_for_timeout(300)
        capture(page, Path(a.out), a.full, a.selector, clip)
        b.close()


def wait_stable(page, timeout_ms: int, every_ms: int = 250):
    """Poll the viewport until two frames in a row are identical, or give up at timeout_ms."""
    last, waited = page.screenshot(), 0
    while waited < timeout_ms:
        page.wait_for_timeout(every_ms)
        waited += every_ms
        now = page.screenshot()
        if now == last:
            print(f"note: page stable after {waited}ms", file=sys.stderr)
            return
        last = now
    print(f"note: page still changing after {timeout_ms}ms (--stable); capturing anyway", file=sys.stderr)


DARK_JS = """(() => { const r = document.documentElement;
  r.classList.remove('light'); r.classList.add('dark'); r.style.colorScheme = 'dark';
  r.setAttribute('data-theme', 'dark'); r.setAttribute('data-bs-theme', 'dark');
  if (document.body) { document.body.classList.remove('light'); document.body.classList.add('dark'); } })()"""


def fulfiller(body: bytes, ctype: str):
    def handle(route, _request=None):
        route.fulfill(status=200, body=body, content_type=ctype, headers={"Access-Control-Allow-Origin": "*"})
    return handle


SEED_JS = """(() => { let s = %d >>> 0;
  Math.random = () => { s = (s + 0x6D2B79F5) >>> 0; let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; })();"""


# ---------------------------------------------------------------- term

ANSI = re.compile(r"\x1b\[([0-9;]*)m")
COLORS = {30: "#555", 31: "#ff6b6b", 32: "#7ee787", 33: "#f2cc60", 34: "#79c0ff", 35: "#d2a8ff",
          36: "#76e3ea", 37: "#e6edf3", 90: "#8b949e", 91: "#ffa198", 92: "#56d364", 93: "#e3b341",
          94: "#a5d6ff", 95: "#e2c5ff", 96: "#b3f0ff", 97: "#ffffff"}


def ansi_to_html(text: str) -> str:
    out, style, pos = [], {}, 0
    open_span = False
    for m in ANSI.finditer(text):
        out.append(html.escape(text[pos:m.start()]))
        pos = m.end()
        for code in [int(c) for c in (m.group(1) or "0").split(";") if c.isdigit()] or [0]:
            if code == 0:
                style = {}
            elif code == 1:
                style["font-weight"] = "700"
            elif code == 2:
                style["opacity"] = ".6"
            elif code in COLORS:
                style["color"] = COLORS[code]
        if open_span:
            out.append("</span>")
            open_span = False
        if style:
            out.append('<span style="%s">' % ";".join(f"{k}:{v}" for k, v in style.items()))
            open_span = True
    out.append(html.escape(text[pos:]))
    if open_span:
        out.append("</span>")
    return "".join(out)


TERM_PAGE = """<!doctype html><meta charset="utf-8"><style>
body{margin:0;padding:28px;background:transparent;font:14px/%(lh)s %(font)s}
.win{display:inline-block;min-width:640px;max-width:%(maxw)spx;background:#0d1117;color:#e6edf3;border-radius:10px;
 box-shadow:0 12px 40px rgba(0,0,0,.35);overflow:hidden;border:1px solid #30363d}
.bar{display:flex;align-items:center;gap:8px;padding:10px 14px;background:#161b22;border-bottom:1px solid #30363d}
.dot{width:12px;height:12px;border-radius:50%%}.t{margin-left:10px;color:#8b949e;font-size:12px}
pre{margin:0;padding:16px 18px 18px;white-space:pre-wrap;word-break:break-word}.p{color:#7ee787}
</style><div class="win"><div class="bar"><span class="dot" style="background:#ff5f57"></span>
<span class="dot" style="background:#febc2e"></span><span class="dot" style="background:#28c840"></span>
<span class="t">%(title)s</span></div><pre>%(body)s</pre></div>"""


def cmd_term(a):
    if a.text:
        body = Path(a.text).read_text()
        shown = a.title or ""
    else:
        env = dict(os.environ, FORCE_COLOR="1", CLICOLOR_FORCE="1", COLUMNS=str(a.cols), TERM="xterm-256color")
        r = subprocess.run(a.command, shell=True, cwd=a.cwd, capture_output=True, text=True, env=env, timeout=120)
        body = (r.stdout if a.no_stderr else r.stdout + r.stderr).rstrip()
        shown = a.title or a.command
    lines = body.splitlines()
    if len(lines) > a.max_lines:
        body = "\n".join(lines[: a.max_lines] + [f"\x1b[2m… {len(lines) - a.max_lines} more lines\x1b[0m"])
        print(f"note: output cut to {a.max_lines} of {len(lines)} lines (--max-lines)", file=sys.stderr)
    prompt = "" if a.text else f'<span class="p">$</span> {html.escape(a.command)}\n'
    page_html = TERM_PAGE % {"lh": a.line_height, "font": a.font, "maxw": a.cols * 9, "title": html.escape(shown), "body": prompt + ansi_to_html(body)}
    with browser() as pw:
        b = pw.chromium.launch()
        page = b.new_page(device_scale_factor=2, viewport={"width": a.cols * 9 + 120, "height": 400})
        page.set_content(page_html)
        page.evaluate("document.fonts.ready.then(() => 0)")
        fonts = sorted({f["familyName"] for f in platform_fonts(page, "pre")})
        if len(fonts) > 1:
            print(f"note: text drawn with {', '.join(fonts)}; some glyphs fell back from the first --font", file=sys.stderr)
        capture(page, Path(a.out), False, ".win")
        b.close()


def platform_fonts(page, selector: str) -> list[dict]:
    """The fonts Chromium actually used for an element's text."""
    cdp = page.context.new_cdp_session(page)
    cdp.send("DOM.enable")
    cdp.send("CSS.enable")
    root = cdp.send("DOM.getDocument")["root"]["nodeId"]
    node = cdp.send("DOM.querySelector", {"nodeId": root, "selector": selector})["nodeId"]
    return cdp.send("CSS.getPlatformFontsForNode", {"nodeId": node})["fonts"]


# ---------------------------------------------------------------- check

PERSONAL = [
    (r"[\w.+-]+@(gmail|yahoo|outlook|hotmail|icloud)\.com", "personal email"),
    (r"\+?\d[\d -]{8,}\d", "phone-like number"),
    (r"/Users/[a-z]+/", "local home path"),
    (r"(sk-[A-Za-z0-9]{20,}|AIza[0-9A-Za-z_-]{30,}|ghp_[A-Za-z0-9]{30,}|xox[bpas]-[A-Za-z0-9-]{20,})", "API key"),
]


def slugify(heading: str) -> str:
    s = re.sub(r"<[^>]+>", "", heading).strip().lower()
    s = re.sub(r"[^\w\- ]", "", s)
    return s.replace(" ", "-")


def check(readme: Path) -> list[str]:
    text = readme.read_text()
    root = readme.parent
    issues = []
    lines = text.splitlines()

    head = "\n".join(lines[:40])
    if 'align="center"' not in head:
        issues.append("header: no centred hero block in the first 40 lines")
    if not re.search(r"<h1>|^# ", head, re.M):
        issues.append("header: no title")

    anchors = {slugify(m.group(1)) for m in re.finditer(r"^#{1,6} (.+)$", text, re.M)}
    anchors |= set(re.findall(r'id="([^"]+)"', text))
    for frag in re.findall(r'\]\(#([^)]+)\)|href="#([^"]+)"', text):
        f = frag[0] or frag[1]
        if f not in anchors:
            issues.append(f"link: #{f} matches no heading")

    refs = re.findall(r'<img[^>]+src="([^"]+)"', text) + re.findall(r"!\[[^\]]*\]\(([^)\s]+)", text)
    local = [r for r in refs if not re.match(r"https?://", r)]
    for r in local:
        p = root / r.split("#")[0]
        if not p.exists():
            issues.append(f"image: {r} does not exist")
        elif p.stat().st_size > MAX_IMAGE_KB * 1024:
            issues.append(f"image: {r} is {p.stat().st_size // 1024}KB (keep under {MAX_IMAGE_KB}KB)")
    for m in re.finditer(r"<img(?![^>]*alt=)[^>]*>", text):
        issues.append(f"image: missing alt text: {m.group(0)[:60]}")

    for m in re.finditer(r"\]\(((?!https?://|#|mailto:)[^)\s]+)\)", text):
        target = m.group(1).split("#")[0]
        if target and not (root / target).exists():
            issues.append(f"link: {target} does not exist")

    prose = re.sub(r'https?://[^\s)"\']+', "", text)  # badge URLs carry colour codes that look like numbers
    prose = re.sub(r"\b\d{4}-\d\d-\d\d\b", "DATE", prose)  # ISO dates, alone or in ranges
    for pat, label in PERSONAL:
        for m in re.finditer(pat, prose if label == "phone-like number" else text):
            if label == "phone-like number" and (re.fullmatch(r"[\d.]+", m.group(0)) or "-" not in m.group(0) and " " not in m.group(0)):
                continue
            issues.append(f"privacy: {label}: {m.group(0)[:40]}")

    visible = len(re.sub(r"<details>.*?</details>", "", text, flags=re.S).splitlines())
    if visible > 220:
        issues.append(f"length: {visible} lines outside <details>; fold reference material away")
    if not re.search(r"^## ", text, re.M):
        issues.append("structure: no ## sections")
    return issues


def cmd_check(a):
    bad = 0
    for f in a.readme:
        issues = check(Path(f))
        print(f"{f}: {'ok' if not issues else str(len(issues)) + ' issue(s)'}")
        for i in issues:
            print(f"  - {i}")
        bad += bool(issues)
    return 1 if bad else 0


# ---------------------------------------------------------------- sidebar

def gh(*args, data=None):
    r = subprocess.run(["gh", *args], input=data, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(r.stderr.strip())
    return r.stdout


def cmd_sidebar(a):
    edit = ["repo", "edit", a.repo]
    if a.description is not None:
        edit += ["--description", a.description]
    if a.homepage is not None:
        edit += ["--homepage", a.homepage]
    if len(edit) > 3:
        gh(*edit)
    if a.topics is not None:
        names = [t.strip().lower() for t in a.topics.split(",") if t.strip()]
        gh("api", "-X", "PUT", f"repos/{a.repo}/topics", "--input", "-", data=json.dumps({"names": names}))
    print(gh("repo", "view", a.repo, "--json", "description,homepageUrl,repositoryTopics",
             "-q", '"\\(.description)\\n\\(.homepageUrl)\\n\\([.repositoryTopics[]?.name]|join(", "))"').strip())


# ---------------------------------------------------------------- audit

def cmd_audit(a):
    rows = []
    for d in sorted(Path(a.dir).expanduser().iterdir()):
        if not (d / ".git").exists():
            continue
        readme = next((d / n for n in ("README.md", "readme.md", "Readme.md") if (d / n).exists()), None)
        if not readme:
            rows.append((d.name, 0, 0, "no README"))
            continue
        text = readme.read_text(errors="ignore")
        imgs = len(re.findall(r"<img|!\[", text))
        rows.append((d.name, len(text.splitlines()), imgs, "ok" if not check(readme) else f"{len(check(readme))} issues"))
    for name, n, imgs, status in rows:
        print(f"{name:34} {n:5} lines {imgs:3} imgs  {status}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("shoot", help="screenshot a URL, folder or html file")
    s.add_argument("target")
    s.add_argument("-o", "--out", required=True)
    s.add_argument("--size", default="1280x800", help="viewport WxH (default 1280x800)")
    s.add_argument("--scale", type=float, default=2, help="device pixel ratio (default 2)")
    s.add_argument("--wait", type=int, default=2500, help="ms to wait after load, for animation/data (default 2500)")
    s.add_argument("--settle", type=int, default=1200, help="ms to wait after --click/--js, before capture (default 1200)")
    s.add_argument("--clip", help="x,y,w,h crop in CSS pixels (with --full it can reach below the fold)")
    s.add_argument("--load", default="load", choices=["load", "domcontentloaded", "networkidle", "commit"],
                   help="navigation event to wait for (default load; domcontentloaded for pages that never finish loading)")
    s.add_argument("--idle", action="store_true", help="same as --load networkidle")
    s.add_argument("--stable", type=int, metavar="MS", help="before capture, wait up to MS until two frames 250ms apart match")
    s.add_argument("--full", action="store_true", help="full-page capture")
    s.add_argument("--selector", help="capture just this element")
    s.add_argument("--mobile", action="store_true", help="mobile emulation (use with --size 390x844)")
    s.add_argument("--dark", action="store_true", help="prefers-color-scheme: dark, plus html.dark and data-theme=dark for class-based themes")
    s.add_argument("--hide", action="append", help="CSS selector to hide (cookie banners), repeatable")
    s.add_argument("--click", action="append", help="x,y to click after --wait, repeatable")
    s.add_argument("--js", help="JavaScript to run after --wait and the interactions below; a returned promise (or top-level await) is awaited")
    s.add_argument("--type", action="append", help='"selector=text": click the field and type, repeatable')
    s.add_argument("--drag", action="append", help="x1,y1,x2,y2 mouse drag (drawing tools, 3D orbit), repeatable")
    s.add_argument("--wheel", type=int, help="scroll-wheel delta at the centre; positive zooms most 3D scenes out")
    s.add_argument("--mock", action="append", help='"url-glob=file.json": answer matching requests with a local file (demo data)')
    s.add_argument("--seed", type=int, help="make Math.random deterministic so captures repeat")
    s.add_argument("--init-js", action="append", help="JS (or a .js file) run before the page's own scripts, e.g. to seed localStorage; repeatable")
    s.set_defaults(fn=cmd_shoot)

    t = sub.add_parser("term", help="render a command's output as a terminal-window image")
    t.add_argument("command", nargs="?", default="")
    t.add_argument("-o", "--out", required=True)
    t.add_argument("--cwd")
    t.add_argument("--text", help="render this file's text instead of running a command")
    t.add_argument("--title")
    t.add_argument("--cols", type=int, default=92)
    t.add_argument("--max-lines", type=int, default=28, help="cut longer output, with a note on stderr (default 28)")
    t.add_argument("--font", default='Menlo, "DejaVu Sans Mono", Consolas, monospace', help="CSS font-family (default Menlo first)")
    t.add_argument("--line-height", default="1.3", help="1.2 keeps box-drawing tables joined (default 1.3)")
    t.add_argument("--no-stderr", action="store_true", help="drop stderr (warnings, progress bars)")
    t.set_defaults(fn=cmd_term)

    c = sub.add_parser("check", help="lint README files")
    c.add_argument("readme", nargs="+")
    c.set_defaults(fn=cmd_check)

    b = sub.add_parser("sidebar", help="set GitHub description, website and topics (topics are replaced)")
    b.add_argument("repo", help="owner/name")
    b.add_argument("--description")
    b.add_argument("--homepage")
    b.add_argument("--topics", help="comma list; replaces existing topics")
    b.set_defaults(fn=cmd_sidebar)

    u = sub.add_parser("audit", help="README status for every git repo in a folder")
    u.add_argument("dir")
    u.set_defaults(fn=cmd_audit)

    a = ap.parse_args()
    return a.fn(a) or 0


if __name__ == "__main__":
    sys.exit(main())

"""Quick checks for rf.py.  python3 -m unittest discover tests   (shoot/term tests need Playwright + Pillow)"""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import rf  # noqa: E402

try:
    import playwright  # noqa: F401
    from PIL import Image
    HAVE_BROWSER = True
except ImportError:
    HAVE_BROWSER = False

GREEN = (0, 128, 0)


def run(*args):
    return subprocess.run([sys.executable, str(ROOT / "rf.py"), *args], capture_output=True, text=True)


class Check(unittest.TestCase):
    def issues(self, body):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "README.md"
            p.write_text('<div align="center">\n<h1>x</h1>\n</div>\n\n## A\n' + body)
            return [i for i in rf.check(p) if "phone" in i]

    def test_iso_dates_are_not_phones(self):
        self.assertEqual(self.issues("On 2026-10-23. From 2026-10-23 2026-10-24, 2026-10-23 - 2026-10-24 "
                                     "and 2026-10-23 14:30.\n"), [])

    def test_phone_still_flagged(self):
        self.assertEqual(len(self.issues("Call 415-555-0134.\n")), 1)


@unittest.skipUnless(HAVE_BROWSER, "needs Playwright and Pillow")
class Shoot(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def shoot(self, html, *args, name="page.html"):
        (self.dir / name).write_text("<!doctype html><style>body{margin:0;height:100vh;background:red}</style><body>" + html)
        out = self.dir / "out.png"
        r = run("shoot", str(self.dir / name), "-o", str(out), "--scale", "1", "--size", "200x200",
                "--wait", "0", "--settle", "0", *args)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.stderr = r.stderr
        return out

    def pixel(self, out, xy=(50, 50)):
        return Image.open(out).convert("RGB").getpixel(xy)

    def test_clip_with_full_reaches_below_fold(self):
        out = self.shoot('<div style="height:3000px"></div>'
                         '<div style="position:absolute;top:2000px;width:100px;height:100px;background:green"></div>',
                         "--full", "--clip", "0,2000,100,100")
        self.assertEqual(Image.open(out).size, (100, 100))
        self.assertEqual(self.pixel(out), GREEN)

    def test_seed_repeats(self):
        page = "<script>document.body.style.background=`hsl(${Math.random()*360},80%,50%)`</script>"
        a = self.shoot(page, "--seed", "7").read_bytes()
        b = self.shoot(page, "--seed", "7").read_bytes()
        c = self.shoot(page, "--seed", "8").read_bytes()
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)

    def test_init_js_runs_before_page(self):
        out = self.shoot("<script>if (localStorage.demo === 'yes') document.body.style.background='green'</script>",
                         "--init-js", "localStorage.demo = 'yes'")
        self.assertEqual(self.pixel(out), GREEN)

    def test_js_await(self):
        out = self.shoot("", "--js", "await new Promise(r => setTimeout(r, 400)); document.body.style.background = 'green'")
        self.assertEqual(self.pixel(out), GREEN)

    def test_dark_class_theme(self):
        out = self.shoot("<style>html.dark body{background:green}</style>", "--dark")
        self.assertEqual(self.pixel(out), GREEN)

    def test_dark_data_theme(self):
        out = self.shoot('<style>[data-theme=dark] body{background:green}</style>', "--dark")
        self.assertEqual(self.pixel(out), GREEN)

    def test_stable_waits_for_animation_to_end(self):
        page = ("<script>let f=0;(function t(){f++;document.body.style.background=f<90?`rgb(${f*2},0,0)`:'green';"
                "if(f<90)requestAnimationFrame(t)})()</script>")
        out = self.shoot(page, "--stable", "6000")
        self.assertEqual(self.pixel(out), GREEN)
        self.assertIn("stable after", self.stderr)

    def test_load_domcontentloaded(self):
        # the image never finishes, so "load" would hang; domcontentloaded must not
        out = self.shoot('<img src="http://10.255.255.1/x.png"><script>document.body.style.background="green"</script>',
                         "--load", "domcontentloaded")
        self.assertEqual(self.pixel(out, (150, 150)), GREEN)

    def test_drag_and_wheel(self):
        page = ("<script>let x0, ok=0;"
                "onpointerdown=e=>x0=e.clientX; onpointerup=e=>{if(e.clientX-x0>100) ok++; paint()};"
                "onwheel=e=>{if(e.deltaY>0) ok++; paint()};"
                "function paint(){if(ok==2) document.body.style.background='green'}</script>")
        out = self.shoot(page, "--drag", "20,100,180,100", "--wheel", "300")
        self.assertEqual(self.pixel(out), GREEN)

    def test_mock_with_query_string(self):
        (self.dir / "demo.json").write_text('{"ok": true}')
        page = ("<script>fetch('/api/data?x=1').then(r=>r.json())"
                ".then(j=>{if(j.ok) document.body.style.background='green'})</script>")
        out = self.shoot(page, "--mock", f"**/api/data?x=1={self.dir / 'demo.json'}", "--stable", "3000")
        self.assertEqual(self.pixel(out), GREEN)


@unittest.skipUnless(HAVE_BROWSER, "needs Playwright and Pillow")
class Term(unittest.TestCase):
    def test_truncation_is_reported_and_output_repeats(self):
        with tempfile.TemporaryDirectory() as d:
            outs = []
            for i in range(2):
                out = Path(d) / f"t{i}.png"
                r = run("term", "seq 1 40", "-o", str(out), "--max-lines", "10")
                self.assertEqual(r.returncode, 0, r.stderr)
                self.assertIn("cut to 10 of 40 lines", r.stderr)
                outs.append(out.read_bytes())
            self.assertEqual(outs[0], outs[1])


if __name__ == "__main__":
    unittest.main()

---
name: readme-forge
description: Use when writing or redoing a GitHub repo's README front page, or setting its description, website and topics.
---

# readme-forge: write a repo's front page

Kit: `~/projects/readme-forge` (github.com/parthchandak02/readme-forge). Read `STYLE.md` there
first, every time; it is the spec. `layouts/` has four skeletons (app, cli, visual, library);
`rf.py` has the tools.

## Steps for one repo

1. **Understand it from the code, not the old README.** Read the entry points, package
   manifest, config and recent `git log`. Note: what it does, for whom, the real data
   sources/APIs, how to run it, and whether there is a live URL (GitHub "Website" field, old
   README, `CNAME`, `wrangler.toml`, Pages settings). Keep any facts from the old README that are
   still true and useful; move long reference material into `<details>` rather than deleting it.
2. **Pick a layout**: `visual` (generative/data-viz web pieces), `app` (mobile/desktop/full web
   app), `cli` (command-line tools), `library` (clients, scripts, research/notes). Mix freely.
3. **Capture the hero image** into `docs/assets/readme/`:
   - Live site: `python3 ~/projects/readme-forge/rf.py shoot <url> -o docs/assets/readme/hero.jpg --wait 5000`
   - Static repo with `index.html` or a built `dist/`: `rf.py shoot ./dist -o ...` (it serves the folder itself).
   - CLI: `rf.py term "<the best command>" -o docs/assets/readme/cli.png --cwd <repo>`; if it needs
     credentials or network you don't have, write a realistic sample output to a scratch file
     from the code's actual output format and use `rf.py term --text file --title "<cmd>"`.
   - Live data: capture when there is something to show (an open park, a market day); if the
     default view is empty, pick a different region/item via URL params, `--js` or `--click`,
     `--type "sel=text"`, `--drag x1,y1,x2,y2` or `--wheel N` (all run after `--wait`; `--settle` waits
     after them). `--clip x,y,w,h` crops. `--mock "glob=file.json"` answers an API with demo data;
     `--seed N` freezes Math.random so a generative piece captures the same frame every run.
     `--init-js "localStorage.x='demo'"` (or a `.js` file) runs before the app's own scripts, so it can
     seed demo state without a reload. `--js` may use `await`; a returned promise is awaited.
   - Timing: `--wait` is a plain timer (animations do run in headless). `--stable 6000` then waits until
     two frames 250 ms apart match, for charts that animate in. Pages that never finish loading (live
     streams, long polls): `--load domcontentloaded`. `--dark` also sets `html.dark` and `data-theme="dark"`.
   - Demo data is fine and often necessary: a scratch copy of the app, a tiny fake API server, or a
     made-up input file, all with obviously fictional content. Say "demo data" in the caption.
   - Hardware projects: show what the device displays (a rendered preview), the web UI, or a
     wiring/architecture table. Never photos with people in them.
   - Always look at the image you captured. Retake if it's blank, mid-load, shows an error,
     a cookie banner, or anyone's personal data. No image beats a bad image.
4. **Write the README** from the layout, following STYLE.md. Never invent features, numbers or
   status; everything must be traceable to the code.
5. **Check**: `python3 ~/projects/readme-forge/rf.py check README.md` until it passes.
6. **Sidebar**: `rf.py sidebar <owner>/<repo> --description "..." --homepage "<live url or empty>" --topics a,b,c`.
7. **Commit only your files**: `git add README.md docs/assets/readme` (never `git add -A`; the repo
   may have the owner's unrelated uncommitted work). Message: `Rewrite README as a front page`.
   If a pre-commit secret scanner blocks the commit, read every flagged line; if all are false
   positives (placeholders, the word `.env`, image bytes), commit that one time with `--no-verify`.
   If anything looks like a real secret, stop and report it. Then `git push`.

## Practicalities

- Run `rf.py` with the system python that has Playwright, never inside a project venv.
- Some repos' `.gitignore` ignores everything by default; check `git status` after `git add` and
  use `git add -f README.md docs/assets/readme` if your files weren't staged.
- Rich/box-drawing tables: `rf.py term ... --line-height 1.2`. Drop warnings with `--no-stderr`.
  `term` prints a note on stderr when it cuts output (`--max-lines`, default 28) or when glyphs fall
  back from the first `--font` (default Menlo); the image shows "… N more lines".
- Viewing the rendered page on GitHub is optional; `rf.py check` is the gate. Private repos can't be
  viewed by `shoot` anyway.
- The owner's git-secrets hook flags `.env`, `.venv`, `environ`, `<your-key>` placeholders and long
  upper-case strings. Read the flagged lines; if every one is that kind of false positive, commit
  with `--no-verify`.

## Don'ts

- Don't stop or kill any process you didn't start. Track the PID of every server you launch and
  kill only that PID; never `pkill` by name or port. The owner runs live services locally.
- Don't touch any file other than `README.md` and `docs/assets/readme/*`.
- Don't put personal data (emails, phone numbers, home addresses, family names, account numbers,
  private messages, local `/Users/...` paths) in the README or in screenshots, even for private repos.
- Don't add vanity badges, emoji in prose, or marketing superlatives.
- Don't run paid APIs to make a screenshot.

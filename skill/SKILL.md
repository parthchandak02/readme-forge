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

## Don'ts

- Don't touch any file other than `README.md` and `docs/assets/readme/*`.
- Don't put personal data (emails, phone numbers, home addresses, family names, account numbers,
  private messages, local `/Users/...` paths) in the README or in screenshots, even for private repos.
- Don't add vanity badges, emoji in prose, or marketing superlatives.
- Don't run paid APIs to make a screenshot.

# The front-page style

A repo's README is its landing page. Someone arrives from a link, a search or a profile, and
gives it about ten seconds. In that time they need to learn three things: what this is, what it
looks like, and whether it's for them. Everything below serves that.

The reference implementation is [calarm](https://github.com/parthchandak02/calarm).

## The shape

```
centred hero      icon or wordmark · name · one-line pitch · hook line · 3-6 badges · section links · hero image
the problem       2-4 sentences: what hurts today and why this exists
how it works      3 steps in a 3-column table (or a short numbered list)
the visual        a second image or a GIF of the thing in use, with a <sub> caption
features          5-9 bullets, each **bold claim.** then one plain sentence
comparison        optional table against the obvious alternatives
run it / use it   the shortest path from clone to working, in one code block
<details>         project layout, documentation index, configuration, API notes
footer            centred <sub> "Built with ..." line
```

Not every repo needs every section. Hardware projects use the `app` layout with a "Hardware"
table (part, role, link) in place of the comparison, and a rendered preview of what the device
shows as the hero. A 200-line generative-art piece needs the hero, one
paragraph on the data, "how it works", the live link and the run commands. A library needs
install, a 10-line usage example and the API. Drop sections; never pad them.

## The hero

- **Name** in `<h1>`, exactly as the project brands itself (CALarm, not calarm).
- **Pitch**: one bold line, under ~8 words, that says what it *is*. "Your calendar, as real alarms."
- **Hook**: one italic line that says why it matters, usually by naming the pain.
  "A calendar notification is a banner you swipe away. A meeting deserves an alarm."
- **Badges**: 3-6, inside `<h6>` so they render small. Platform, language, the one key
  framework, the data source or API, and status. `style=flat-square`, colours from the
  project's own palette (fall back to `111111` and one accent). No vanity badges (stars,
  downloads, "made with love").
- **Section links**: 3-4 bold anchors separated by ` · `.
- **Hero image**: the most honest picture of the thing working. Live sites and apps get a real
  screenshot; CLIs get `rf.py term` output of the single most impressive command; libraries get
  a terminal image of the usage example running. Below it a `<sub>` caption saying what the
  viewer is looking at and whether the data is real or demo.
- If there is a live site, the first section link is `<a href="URL"><b>Live demo</b></a>`.

## Voice

- Write for a smart stranger, not for yourself. No internal codenames, ticket numbers, or
  "as discussed".
- Concrete beats clever. "Rings through Silent and Focus" beats "never miss what matters".
- Plain verbs, short sentences, no exclamation marks, no emoji in prose.
- Name the real data source, API, model or hardware. Specifics are what make it credible.
- Honest status: say "private beta", "experiment", "archived" or "works on my machine" when true.
- Never invent features, numbers, users or benchmarks. If the code doesn't do it, it's not on
  the page. Read the code before writing.

## Images

- Store in `docs/assets/readme/` (create it). Lower-case kebab names: `hero.png`, `cli.png`.
- Capture at 2x, show at a fixed width (`width="720"` for desktop shots, `width="32%"` for
  phone shots side by side). Keep each file under 600 KB; use `.jpg` for photographic or 3D
  content, `.png` for UI and terminals.
- Every `<img>` has `alt` text that describes the content, not "screenshot".
- Never commit images containing real personal data: names, emails, addresses, account numbers,
  private messages. Use demo data, or crop.
- Demo data is fine and usually necessary: fake API, made-up files, public-domain sample photos.
  Say so in the caption.
- Make captures repeatable: `rf.py shoot --seed N` for anything random, `--mock` or `--init-js` for
  demo data, `--stable MS` for pages that animate in. Run `python3 rf.py shoot -h` for every option.
- No image is better than a bad image. If the thing has no honest visual, use a text-only hero.

## Private repos

Private repos get the same treatment; they are front pages for future you. Keep personal facts
out of the README anyway (repos go public later): describe what the tool does, not whose data
it holds.

## Sidebar

The GitHub "About" box is part of the front page:

- **Description**: the pitch line, expanded to one sentence of plain text, under 120 characters.
  No emoji.
- **Website**: the live URL if there is one, otherwise empty.
- **Topics**: 4-8 lower-case topics: language, framework, domain, data source, platform.

`python3 rf.py sidebar owner/repo --description ... --homepage ... --topics ...` sets all three
(topics are replaced, not appended).

## Before you push

`python3 rf.py check README.md` must pass: hero present, anchors resolve, images exist and are
small enough, alt text present, no personal email, local paths or keys. Viewing the rendered
page on GitHub afterwards is worth it for public repos.

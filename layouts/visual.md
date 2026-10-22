<!-- Layout: visual / generative / data-viz web piece. Replace every {PLACEHOLDER}; delete what doesn't apply. -->
<div align="center">

<h1>{Name}</h1>

<p><b>{Pitch: what you see, in under 8 words.}</b></p>

<p><i>{Hook: the real-world data or idea behind it.}</i></p>

<h6>

![{Data}](https://img.shields.io/badge/data-{Data_Source}-{ACCENT}?style=flat-square)
![{Stack}](https://img.shields.io/badge/{Three.js}-{r0}-111111?style=flat-square&logo={threedotjs}&logoColor=white)
![Live](https://img.shields.io/badge/live-{domain}-{ACCENT}?style=flat-square)

</h6>

<a href="{LIVE_URL}"><b>Live demo</b></a> ·
<a href="#how-it-works"><b>How it works</b></a> ·
<a href="#run-it"><b>Run it</b></a>

<br><br>

<a href="{LIVE_URL}"><img src="docs/assets/readme/hero.jpg" width="100%" alt="{What the frame shows}"></a>

<sub>{Live capture, date or "real data at capture time".}</sub>

</div>

<br>

{One short paragraph: what you are looking at and why it is interesting.}

## How it works

| Data | Drives |
|---|---|
| {wave height (Open-Meteo Marine)} | {vertex displacement} |
| {swell direction} | {wave field rotation} |

{Interaction: what clicking, dragging or hovering does.}

## Run it

```bash
git clone https://github.com/{owner}/{repo}.git
cd {repo}
npm install && npm run dev
```

<br>

<div align="center">
<sub>Built with {stack}. Data from {source}.</sub>
</div>

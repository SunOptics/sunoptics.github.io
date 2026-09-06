# ivansuun.github.io — Yifan Sun

The personal research website of Yifan Sun (nonlinear photonics, cavity solitons,
Kerr resonators). Hand-written HTML and CSS, generated from JSON by a single
Python script. No framework, no npm, no build service — GitHub Pages serves the
committed files directly.

Live at **https://ivansuun.github.io**

---

## 中文维护手册

### 一句话原理

内容全部放在 `data/*.json`，运行 `python3 tools/build.py` 就会把它们渲染成
`index.html`、`research/index.html` 等文件。你改 JSON，跑一次脚本，提交，网站就更新了。
**永远不要直接改生成出来的 `.html` 文件** —— 下次跑脚本会被覆盖。

### 日常操作

```bash
python3 tools/build.py
```

跑完会打印每个生成文件的大小。然后：

```bash
git add -A && git commit -m "Update publications" && git push
```

推上去大约 1 分钟后网站生效。

### 本地预览

```bash
python3 -m http.server 4173
```

然后打开 http://localhost:4173 。

### 我要改什么，就改哪个文件

| 想做的事 | 改这个文件 |
| --- | --- |
| 加一篇论文 / 会议报告 | `data/publications.json` |
| 加一条动态（论文接收、获奖、受邀报告） | `data/news.json` |
| 改研究方向的介绍文字 | `data/research.json` |
| 改经历、学位、基金、奖项 | `data/cv.json` |
| 改姓名、职位、邮箱、Scholar/ORCID 链接、SEO 描述 | `data/site.json` |
| 加图片或视频到 Gallery | `data/gallery.json` |
| 改配色、字号、间距 | `assets/css/site.css` 顶部的 `:root` 变量 |

### 加一篇论文

在 `data/publications.json` 的 `"publications"` 数组里加一条。字段说明：

```json
{
  "id": "sun-2027-prl-something",        // 唯一标识，用作页面锚点，别用序号
  "type": "journal",                     // journal | preprint | chapter | conference
  "authors": ["Y. Sun", "F. Leo"],       // 你自己写成 "Y. Sun" 会自动加粗
  "title": "论文标题",
  "venue": "Phys. Rev. Lett.",
  "volume": "131", "pages": "137201", "year": 2027,
  "doi": "10.1103/...",                  // 没有就写 null
  "arxiv": "2504.04788",                 // 没有就写 null
  "book": null,                          // 只有 type=chapter 才填（书名）
  "role": "first",                       // first | corresponding | co
  "invited": false,                      // true 会显示 INVITED 标签
  "award": null,                         // 例如 "Best Oral Award"
  "presentation": null,                  // 会议才填：oral | poster | invited
  "location": null,                      // 会议才填："San Jose, USA"
  "topic": "cavity-solitons",            // cavity-solitons | multimode-fiber | nanolasers | noise | other
  "status": "published",                 // published | accepted | preprint | upcoming
  "selected": false,                     // true 会出现在首页「五篇论文」里（保持只有 5 篇）
  "blurb": null                          // selected 为 true 时写一句大白话说明
}
```

作者名字里加 `*`（例如 `"Y. Sun*"`）会渲染成通讯作者星号。

### 需要你补的两处占位

1. **`data/gallery.json` 里的 `figures`** —— 现在是虚线占位框。把论文里的图存成
   `assets/img/xxx.png`，再把对应条目的 `src` 改成那个路径，图就会显示出来。
2. **`data/gallery.json` 里的 `videos`** —— 把 YouTube / Vimeo 的 embed 链接填进 `embed`。

（Google Scholar、ORCID、arXiv 三个链接已经填好了，并且写进了页面的 JSON-LD `sameAs`，
让搜索引擎知道这个网站、你的 Scholar 主页和 ORCID 是同一个人 —— 重名的 Yifan Sun 不少，
这一步对搜到你很关键。）

### 首页那张图是什么

不是视频，也不是图片。是你自己的方程在访客浏览器里被实时求解：

$$\partial_t E = S - (1 + i\theta)E + i|E|^2E + i\,\partial_\tau^2 E$$

`assets/js/lle.js` 用分步傅里叶法（线性+驱动项在频域精确积分，克尔项在时域做相位旋转，
Strang 分裂）解 Lugiato–Lefever 方程；`assets/js/waterfall.js` 把连续若干个腔内往返
画成隐藏线瀑布图。画完一次就停止，之后整个网站不再有任何动画帧。

`tools/make_assets.py` 是同一套物理的纯 Python 版本，用来离线生成
`assets/img/soliton-rule.svg`（姓名下方那条细线）、`favicon.svg` 和 `og.png`（分享卡片图）。
想换图就改参数重跑：

```bash
python3 tools/make_assets.py
python3 tools/build.py
```

---

## Layout

```
data/            content — the only files you normally edit
tools/build.py   renders data/ into the pages at the repo root
tools/make_assets.py   generates the SVG rule, favicon and OG image from the physics
tools/templates/ the shared HTML shell
assets/css/      site.css (design tokens first), fonts.css
assets/js/       lle.js (solver), waterfall.js (figure), site.js (theme), pubs.js (filter)
assets/fonts/    Newsreader + IBM Plex Mono, self-hosted — no request reaches Google
index.html …     generated; do not edit by hand
```

## Notes

- Fonts are self-hosted deliberately: `fonts.gstatic.com` would send every
  visitor's IP to Google, which is neither necessary nor appropriate on a page
  hosted by an EU institution's researcher.
- `.nojekyll` skips Jekyll processing, so deploys are fast and `_`-prefixed
  paths are served as-is.
- Everything a crawler needs — titles, descriptions, JSON-LD, the publication
  list — is in the served HTML, never assembled by JavaScript.

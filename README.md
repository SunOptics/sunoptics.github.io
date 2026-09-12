# ivansuun.github.io — Yifan Sun

Yifan Sun 的个人研究网站，介绍非线性光子学、腔孤子和 Kerr 谐振器研究。
内容保存在 JSON 中，由一个 Python 脚本生成静态 HTML；GitHub Pages 直接提供仓库中的页面。

网站：[ivansuun.github.io](https://ivansuun.github.io)

## 维护与预览

修改内容或模板后，在项目根目录运行：

```bash
python3 tools/build.py
python3 tools/check.py
python3 -m http.server 4173
```

然后打开 [本地预览](http://localhost:4173)。确认页面后，将源文件和生成文件一起提交并推送到 GitHub。

日常内容编辑 `data/*.json`；页面结构编辑 `tools/build.py`，共用页头、导航和页脚编辑
`tools/templates/base.html`。**不要直接修改生成的 HTML**，下一次构建会覆盖这些改动。

| 想修改的内容 | 文件 |
| --- | --- |
| 论文、预印本、章节、会议报告 | `data/publications.json` |
| 动态、获奖、受邀报告 | `data/news.json` |
| 研究方向、相关论文和媒体引用 | `data/research.json` |
| 经历、学位、基金和奖项 | `data/cv.json` |
| 姓名、职位、联系链接、首页介绍、页面元信息 | `data/site.json` |
| 图片、视频、首页与分享图 | `data/media.json` |
| 配色、字体大小、留白、响应式布局 | `assets/css/site.css` |
| 字体文件声明 | `assets/css/fonts.css` |
| 各页面结构 | `tools/build.py` |
| 共用 HTML 外壳 | `tools/templates/base.html` |

## 页面结构

- **首页**：简短的研究者介绍、孤子图、四个研究方向、精选论文和最近三条动态。
  更早动态收在可展开的归档中。目前有五篇精选论文，数量随数据调整。
- **Research**：每个方向集中呈现介绍、研究图和视频；相关文献可展开查看。
- **Publications**：完整文献列表，支持按标题、作者、期刊或会议名称搜索，并按类型与主题筛选。
  搜索和筛选状态保存在网址的 `#filter=` 部分，可以直接分享；每篇论文也有独立锚点。
- **Gallery**：研究视频及旅行记录，按内容分组。
- **CV**：经历、教育、项目、奖项等学术履历。

## 添加论文

在 `data/publications.json` 的 `publications` 数组中添加一条，例如：

```json
{
  "id": "sun-2027-prl-something",
  "type": "journal",
  "authors": ["Y. Sun", "F. Leo"],
  "title": "论文标题",
  "venue": "Phys. Rev. Lett.",
  "volume": null,
  "pages": null,
  "year": 2027,
  "doi": null,
  "arxiv": null,
  "book": null,
  "role": "first",
  "invited": false,
  "award": null,
  "presentation": null,
  "location": null,
  "topic": "cavity-solitons",
  "status": "accepted",
  "selected": false,
  "blurb": null
}
```

| 字段 | 说明 |
| --- | --- |
| `id` | 稳定、唯一的标识，供论文锚点和研究方向引用使用 |
| `type` | `journal`、`preprint`、`chapter` 或 `conference` |
| `doi` / `arxiv` | 只填标识符；没有时写 `null` |
| `book` | 章节所属的书名；其他类型写 `null` |
| `role` | `first`、`corresponding` 或 `co` |
| `topic` | `cavity-solitons`、`multimode-fiber`、`nanolasers`、`noise` 或 `other` |
| `status` | `published`、`accepted`、`preprint` 或 `upcoming` |
| `selected` | `true` 时进入精选论文列表，数量没有固定限制 |
| `blurb` | 精选论文必须填写一句简短的研究贡献说明 |
| `presentation` / `location` | 会议报告形式（`oral`、`poster`、`invited`）和地点 |
| `invited` / `award` | 是否受邀及奖项名称 |

作者列表中的 `Y. Sun` 会自动加粗；`Y. Sun*` 会显示通讯作者星号。
不要改变已有论文的 `id`，以免旧链接和研究方向引用失效。

## 添加图片与视频

媒体清单使用 `data/media.json`：

- `share`：首页及分享预览所用图片，包括 `src`、宽高、替代文字和说明。
- `figures`：研究图，包含稳定的 `id`、本地 `src`、宽高、标题、`alt`、图注和来源链接。
- `videos`：YouTube 视频，包含视频 `id`、标题、本地 `thumb`、原视频 `href` 和分组。
  分组为 `cavity`、`fiber` 或 `travel`。

先把图片存入 `assets/img/figures/`，视频封面存入 `assets/img/thumbs/`，
再将对应条目加入媒体清单。图片路径使用 `assets/img/...`。
要将媒体挂到某个研究方向，在 `data/research.json` 对应 strand 的 `figures` 或 `videos`
数组中添加它的 `id`；相关论文则放入 `pubs` 数组。

首页使用 `assets/img/banners/home.png` 中已有的孤子曲面图；它是静态图片。
目前五张研究图与 22 张视频封面也都从本站加载。仓库还保留了旧站导入的部分未使用 banner。
`tools/fetch_google_assets.py` 是旧 Google Sites 媒体的导入脚本，日常更新无需运行。

视频先显示本地封面，点击播放后才加载 `youtube-nocookie.com` 播放器。
相关逻辑在 `assets/js/video.js`。

## 字体与样式

当前排版采用 Google Fonts 的 **Roboto**，正常体和斜体均支持 100–900 可变字重，
拉丁字符子集以 WOFF2 文件保存在 `assets/fonts/`，通过 `fonts.css` 本地加载。
许可见 `assets/fonts/Roboto-OFL.txt`。Newsreader 和 IBM Plex Mono 文件及声明暂时保留，
当前页面排版不使用它们。

颜色、排版、间距和布局集中在 `assets/css/site.css` 中。
`tools/make_assets.py` 可离线生成 favicon 与旧版 `soliton-rule.svg`；
后者保留在仓库中，当前首页不使用。网页运行时无需进行物理模拟。

## 文件布局与检查

```text
data/                       网站内容
tools/build.py              页面与 feed、sitemap 生成器
tools/templates/base.html   共用 HTML 模板
tools/check.py              数据、引用、资源与生成结果检查
tools/make_assets.py        离线 SVG 生成工具
tools/fetch_google_assets.py 旧站媒体导入工具
assets/css/                 样式与字体声明
assets/js/                  主题切换、论文搜索筛选、视频播放
assets/fonts/               自托管字体与许可
assets/img/                 首页图、研究图、视频封面
index.html 等               生成结果，随源文件一起提交
```

`tools/check.py` 检查论文标识与 DOI、精选论文说明、研究与媒体引用、页面标题和描述、
资源文件、重复 HTML id、本页及跨页面锚点，以及 feed 和 sitemap 的 XML 格式。
字体检查以 `fonts.css` 实际引用的文件为准。

站点无需 npm 或前端框架。标题、描述、JSON-LD 和论文内容直接写入 HTML，
JavaScript 用于主题、搜索筛选及按需播放。`.nojekyll` 让 GitHub Pages 直接提供生成文件。

#!/usr/bin/env python3
"""HPPT 全集合订 -> 单个 PDF(每篇文章独立起页 + PDF 书签大纲 + 带页码目录)。

用法: python3 build_collection.py <repo_dir> <out.pdf> [title] [subtitle]

流程:
  1) 渲染一趟 -> 每个标题里埋隐藏锚点文本 -> 从 PDF 提取文本反查每个锚点落在第几页
  2) 用真实页码重渲染(目录带页码 + 每篇头部带本篇小节页码)
  3) 用 pypdf 写入 PDF 书签大纲(篇 -> 节, 四级)
"""
import html
import re
import sys
from pathlib import Path

import markdown

sys.path.insert(0, str(Path(__file__).parent))
from md2pdf import smart_quotes  # noqa: E402

CSS = """
@page { size: A4; margin: 20mm 19mm 18mm 19mm; }
* { box-sizing: border-box; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body {
  font-family: "Noto Serif CJK SC", serif;
  font-size: 10.8pt; line-height: 1.88; color: #1a1a1a;
  margin: 0; text-align: justify;
}
.cover {
  height: 297mm; width: 210mm; page-break-after: always;
  padding: 40mm 24mm 22mm 24mm; position: relative;
  background: #fbfbf9; box-sizing: border-box;
}
.cover .kicker { font-family: "Noto Sans CJK SC", sans-serif; font-size: 9.5pt;
  letter-spacing: .42em; color: #9a9a9a; margin-bottom: 30mm; }
.cover h1 { font-size: 30pt; line-height: 1.5; margin: 0 0 8mm 0; font-weight: 700; letter-spacing: .02em; }
.cover .sub { font-size: 11.5pt; color: #666; line-height: 1.85; margin: 0; max-width: 130mm; }
.cover .rule { width: 34mm; border-top: 2.5px solid #1a1a1a; margin: 12mm 0 9mm 0; }
.cover .meta { font-family: "Noto Sans CJK SC", sans-serif; font-size: 9pt; color: #8a8a8a;
  letter-spacing: .08em; margin-top: 14mm; }
.cover .meta span { margin-right: 16px; }
.cover .foot { position: absolute; left: 24mm; right: 24mm; bottom: 20mm;
  font-family: "Noto Sans CJK SC", sans-serif; font-size: 8.4pt; color: #b0b0b0; letter-spacing: .05em;
  border-top: 1px solid #e4e4e0; padding-top: 5mm; }

.toc { page-break-after: always; }
.toc h2 { font-size: 17pt; margin: 0 0 4mm 0; border: none; padding: 0 0 3mm 0;
  border-bottom: 2px solid #1a1a1a; break-after: auto; page-break-after: auto; }
.toc .hint { font-family: "Noto Sans CJK SC", sans-serif; font-size: 8.6pt; color: #aaa;
  letter-spacing: .04em; margin: 0 0 6mm 0; }
.toc table { width: 100%; border-collapse: collapse; font-size: 9.5pt;
  font-family: "Noto Sans CJK SC", sans-serif;
  page-break-before: auto; break-inside: auto; }
.toc td { padding: 1.9mm 1.2mm; border-bottom: 1px solid #ededea; vertical-align: top; }
.toc tr { break-inside: avoid; }
.toc td.n { width: 12mm; color: #999; font-variant-numeric: tabular-nums; }
.toc td.d { width: 23mm; color: #888; white-space: nowrap; }
.toc td.b { color: #444; line-height: 1.55; }
.toc td.p { width: 12mm; text-align: right; color: #999; font-variant-numeric: tabular-nums;
  white-space: nowrap; }

.article { page-break-before: always; }
.article-head { border-bottom: 1.5px solid #1a1a1a; padding-bottom: 4mm; margin-bottom: 6mm; }
.article-head .num { font-family: "Noto Sans CJK SC", sans-serif; font-size: 8.6pt;
  letter-spacing: .26em; color: #999; margin-bottom: 3mm; }
.article-head h2 { font-size: 19pt; line-height: 1.45; margin: 0 0 3.5mm 0; border: none; padding: 0; }
.article-head .brief { font-size: 10pt; color: #666; line-height: 1.75; margin: 0;
  padding-left: 3.5mm; border-left: 2px solid #d8d8d4; }
.article-head .date { font-family: "Noto Sans CJK SC", sans-serif; font-size: 8.6pt;
  color: #aaa; letter-spacing: .1em; margin-top: 3mm; }
.article-head .outline { margin-top: 4mm; font-family: "Noto Sans CJK SC", sans-serif;
  font-size: 8.8pt; color: #7a7a7a; line-height: 1.8; }
.article-head .outline b { color: #444; font-weight: 600; }
.article-head .outline .p { color: #bbb; }

.anchor { color: transparent; font-size: 1pt; line-height: 1; letter-spacing: 0; }

h1 { font-size: 15pt; margin: 8mm 0 4mm 0; break-after: avoid; }
h2 { font-size: 13.5pt; font-weight: 700; margin: 8mm 0 3.5mm 0; padding-bottom: 1.8mm;
     border-bottom: 1px solid #dcdcd8; break-after: avoid; page-break-after: avoid; }
h3 { font-size: 11.6pt; font-weight: 700; margin: 6mm 0 2.5mm 0; color: #333;
     break-after: avoid; page-break-after: avoid; }
p { margin: 0 0 3.2mm 0; }
strong { font-weight: 700; color: #000; }
blockquote { margin: 4.5mm 0; padding: 3.2mm 5.5mm; border-left: 3px solid #b8b8b4;
  background: #f8f8f5; color: #333; break-inside: avoid; }
blockquote p { margin: 0; }
ol, ul { margin: 0 0 3.4mm 0; padding-left: 6.5mm; }
li { margin-bottom: 1.4mm; }
hr { border: none; border-top: 1px solid #e6e6e2; margin: 6mm 0; }
table { width: 100%; border-collapse: collapse; font-size: 9.6pt; margin: 3.5mm 0;
  font-family: "Noto Sans CJK SC", sans-serif; break-inside: avoid; }
th, td { border: 1px solid #d8d8d4; padding: 2mm 2.5mm; text-align: left; }
th { background: #f4f4f1; font-weight: 700; }
code { font-family: "Noto Sans Mono CJK SC", monospace; font-size: 9.6pt;
  background: #f2f2f0; padding: .4mm 1.2mm; border-radius: 2px; }
pre { background: #f6f6f4; padding: 4mm; overflow-x: auto; font-size: 9.6pt; }
pre code { background: none; padding: 0; }
img { max-width: 100%; margin: 3mm auto; display: block; }
"""


# ---------------------------------------------------------------- 解析索引
def parse_index(repo: Path):
    rows = []
    for line in (repo / "README.md").read_text(encoding="utf-8").split("\n"):
        m = re.match(
            r"^\|\s*(\d{3})\s*\|\s*([\d-]+)\s*\|\s*([^|]*?)\s*\|\s*\[([^\]]+)\]\(([^)]+)\)\s*\|",
            line,
        )
        if m:
            rows.append(
                {
                    "no": int(m.group(1)),
                    "date": m.group(2),
                    "brief": m.group(3),
                    "path": m.group(5),
                }
            )
    rows.sort(key=lambda r: r["no"])
    return rows


def strip_tags(s: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


# ---------------------------------------------------------------- 单篇
def parse_article(repo: Path, row, counter):
    """返回 dict: title, body_html(含锚点), headings=[(level, text, anchor_id)]"""
    src = repo / row["path"]
    raw = src.read_text(encoding="utf-8")
    title = ""
    m = re.search(r"^#\s+(.+)$", raw, re.M)
    if m:
        title = m.group(1).strip()
    md = smart_quotes(raw)
    md = re.sub(r"^\s*#\s+.+$", "", md, count=1, flags=re.M)

    def fix_img(mm):
        p = (src.parent / mm.group(2)).resolve()
        return "![%s](%s)" % (mm.group(1), p.as_uri())

    md = re.sub(r"!\[(.*?)\]\((.*?)\)", fix_img, md)
    body = markdown.markdown(md, extensions=["extra", "sane_lists"], output_format="html5")
    body = re.sub(r"^\s*<hr\s*/?>\s*$", "", body, flags=re.M)

    headings = []

    def add_anchor(mm):
        tag = mm.group(1)
        inner = mm.group(2)
        lvl = 2 if tag == "h2" else 3
        txt = strip_tags(inner)
        if not txt:
            return mm.group(0)
        counter[0] += 1
        aid = "@@H%05d@@" % counter[0]
        headings.append((lvl, txt, aid))
        return "<%s>%s<span class='anchor'>%s</span></%s>" % (tag, inner, aid, tag)

    body = re.sub(r"<(h2|h3)>(.*?)</\1>", add_anchor, body, flags=re.S)

    article_anchor = "@@A%03d@@" % row["no"]
    return {
        "title": title,
        "body": body,
        "headings": headings,
        "anchor": article_anchor,
    }


# ---------------------------------------------------------------- 渲染
def render(page_html: str, out: Path, title: str):
    from playwright.sync_api import sync_playwright

    html_path = Path("/root/.hermes/cache/scratch/collection.html")
    html_path.write_text(page_html, encoding="utf-8")
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--font-render-hinting=none"])
        pg = b.new_page()
        pg.goto(html_path.as_uri(), wait_until="load")
        pg.emulate_media(media="print")
        pg.pdf(
            path=str(out),
            format="A4",
            print_background=True,
            display_header_footer=True,
            header_template="<div></div>",
            footer_template=(
                '<div style="width:100%;font-size:7.6pt;color:#aaa;'
                "font-family:Noto Sans CJK SC,sans-serif;padding:0 19mm;"
                "display:flex;justify-content:space-between;\">"
                "<span>" + html.escape(title) + "</span>"
                '<span class="pageNumber"></span></div>'
            ),
            margin={"top": "18mm", "bottom": "15mm", "left": "19mm", "right": "19mm"},
        )
        b.close()


def anchor_pages(pdf: Path):
    """返回 {anchor_id: 1-based page}"""
    from pypdf import PdfReader

    reader = PdfReader(str(pdf))
    found = {}
    pat = re.compile(r"@@[AH]\d+@@")
    for i, pg in enumerate(reader.pages, 1):
        t = (pg.extract_text() or "").replace(" ", "").replace("\n", "")
        for m in pat.finditer(t):
            found.setdefault(m.group(0), i)
    return found


def write_outline(pdf: Path, out: Path, title: str, entries):
    """entries: [(level, text, page1based)]"""
    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(str(pdf))
    writer = PdfWriter()
    writer.append_pages_from_reader(reader)
    writer.add_metadata({"/Title": title, "/Producer": "his-pol-phy-think collection builder"})
    stack = {}
    for lvl, text, page in entries:
        if page is None:
            continue
        idx = page - 1
        if idx < 0 or idx >= len(writer.pages):
            continue
        if lvl == 1:
            root = writer.add_outline_item(text, idx, bold=True)
            stack = {1: root}
        else:
            parent = stack.get(lvl - 1)
            item = writer.add_outline_item(text, idx, parent=parent)
            stack[lvl] = item
    with open(out, "wb") as f:
        writer.write(f)


# ---------------------------------------------------------------- 主流程
def build(repo: Path, out: Path, title: str, subtitle: str):
    rows = parse_index(repo)
    if not rows:
        raise SystemExit("README 里没解析到条目")

    counter = [0]
    arts = []
    for r in rows:
        a = parse_article(repo, r, counter)
        a["row"] = r
        arts.append(a)

    def compose(art_pages, sub_pages):
        toc_rows = []
        for a in arts:
            r = a["row"]
            pg = art_pages.get(r["no"], "")
            toc_rows.append(
                "<tr><td class='n'>%03d</td><td class='d'>%s</td>"
                "<td class='b'>%s</td><td class='p'>%s</td></tr>"
                % (r["no"], r["date"], html.escape(r["brief"]), pg)
            )
        blocks = []
        for a in arts:
            r = a["row"]
            items = []
            for lvl, htxt, aid in a["headings"]:
                pg = sub_pages.get(aid, "")
                items.append(
                    "<div>%s <span class='p'>%s</span></div>"
                    % (html.escape(htxt), ("P%s" % pg) if pg else "")
                )
            ol = (
                '<div class="outline"><b>本篇目录</b><br>%s</div>' % "".join(items)
                if items
                else ""
            )
            blocks.append(
                """
<div class="article">
  <div class="article-head">
    <div class="num">NO. %03d<span class='anchor'>%s</span></div>
    <h2>%s</h2>
    <div class="brief">%s</div>
    <div class="date">%s · %s</div>
    %s
  </div>
  %s
</div>"""
                % (
                    r["no"],
                    a["anchor"],
                    html.escape(a["title"] or r["brief"]),
                    html.escape(r["brief"]),
                    r["date"],
                    html.escape(r["path"]),
                    ol,
                    a["body"],
                )
            )
        span = "%s — %s" % (rows[0]["date"], rows[-1]["date"])
        return """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>%s</title><style>%s</style></head><body>
  <div class="cover">
    <div class="kicker">历史 · 政治 · 哲学思辨</div>
    <h1>%s</h1>
    <div class="rule"></div>
    <p class="sub">%s</p>
    <div class="meta">
      <span>%d 篇</span><span>%s</span><span>his-pol-phy-think</span>
    </div>
    <div class="foot">每篇文章独立起页 · 编号 001–%03d 与 README 索引一致</div>
  </div>
  <div class="toc">
    <h2>内容索引</h2>
    <p class="hint">PDF 左侧大纲栏可按篇 / 节跳转 · 页码为 PDF 页码</p>
    <table>%s</table>
  </div>
  %s
</body></html>""" % (
            html.escape(title),
            CSS,
            html.escape(title),
            html.escape(subtitle),
            len(rows),
            span,
            len(rows),
            "".join(toc_rows),
            "\n".join(blocks),
        )

    tmp = Path("/root/.hermes/cache/scratch/collection-pass1.pdf")

    # pass 1: 抓锚点页码
    render(compose({}, {}), tmp, title)
    pmap = anchor_pages(tmp)
    art_pages = {a["row"]["no"]: pmap.get(a["anchor"]) for a in arts}
    sub_pages = {aid: pmap.get(aid) for a in arts for _l, _t, aid in a["headings"]}
    missing = [a["anchor"] for a in arts if not art_pages.get(a["row"]["no"])]
    if missing:
        print("WARN 未定位到文章锚点: %s" % missing)

    # pass 2: 填页码后重渲染(页数可能变) -> 重新抓
    render(compose(art_pages, sub_pages), tmp, title)
    pmap2 = anchor_pages(tmp)
    art2 = {a["row"]["no"]: pmap2.get(a["anchor"]) for a in arts}
    sub2 = {aid: pmap2.get(aid) for a in arts for _l, _t, aid in a["headings"]}
    if art2 != art_pages:
        print("WARN 页码漂移, 采用第二轮")
        art_pages, sub_pages = art2, sub2

    # pass 3: 最终渲染
    render(compose(art_pages, sub_pages), tmp, title)
    pmap3 = anchor_pages(tmp)
    art3 = {a["row"]["no"]: pmap3.get(a["anchor"]) for a in arts}
    sub3 = {aid: pmap3.get(aid) for a in arts for _l, _t, aid in a["headings"]}
    if art3 != art_pages:
        print("WARN 页码二次漂移, 采用第三轮")
        art_pages, sub_pages = art3, sub3

    # 写书签
    entries = [(1, title, 1)]
    for a in arts:
        r = a["row"]
        entries.append(
            (2, "NO.%03d %s" % (r["no"], a["title"] or r["brief"]), art_pages.get(r["no"]))
        )
        for lvl, htxt, aid in a["headings"]:
            entries.append((3 if lvl == 2 else 4, htxt, sub_pages.get(aid)))
    write_outline(tmp, out, title, entries)

    print(
        "OK %s  articles=%d  outline_entries=%d  pages=%d"
        % (out, len(rows), len(entries), len(PdfPages(out)))
    )


def PdfPages(pdf: Path):
    from pypdf import PdfReader

    return PdfReader(str(pdf)).pages


if __name__ == "__main__":
    repo = Path(sys.argv[1])
    out = Path(sys.argv[2])
    title = sys.argv[3] if len(sys.argv) > 3 else "历史·政治·哲学思辨对话集"
    subtitle = sys.argv[4] if len(sys.argv) > 4 else "合订本"
    build(repo, out, title, subtitle)

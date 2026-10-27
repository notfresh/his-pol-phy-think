#!/usr/bin/env python3
"""HPPT 全集合订 -> 单个 PDF(每篇文章独立起页)。

用法: python3 build_collection.py <repo_dir> <out.pdf> [title] [subtitle]
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
.toc h2 { font-size: 17pt; margin: 0 0 8mm 0; border: none; padding: 0 0 3mm 0;
  border-bottom: 2px solid #1a1a1a; }
.toc table { width: 100%; border-collapse: collapse; font-size: 9.6pt;
  font-family: "Noto Sans CJK SC", sans-serif; }
.toc td { padding: 2.1mm 1.5mm; border-bottom: 1px solid #ededea; vertical-align: top; }
.toc td.n { width: 13mm; color: #999; font-variant-numeric: tabular-nums; }
.toc td.d { width: 24mm; color: #888; white-space: nowrap; }
.toc td.b { color: #444; line-height: 1.6; }

.article { page-break-before: always; }
.article-head { border-bottom: 1.5px solid #1a1a1a; padding-bottom: 4mm; margin-bottom: 7mm; }
.article-head .num { font-family: "Noto Sans CJK SC", sans-serif; font-size: 8.6pt;
  letter-spacing: .26em; color: #999; margin-bottom: 3mm; }
.article-head h2 { font-size: 19pt; line-height: 1.45; margin: 0 0 3.5mm 0; border: none; padding: 0; }
.article-head .brief { font-size: 10pt; color: #666; line-height: 1.75; margin: 0;
  padding-left: 3.5mm; border-left: 2px solid #d8d8d4; }
.article-head .date { font-family: "Noto Sans CJK SC", sans-serif; font-size: 8.6pt;
  color: #aaa; letter-spacing: .1em; margin-top: 3mm; }

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


def article_html(repo: Path, row):
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
    head_title = html.escape(title or row["brief"])
    brief = html.escape(row["brief"])
    return """
<div class="article">
  <div class="article-head">
    <div class="num">NO. %03d</div>
    <h2>%s</h2>
    <div class="brief">%s</div>
    <div class="date">%s · %s</div>
  </div>
  %s
</div>""" % (
        row["no"],
        head_title,
        brief,
        row["date"],
        html.escape(row["path"]),
        body,
    )


def build(repo: Path, out: Path, title: str, subtitle: str):
    rows = parse_index(repo)
    if not rows:
        raise SystemExit("README 里没解析到条目")

    toc_rows = "".join(
        "<tr><td class='n'>%03d</td><td class='d'>%s</td><td class='b'>%s</td></tr>"
        % (r["no"], r["date"], html.escape(r["brief"]))
        for r in rows
    )
    arts = "\n".join(article_html(repo, r) for r in rows)
    span = "%s — %s" % (rows[0]["date"], rows[-1]["date"])

    page = """<!DOCTYPE html>
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
        toc_rows,
        arts,
    )

    html_path = Path("/root/.hermes/cache/scratch/collection.html")
    html_path.write_text(page, encoding="utf-8")

    from playwright.sync_api import sync_playwright

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
    print("OK %s  articles=%d" % (out, len(rows)))


if __name__ == "__main__":
    repo = Path(sys.argv[1])
    out = Path(sys.argv[2])
    title = sys.argv[3] if len(sys.argv) > 3 else "历史·政治·哲学思辨对话集"
    subtitle = sys.argv[4] if len(sys.argv) > 4 else "合订本"
    build(repo, out, title, subtitle)

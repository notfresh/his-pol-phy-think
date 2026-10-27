#!/usr/bin/env python3
"""Markdown -> A4 PDF (中文排版) via Chromium/Playwright.

用法: python3 md2pdf.py <input.md> <output.pdf> [--subtitle "..."] [--date YYYY-MM-DD]
"""
import argparse
import html
import re
import sys
from pathlib import Path

import markdown

CSS = """
@page { size: A4; margin: 22mm 20mm 20mm 20mm; }
* { box-sizing: border-box; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body {
  font-family: "Noto Serif CJK SC", "Source Han Serif SC", "Songti SC", serif;
  font-size: 11.2pt;
  line-height: 1.9;
  color: #1a1a1a;
  margin: 0;
  text-align: justify;
  hyphens: none;
}
.cover { padding: 26mm 0 12mm 0; border-bottom: 2px solid #1a1a1a; margin-bottom: 12mm; }
.kicker { font-family: "Noto Sans CJK SC", sans-serif; font-size: 9pt; letter-spacing: .32em;
          color: #8a8a8a; text-transform: uppercase; margin-bottom: 7mm; }
h1.title { font-size: 23pt; line-height: 1.42; margin: 0 0 6mm 0; font-weight: 700;
           letter-spacing: .01em; }
.subtitle { font-size: 11pt; color: #555; line-height: 1.75; margin: 0 0 7mm 0; }
.meta { font-family: "Noto Sans CJK SC", sans-serif; font-size: 9pt; color: #9a9a9a; letter-spacing: .06em; }
.meta span { margin-right: 14px; }
h2 {
  font-size: 14.5pt; font-weight: 700; margin: 11mm 0 4mm 0; padding-bottom: 2mm;
  border-bottom: 1px solid #d8d8d8; break-after: avoid; page-break-after: avoid;
  letter-spacing: .01em;
}
h3 { font-size: 12pt; font-weight: 700; margin: 7mm 0 2.5mm 0; color: #333;
     break-after: avoid; page-break-after: avoid; }
p { margin: 0 0 3.4mm 0; }
strong { font-weight: 700; color: #000; }
blockquote {
  margin: 5mm 0; padding: 3.5mm 6mm; border-left: 3px solid #b0b0b0;
  background: #f7f7f5; color: #333; font-size: 11.4pt; break-inside: avoid;
}
blockquote p { margin: 0; }
ol, ul { margin: 0 0 3.6mm 0; padding-left: 7mm; }
li { margin-bottom: 1.6mm; }
hr { border: none; border-top: 1px solid #e2e2e2; margin: 8mm 0; }
code { font-family: "Noto Sans Mono CJK SC", monospace; font-size: 10pt;
       background: #f2f2f0; padding: .4mm 1.2mm; border-radius: 2px; }
pre { background: #f6f6f4; padding: 4mm; overflow-x: auto; font-size: 10pt; }
pre code { background: none; padding: 0; }
blockquote strong { color: #000; }
.tail { margin-top: 12mm; padding-top: 5mm; border-top: 1px solid #ddd;
        font-family: "Noto Sans CJK SC", sans-serif; font-size: 8.6pt; color: #aaa;
        letter-spacing: .04em; }
"""


def smart_quotes(md: str) -> str:
    out = []
    for line in md.split("\n"):
        if '"' not in line:
            out.append(line)
            continue
        buf = []
        open_q = True
        for ch in line:
            if ch == '"':
                buf.append("\u201c" if open_q else "\u201d")
                open_q = not open_q
            else:
                buf.append(ch)
        out.append("".join(buf))
    return "\n".join(out)


def build_html(md_text: str, title: str, subtitle: str, date: str, tail: str) -> str:
    # 直引号 -> 中文弯引号（仅渲染层，.md 源文件保持仓库统一风格）
    md_text = smart_quotes(md_text)
    body = markdown.markdown(
        md_text,
        extensions=["extra", "sane_lists", "smarty"],
        output_format="html5",
    )
    # 首行 h1 作为封面标题，正文里去掉
    body = re.sub(r"^\s*<h1[^>]*>.*?</h1>\s*", "", body, count=1, flags=re.S)
    # 引文块里的强调块做深色
    body = body.replace("<blockquote>", '<blockquote class="pull">')
    meta = "".join(f"<span>{html.escape(x)}</span>" for x in (date,) if x)
    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>{html.escape(title)}</title><style>{CSS}</style></head>
<body>
  <div class="cover">
    <div class="kicker">历史 · 政治 · 哲学思辨</div>
    <h1 class="title">{html.escape(title)}</h1>
    {f'<p class="subtitle">{html.escape(subtitle)}</p>' if subtitle else ''}
    <div class="meta">{meta}</div>
  </div>
  {body}
  <div class="tail">{html.escape(tail)}</div>
</body></html>"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--subtitle", default="")
    ap.add_argument("--date", default="")
    ap.add_argument("--tail", default="")
    a = ap.parse_args()

    src = Path(a.src)
    md_text = src.read_text(encoding="utf-8")
    title = re.search(r"^#\s+(.+)$", md_text, re.M).group(1).strip()
    page = build_html(md_text, title, a.subtitle, a.date, a.tail)

    html_path = Path("/root/.hermes/cache/scratch") / (src.stem + ".html")
    html_path.write_text(page, encoding="utf-8")

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        b = p.chromium.launch(args=["--font-render-hinting=none"])
        pg = b.new_page()
        pg.goto(html_path.as_uri(), wait_until="load")
        pg.emulate_media(media="print")
        pg.pdf(
            path=a.dst,
            format="A4",
            print_background=True,
            display_header_footer=True,
            header_template="<div></div>",
            footer_template=(
                '<div style="width:100%;font-size:8pt;color:#aaa;font-family:Noto Sans CJK SC,sans-serif;'
                'padding:0 20mm;display:flex;justify-content:space-between;">'
                f'<span>{html.escape(title)}</span>'
                '<span class="pageNumber"></span></div>'
            ),
            margin={"top": "18mm", "bottom": "16mm", "left": "20mm", "right": "20mm"},
        )
        b.close()
    print(f"OK {a.dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

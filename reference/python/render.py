#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MMP-AIR v0.1 reference renderer.

Read an MMP-AIR JSON record and emit the disclosure document required by
the contest rules, plus the declaration sentence to put inside the paper.

The default output file name follows the CUMCM 2026 regulation
(Article 4: file name "AI工具使用详情.pdf").  Use --filename to override.

Usage:
    python render.py record.json
    python render.py record.json -o out/ --filename "AI工具使用详情.pdf"
    python render.py record.json --write-hash      # write hash back into the record

Dependencies:
    pip install reportlab
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.platypus import (
        KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
    )
except ImportError:  # pragma: no cover
    sys.exit("reportlab is required: pip install reportlab")

# ---------------------------------------------------------------- constants

CJK_FONT = "STSong-Light"
DEFAULT_FILENAME = "AI\u5de5\u5177\u4f7f\u7528\u8be6\u60c5.pdf"  # AI工具使用详情.pdf

PURPOSE_LABEL = {
    "literature": "文献检索", "ideation": "思路构思", "modeling": "模型构建",
    "data": "数据处理", "coding": "代码编写", "debugging": "调试纠错",
    "visualization": "图表绘制", "writing": "正文撰写", "polishing": "语言润色",
    "translation": "翻译", "review": "审校挑错",
}
ADOPTED_LABEL = {"full": "全部采纳", "modified": "采纳并修改", "none": "未采纳"}
ROLE_LABEL = {"user": "输入", "assistant": "输出", "note": "批注"}

DECL_NOT_USED = "本参赛队在竞赛过程中未使用任何AI工具。"
DECL_USED = (
    "本参赛队在竞赛过程中使用了AI工具，主要用于【{s}】，详细使用情况见支撑材料。"
)


# ---------------------------------------------------------------- helpers

def register_cjk() -> None:
    """Register a CID font so Chinese renders without embedding a TTF."""
    try:
        pdfmetrics.registerFont(UnicodeCIDFont(CJK_FONT))
    except Exception as exc:  # pragma: no cover
        sys.exit(f"cannot register CJK font {CJK_FONT}: {exc}")


def canonical_hash(payload: dict) -> str:
    """Hash of the record with integrity.hash removed, keys sorted."""
    clone = json.loads(json.dumps(payload, ensure_ascii=False))
    if isinstance(clone.get("integrity"), dict):
        clone["integrity"].pop("hash", None)
    blob = json.dumps(clone, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(blob.encode("utf-8")).hexdigest()


def declaration_sentence(payload: dict) -> str:
    decl = payload.get("declaration", {})
    if decl.get("used"):
        summary = (decl.get("summary_zh") or "").strip()
        # the regulation template already reads "主要用于【...】",
        # so drop a duplicated "主要用于" / "用于" prefix
        for prefix in ("主要用于", "用于"):
            if summary.startswith(prefix):
                summary = summary[len(prefix):].lstrip("，, ")
                break
        if not summary:
            summary = "详见支撑材料"
        return DECL_USED.format(s=summary)
    return DECL_NOT_USED


def validate(payload: dict) -> list[str]:
    """Minimal checks. Returns a list of problems (empty means OK)."""
    problems: list[str] = []
    if payload.get("spec") != "MMP-AIR":
        problems.append("spec must be \"MMP-AIR\"")
    if payload.get("version") != "0.1":
        problems.append("version must be \"0.1\"")
    decl = payload.get("declaration")
    if not isinstance(decl, dict) or "used" not in decl:
        problems.append("declaration.used is required")
        return problems

    if not decl["used"]:
        if payload.get("tools"):
            problems.append("declaration.used is false but tools is not empty")
        if payload.get("records"):
            problems.append("declaration.used is false but records is not empty")
        return problems

    tools = payload.get("tools") or []
    records = payload.get("records") or []
    if not tools:
        problems.append("tools is required when AI was used")
    if not records:
        problems.append("records is required when AI was used")

    ids = {t.get("id") for t in tools}
    for t in tools:
        for key in ("id", "name", "model"):
            if not t.get(key):
                problems.append(f"tools[].{key} is required (id={t.get('id')})")
    for r in records:
        rid = r.get("id", "<no id>")
        for key in ("purpose", "stage", "purpose_detail_zh", "prompt_approach_zh"):
            if not r.get(key):
                problems.append(f"records[{rid}].{key} is required")
        if r.get("purpose") not in PURPOSE_LABEL:
            problems.append(f"records[{rid}].purpose is not a known value")
        for ref in r.get("tool_refs") or []:
            if ref not in ids:
                problems.append(f"records[{rid}] references unknown tool {ref}")
        outcome = r.get("outcome") or {}
        if outcome.get("adopted") not in ADOPTED_LABEL:
            problems.append(f"records[{rid}].outcome.adopted is required")
        if outcome.get("adopted") == "modified" and not outcome.get("modification_zh"):
            problems.append(f"records[{rid}].outcome.modification_zh is required when modified")
        ver = outcome.get("verification")
        if r.get("purpose") == "polishing":
            continue  # 语言润色豁免核验
        if not ver or "verified" not in ver:
            problems.append(f"records[{rid}].outcome.verification.verified is required")
        elif not ver.get("method_zh"):
            problems.append(f"records[{rid}].outcome.verification.method_zh is required")
    return problems


# ---------------------------------------------------------------- styles

def make_styles():
    base = dict(fontName=CJK_FONT, fontSize=10.5, leading=15, alignment=TA_LEFT,
                textColor=colors.HexColor("#1a1a1a"))
    return {
        "title": ParagraphStyle("title", **{**base, "fontSize": 16, "leading": 22,
                                            "spaceAfter": 4}),
        "sub": ParagraphStyle("sub", **{**base, "fontSize": 9, "leading": 13,
                                        "textColor": colors.HexColor("#666666")}),
        "h": ParagraphStyle("h", **{**base, "fontSize": 12, "leading": 17,
                                    "spaceBefore": 12, "spaceAfter": 5,
                                    "textColor": colors.HexColor("#0b3d91")}),
        "body": ParagraphStyle("body", **base),
        "small": ParagraphStyle("small", **{**base, "fontSize": 8.5, "leading": 12,
                                            "textColor": colors.HexColor("#555555")}),
        "cell": ParagraphStyle("cell", **{**base, "fontSize": 9.5, "leading": 13.5}),
        "cellh": ParagraphStyle("cellh", **{**base, "fontSize": 9.5, "leading": 13.5,
                                            "textColor": colors.white}),
        "mono": ParagraphStyle("mono", fontName="Courier", fontSize=7.5, leading=10,
                               textColor=colors.HexColor("#333333")),
    }


def cell(text: str, st) -> Paragraph:
    esc = (str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
           .replace("\n", "<br/>"))
    return Paragraph(esc, st)


def table(rows, widths, st) -> Table:
    t = Table(rows, colWidths=widths, repeatRows=1, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0b3d91")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#b9c4d6")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f6fa")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


# ---------------------------------------------------------------- build

def build(payload: dict, digest: str, out_path: Path) -> None:
    st = make_styles()
    W = A4[0] - 36 * mm
    story: list = []

    sub = payload.get("submission") or {}
    head = "AI\u5de5\u5177\u4f7f\u7528\u8be6\u60c5"  # AI工具使用详情
    story.append(Paragraph(head, st["title"]))
    meta = "  |  ".join(x for x in [
        str(sub.get("contest") or ""),
        str(sub.get("year") or ""),
        ("\u9898\u76ee " + sub["problem"]) if sub.get("problem") else "",  # 题目
        ("\u961f\u53f7 " + sub["team_ref"]) if sub.get("team_ref") else "",  # 队号
    ] if x)
    if meta:
        story.append(Paragraph(meta, st["sub"]))
    story.append(Spacer(1, 6))

    # 论文内声明
    story.append(Paragraph(
        "\u4e00\u3001\u8bba\u6587\u5185\u58f0\u660e\uff08\u7f6e\u4e8e\u53c2\u8003\u6587\u732e\u4e4b\u524d\uff09",
        st["h"]))  # 一、论文内声明（置于参考文献之前）
    story.append(Table(
        [[cell(declaration_sentence(payload), st["cell"])]],
        colWidths=[W], hAlign="LEFT",
        style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f4f6fa")),
            ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#b9c4d6")),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ])))

    if not payload.get("declaration", {}).get("used"):
        story.append(Spacer(1, 10))
        story.append(Paragraph(
            "\u672c\u53c2\u8d5b\u961f\u672a\u4f7f\u7528\u4efb\u4f55 AI \u5de5\u5177\uff0c"
            "\u65e0\u9700\u5448\u73b0\u540e\u7eed\u5185\u5bb9\u3002", st["body"]))
        finish(story, payload, digest, st, W, out_path)
        return

    # 二、工具清单
    story.append(Paragraph("\u4e8c\u3001AI \u5de5\u5177\u6e05\u5355", st["h"]))  # 二、AI工具清单
    rows = [[cell(x, st["cellh"]) for x in
             ["\u7f16\u53f7", "\u5de5\u5177\u540d\u79f0", "\u7248\u672c\u6216\u578b\u53f7",
              "\u5f00\u53d1\u673a\u6784", "\u4f7f\u7528\u65e5\u671f"]]]
    for t in payload["tools"]:
        rows.append([cell(t.get("id", ""), st["cell"]),
                     cell(t.get("name", ""), st["cell"]),
                     cell(t.get("model", "") + (f" ({t['version']})" if t.get("version") else ""),
                          st["cell"]),
                     cell(t.get("vendor", "-"), st["cell"]),
                     cell(t.get("access_date", "-"), st["cell"])])
    story.append(table(rows, [16 * mm, 34 * mm, 42 * mm, W - 118 * mm, 26 * mm], st))

    # 三、使用目的与环节
    story.append(Paragraph("\u4e09\u3001\u4f7f\u7528\u76ee\u7684\u4e0e\u73af\u8282", st["h"]))
    rows = [[cell(x, st["cellh"]) for x in
             ["\u7f16\u53f7", "\u4f7f\u7528\u73af\u8282", "\u76ee\u7684", "\u5177\u4f53\u8bf4\u660e"]]]
    for r in payload["records"]:
        rows.append([cell(r.get("id", ""), st["cell"]),
                     cell(r.get("stage", ""), st["cell"]),
                     cell(PURPOSE_LABEL.get(r.get("purpose"), r.get("purpose", "")), st["cell"]),
                     cell(r.get("purpose_detail_zh", ""), st["cell"])])
    story.append(table(rows, [16 * mm, 40 * mm, 22 * mm, W - 78 * mm], st))

    # 四、提示方式与使用过程
    story.append(Paragraph(
        "\u56db\u3001\u4e3b\u8981\u63d0\u793a\u65b9\u5f0f\u4e0e\u4f7f\u7528\u8fc7\u7a0b"
        "\uff08\u542b\u5178\u578b\u4ea4\u4e92\u793a\u4f8b\uff09", st["h"]))
    for r in payload["records"]:
        block = [Paragraph(
            f"<b>{r.get('id', '')}</b> \u00b7 {r.get('stage', '')}", st["body"])]
        block.append(Paragraph(r.get("prompt_approach_zh", ""), st["body"]))
        for it in r.get("interactions") or []:
            label = ROLE_LABEL.get(it.get("role"), it.get("role", ""))
            ts = f" <font color='#888888'>[{it['ts']}]</font>" if it.get("ts") else ""
            block.append(Paragraph(
                f"&nbsp;&nbsp;<font color='#0b3d91'>[{label}]</font>{ts} "
                + str(it.get("content", "")), st["small"]))
        block.append(Spacer(1, 5))
        story.append(KeepTogether(block))

    # 五、采纳、修改与核验
    story.append(PageBreak())
    story.append(Paragraph(
        "\u4e94\u3001AI \u8f93\u51fa\u7684\u91c7\u7eb3\u3001\u4eba\u5de5\u4fee\u6539\u4e0e\u6838\u9a8c\u60c5\u51b5",
        st["h"]))
    rows = [[cell(x, st["cellh"]) for x in
             ["\u7f16\u53f7", "\u91c7\u7eb3", "\u4eba\u5de5\u4fee\u6539",
              "\u6838\u9a8c\u65b9\u5f0f", "\u5df2\u6838\u9a8c"]]]
    for r in payload["records"]:
        o = r.get("outcome") or {}
        v = o.get("verification") or {}
        if r.get("purpose") == "polishing":
            rows.append([cell(r.get("id", ""), st["cell"]),
                         cell(ADOPTED_LABEL.get(o.get("adopted"), ""), st["cell"]),
                         cell(o.get("modification_zh", "-"), st["cell"]),
                         cell("\u8bed\u8a00\u6da6\u8272\u514d\u6838\u9a8c", st["cell"]),
                         cell("-", st["cell"])])
            continue
        rows.append([cell(r.get("id", ""), st["cell"]),
                     cell(ADOPTED_LABEL.get(o.get("adopted"), ""), st["cell"]),
                     cell(o.get("modification_zh", "-"), st["cell"]),
                     cell(v.get("method_zh", "-"), st["cell"]),
                     cell("\u662f" if v.get("verified") else "\u5426", st["cell"])])
    story.append(table(rows, [16 * mm, 24 * mm, W - 128 * mm, 62 * mm, 26 * mm], st))
    story.append(Paragraph(
        "\u6838\u9a8c\u4eba\uff1a"
        + "、".join(sorted({(r.get("outcome") or {}).get("verification", {}).get("verifier_role")
                          for r in payload["records"]
                          if (r.get("outcome") or {}).get("verification", {})
                          .get("verifier_role")})) or "-",
        st["small"]))

    finish(story, payload, digest, st, W, out_path)


def finish(story, payload, digest, st, W, out_path) -> None:
    story.append(Spacer(1, 14))
    story.append(Paragraph("\u9644\u5f55\uff1a\u673a\u5668\u53ef\u8bfb\u8bb0\u5f55", st["h"]))
    story.append(Paragraph(
        "\u672c\u6587\u4ef6\u7531 MMP-AIR v0.1 \u8bb0\u5f55\u751f\u6210\u3002"
        "\u8bb0\u5f55\u6587\u4ef6\u53ef\u88ab\u4efb\u4f55\u652f\u6301\u8be5\u89c4\u8303\u7684"
        "\u5de5\u5177\u89e3\u6790\u4e0e\u6838\u5bf9\u3002", st["small"]))
    gen = (payload.get("integrity") or {}).get("generator") or {}
    story.append(Paragraph(
        "\u751f\u6210\u5de5\u5177\uff1a" + (gen.get("name", "-"))
        + (" " + gen["version"] if gen.get("version") else ""), st["small"]))
    # keep CJK out of the Courier style: Courier cannot render Chinese
    story.append(Paragraph("\u8bb0\u5f55\u6458\u8981\uff1a", st["small"]))
    story.append(Paragraph(digest, st["mono"]))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    SimpleDocTemplate(
        str(out_path), pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=16 * mm, bottomMargin=16 * mm,
        title="AI\u5de5\u5177\u4f7f\u7528\u8be6\u60c5", author="MMP-AIR v0.1",
    ).build(story)


# ---------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser(description="Render an MMP-AIR v0.1 record to PDF.")
    ap.add_argument("record", type=Path, help="path to the MMP-AIR JSON file")
    ap.add_argument("-o", "--out", type=Path, default=Path("."), help="output directory")
    ap.add_argument("--filename", default=DEFAULT_FILENAME, help="output file name")
    ap.add_argument("--write-hash", action="store_true",
                    help="write the computed hash back into the record file")
    ap.add_argument("--strict", action="store_true",
                    help="exit non-zero instead of rendering when problems are found")
    args = ap.parse_args()

    if not args.record.exists():
        sys.exit(f"record not found: {args.record}")

    payload = json.loads(args.record.read_text(encoding="utf-8"))
    problems = validate(payload)
    if problems:
        print("validation problems:", file=sys.stderr)
        for p in problems:
            print("  - " + p, file=sys.stderr)
        if args.strict:
            return 2

    digest = canonical_hash(payload)
    if args.write_hash:
        payload.setdefault("integrity", {})
        payload["integrity"]["hash"] = digest
        args.record.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    register_cjk()
    out_path = args.out / args.filename
    build(payload, digest, out_path)

    print("declaration (put this in the paper, before the references):")
    print("  " + declaration_sentence(payload))
    print(f"written: {out_path}")
    print(f"hash:    {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

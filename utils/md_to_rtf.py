#!/usr/bin/env python3
"""
Simple Markdown → RTF (.doc) converter
Creates a Word-compatible .doc (RTF) without external dependencies.
Supports: # headings, paragraphs, bullet lists (- ), code fences ```.
"""
import argparse
from pathlib import Path
from datetime import datetime

RTF_HEADER = r"{\rtf1\ansi\deff0{\fonttbl{\f0 Arial;}{\f1 Courier New;}}\n"
RTF_FOOTER = r"}\n"


def esc(text: str) -> str:
    return text.replace('\\', r'\\').replace('{', r'\{').replace('}', r'\}')


def md_to_rtf_lines(lines: list[str]) -> list[str]:
    out: list[str] = []
    in_code = False

    # Title block
    title = "Guía Completa de Operación – PropertyScraper Dell710"
    out.append(r"\fs36 \b " + esc(title) + r"\b0\par\par\fs24 ")
    out.append(esc(datetime.now().strftime('%Y-%m-%d %H:%M')) + r"\par\par")

    for raw in lines:
        line = raw.rstrip('\n')

        # code fences
        if line.strip().startswith('```'):
            in_code = not in_code
            if not in_code:
                out.append(r"\par")
            else:
                out.append(r"\par{\f1 ")
            continue

        if in_code:
            out.append(esc(line) + r"\line")
            continue

        if line.startswith('#'):
            hashes = len(line) - len(line.lstrip('#'))
            text = line.lstrip('#').strip()
            size = {1: 28, 2: 24, 3: 22, 4: 20}.get(hashes, 20)
            out.append(fr"\par\fs{size} \b {esc(text)}\b0\fs22 \par")
            continue

        stripped = line.lstrip()
        if stripped.startswith(('- ', '* ')):
            out.append(r"\par \bullet " + esc(stripped[2:]) + r"\par")
            continue

        if stripped == '':
            out.append(r"\par")
            continue

        out.append(esc(line) + r"\par")

    if in_code:
        out.append(r"}\par")

    return out


def convert(md_path: Path, out_path: Path):
    text = md_path.read_text(encoding='utf-8', errors='replace')
    lines = text.splitlines()
    rtf_lines = md_to_rtf_lines(lines)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open('w', encoding='utf-8', newline='') as f:
        f.write(RTF_HEADER)
        for ln in rtf_lines:
            f.write(ln + "\n")
        f.write(RTF_FOOTER)


def main():
    ap = argparse.ArgumentParser(description='Convert Markdown to RTF (.doc)')
    ap.add_argument('-i', '--input', required=True, help='Input .md path')
    ap.add_argument('-o', '--output', required=True, help='Output .doc (RTF) path')
    args = ap.parse_args()

    convert(Path(args.input), Path(args.output))
    print(f"DOC (RTF) created: {args.output}")


if __name__ == '__main__':
    main()

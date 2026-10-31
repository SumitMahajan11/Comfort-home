#!/usr/bin/env python3
"""
tools/extract_pdf_clean.py

Robust pure-Python text extractor for Skia/Chromium-generated PDFs.
Correctly decodes font-specific CMaps (Identity-H / Type3 / CIDFontType2).
"""

import sys
import re
import zlib
from pathlib import Path

def decompress_stream(raw_obj):
    m = re.search(rb"stream[\r\n]+(.*?)[\r\n]+endstream", raw_obj, re.DOTALL)
    if not m:
        return b""
    try:
        return zlib.decompress(m.group(1))
    except:
        return m.group(1)

def parse_cmap(cstream):
    cmap = {}
    code_len = 2 # default 1 byte (2 hex chars)

    csr = re.search(rb"begincodespacerange(.*?)endcodespacerange", cstream, re.DOTALL)
    if csr:
        range_match = re.search(rb"<([0-9a-fA-F]+)>\s+<([0-9a-fA-F]+)>", csr.group(1))
        if range_match:
            code_len = len(range_match.group(1))

    # Parse beginbfchar
    for bfc in re.finditer(rb"beginbfchar(.*?)endbfchar", cstream, re.DOTALL):
        for m in re.finditer(rb"<([0-9a-fA-F]+)>\s+<([0-9a-fA-F]+)>", bfc.group(1)):
            src = int(m.group(1), 16)
            dst_hex = m.group(2).decode("ascii")
            try:
                cmap[src] = bytes.fromhex(dst_hex).decode("utf-16-be")
            except:
                pass

    # Parse beginbfrange
    for bfr in re.finditer(rb"beginbfrange(.*?)endbfrange", cstream, re.DOTALL):
        # Format 1: <start> <end> <dst_start>
        for m in re.finditer(rb"<([0-9a-fA-F]+)>\s+<([0-9a-fA-F]+)>\s+<([0-9a-fA-F]+)>", bfr.group(1)):
            start = int(m.group(1), 16)
            end = int(m.group(2), 16)
            dst_start = int(m.group(3), 16)
            for code in range(start, end + 1):
                val = dst_start + (code - start)
                try:
                    b = val.to_bytes((val.bit_length() + 7) // 8 or 1, "big")
                    if len(b) % 2 != 0:
                        b = b"\x00" + b
                    cmap[code] = b.decode("utf-16-be")
                except:
                    pass
        # Format 2: <start> <end> [ <dst1> <dst2> ... ]
        for m in re.finditer(rb"<([0-9a-fA-F]+)>\s+<([0-9a-fA-F]+)>\s*\[(.*?)\]", bfr.group(1), re.DOTALL):
            start = int(m.group(1), 16)
            end = int(m.group(2), 16)
            dsts = re.findall(rb"<([0-9a-fA-F]+)>", m.group(3))
            for i, d in enumerate(dsts):
                code = start + i
                try:
                    cmap[code] = bytes.fromhex(d.decode("ascii")).decode("utf-16-be")
                except:
                    pass

    return cmap, code_len

def extract_pdf_text(pdf_path):
    with open(pdf_path, "rb") as f:
        data = f.read()

    objs = {}
    for m in re.finditer(rb"(\d+)\s+0\s+obj\s*(.*?)endobj", data, re.DOTALL):
        objs[int(m.group(1))] = m.group(2)

    # Find page objects
    pages = []
    for oid, content in objs.items():
        if b"/Type /Page\n" in content or b"/Type /Page " in content or b"/Type/Page" in content:
            pages.append(oid)

    all_text = []

    for p_id in sorted(pages):
        p_content = objs[p_id]

        # Extract font mappings in page resources
        font_map = {}
        f_match = re.search(rb"/Font\s*<<\s*(.*?)\s*>>", p_content, re.DOTALL)
        if f_match:
            for fm in re.finditer(rb"/(F\d+)\s+(\d+)\s+0\s+R", f_match.group(1)):
                font_map[fm.group(1).decode("ascii")] = int(fm.group(2))

        # Build CMap and code length for each font
        font_cmaps = {}
        font_code_lens = {}
        for fname, f_oid in font_map.items():
            f_obj = objs.get(f_oid, b"")
            tu_match = re.search(rb"/ToUnicode\s+(\d+)\s+0\s+R", f_obj)
            if tu_match:
                tu_oid = int(tu_match.group(1))
                cstream = decompress_stream(objs[tu_oid])
                cmap, clen = parse_cmap(cstream)
                font_cmaps[fname] = cmap
                font_code_lens[fname] = clen
            else:
                font_cmaps[fname] = {}
                font_code_lens[fname] = 2

        # Extract contents
        c_match = re.search(rb"/Contents\s+(\d+)\s+0\s+R", p_content)
        if not c_match:
            continue
        c_stream = decompress_stream(objs[int(c_match.group(1))])

        # Parse text blocks
        bt_blocks = re.findall(rb"BT\s*(.*?)\s*ET", c_stream, re.DOTALL)
        for block in bt_blocks:
            current_font = "F1"
            block_text = ""
            # Match font changes and text operators
            items = re.findall(rb"/(F\d+)\s+[\d\.]+\s+Tf|<([0-9a-fA-F]+)>\s*Tj|(\d+\.?\d*)\s+(\d+\.?\d*)\s+Td", block)
            for f_op, hex_tj, td_x, td_y in items:
                if f_op:
                    current_font = f_op.decode("ascii")
                elif hex_tj:
                    cmap = font_cmaps.get(current_font, {})
                    clen = font_code_lens.get(current_font, 2)
                    raw = hex_tj.decode("ascii")
                    for k in range(0, len(raw), clen):
                        code = int(raw[k:k+clen], 16)
                        char = cmap.get(code, "")
                        block_text += char
                elif td_x or td_y:
                    # If vertical move or significant horizontal move, insert space
                    if td_y and float(td_y) != 0:
                        block_text += "\n"
                    elif td_x and float(td_x) > 3:
                        pass
            if block_text.strip():
                all_text.append(block_text.strip())

    return "\n".join(all_text)

def main():
    if len(sys.argv) < 2:
        print("Usage: extract_pdf_clean.py <path_to_pdf>")
        sys.exit(1)
    
    text = extract_pdf_text(sys.argv[1])
    print(text)

if __name__ == "__main__":
    main()

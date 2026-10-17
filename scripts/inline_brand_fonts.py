#!/usr/bin/env python3
"""Regenerate render/src/assets/brandfonts.ts (Archivo 800 + Source Sans 3 700, latin) from Google Fonts.

The reel uses the same two typefaces as jesemmhomeventures.com. They are inlined as data URIs
for the reason explained in render/src/fonts.ts. Swap the families in the URL below to rebrand.

    python3 scripts/inline_brand_fonts.py
"""
import base64, pathlib, re, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
UA = {"User-Agent": "Mozilla/5.0 (Macintosh) AppleWebKit/537.36 Chrome/120"}
CSS = "https://fonts.googleapis.com/css2?family=Archivo:wght@800&family=Source+Sans+3:wght@700&display=swap"
HEADER = ("// Archivo (headline) and Source Sans 3 (captions), latin subsets, SIL Open Font License 1.1 (fonts.google.com).\n"
          "// The same two typefaces as jesemmhomeventures.com. Inlined as data URIs for the reason given in ../fonts.ts.\n"
          "// Regenerate with: python3 scripts/inline_brand_fonts.py\n")


def main() -> int:
    css = urllib.request.urlopen(urllib.request.Request(CSS, headers=UA)).read().decode()
    out = {}
    for subset, block in re.findall(r"/\* (\S+) \*/\s*@font-face \{(.*?)\}", css, re.S):
        if subset != "latin":
            continue
        family = re.search(r"font-family: '([^']+)'", block).group(1)
        url = re.search(r"url\(([^)]+)\)", block).group(1)
        out[family] = base64.b64encode(urllib.request.urlopen(urllib.request.Request(url, headers=UA)).read()).decode()
    dest = ROOT / "render/src/assets/brandfonts.ts"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(HEADER + f'export const ARCHIVO_800 = "data:font/woff2;base64,{out["Archivo"]}";\n'
                    f'export const SOURCE_SANS_700 = "data:font/woff2;base64,{out["Source Sans 3"]}";\n')
    print(f"wrote {dest.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

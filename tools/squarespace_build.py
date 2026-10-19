"""Genera el bloque de código para Squarespace a partir de index.html.

Uso:  python tools/squarespace_build.py <commit> [salida]

- Aísla el CSS bajo #fdi para no pisar ni ser pisado por la plantilla de Squarespace.
- Las imágenes y fuentes se sirven desde jsDelivr fijadas a <commit> (tiene que estar en GitHub).
- Sin <script>: el plan Personal de Squarespace no ejecuta JavaScript en bloques de código.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCOPE = "#fdi"


def split_rules(css):
    """Divide CSS en (prelude, cuerpo) de primer nivel respetando llaves anidadas."""
    out, i, n = [], 0, len(css)
    while i < n:
        j = css.find("{", i)
        if j == -1:
            break
        prelude = css[i:j].strip()
        depth, k = 1, j + 1
        while depth:
            depth += {"{": 1, "}": -1}.get(css[k], 0)
            k += 1
        out.append((prelude, css[j + 1:k - 1]))
        i = k
    return out


def scope_selector(sel):
    sel = sel.strip()
    if sel.startswith(".js"):
        return None  # mejoras que dependen de JS: fuera
    if sel in (":root", "body"):
        return SCOPE
    if sel == "html":
        return "html"
    if sel.startswith("*") or sel.startswith("::") or sel.startswith(":"):
        return f"{SCOPE} {sel}"
    return f"{SCOPE} {sel}"


def scope_css(css):
    out = []
    for prelude, body in split_rules(css):
        if prelude.startswith("@font-face"):
            out.append(f"{prelude}{{{body}}}")
        elif prelude.startswith("@keyframes"):
            out.append(f"{prelude}{{{body}}}")
        elif prelude.startswith("@media"):
            inner = scope_css(body)
            if inner.strip():
                out.append(f"{prelude}{{{inner}}}")
        else:
            sels = [s for s in (scope_selector(x) for x in prelude.split(",")) if s]
            if sels:
                out.append(f"{', '.join(sels)}{{{body.strip()}}}")
    return "\n".join(out)


def main():
    commit = sys.argv[1]
    dest = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "squarespace-bloque.html"
    cdn = f"https://cdn.jsdelivr.net/gh/urpito/Fratelli-d-Italia@{commit}/"
    src = (ROOT / "index.html").read_text(encoding="utf-8")

    css = re.search(r"<style>(.*?)</style>", src, re.S).group(1)
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    css = css.replace("url(fonts/", f"url({cdn}fonts/")
    scoped = scope_css(css)
    # Solo se carga en la página que lleva el bloque: ahí manda nuestro diseño
    extra = f"""
html,body{{overflow-x:clip}}
#header,#footer-sections,.header-announcement-bar-wrapper{{display:none!important}}
.page-section:has({SCOPE}),.page-section:has({SCOPE}) .content-wrapper,.page-section:has({SCOPE}) .content{{padding:0!important;max-width:none!important;min-height:0!important}}
.sqs-block:has({SCOPE}),.fe-block:has({SCOPE}){{padding:0!important}}
.fluid-engine:has({SCOPE}){{display:block!important}}
.fe-block:has({SCOPE}){{position:static!important;width:auto!important;height:auto!important}}
{SCOPE}{{position:relative;width:100vw;margin-left:calc(50% - 50vw);text-align:left;overflow-x:clip}}
{SCOPE} p,{SCOPE} h1,{SCOPE} h2,{SCOPE} h3,{SCOPE} h4{{margin:0;letter-spacing:normal;text-transform:none}}
{SCOPE} a{{text-decoration:none}}
"""
    body = re.search(r"<body>(.*?)<script>", src, re.S).group(1)
    body = re.sub(r'(src|href)="(img|fonts)/', lambda m: f'{m.group(1)}="{cdn}{m.group(2)}/', body)
    body = body.replace('<span id="year">2026</span>', "2026")
    body = re.sub(r"<!--.*?-->", "", body, flags=re.S)
    body = re.sub(r"\n\s*\n", "\n", body)

    html = f"<style>\n{scoped}\n{extra}</style>\n<div id=\"fdi\">\n{body.strip()}\n</div>\n"
    dest.write_text(html, encoding="utf-8", newline="\n")
    print(f"{dest} · {len(html):,} caracteres")


if __name__ == "__main__":
    main()

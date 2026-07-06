"""Gera uma apresentacao HTML autocontida (deck com nav/teclado/swipe) a partir de um
markdown no estilo Marp (front matter YAML + slides separados por `---`).

Nao usa o marp-cli: e' um conversor proprio (python-markdown por slide) que reproduz o
layout fixo 16:9 usado nos decks existentes em docs/*.html (fundo escuro, canvas 1280x720
escalado via JS, contador de slide, `<!-- _class: ... -->` / `<!-- _paginate: false -->`
por slide).

Uso:
    python scripts/render_marp.py docs/apresentacao_sarima_valor.md [outro.md ...]

Cada `arquivo.md` gera `arquivo.html` na mesma pasta.
"""
import re
import sys
from pathlib import Path

import markdown
import yaml

MD_EXTENSIONS = ["tables", "fenced_code", "sane_lists", "nl2br"]

# Delimitadores LaTeX suportados (KaTeX auto-render). Protegidos ANTES do markdown.markdown()
# rodar -- senao `_`/`*` dentro da formula (ex.: beta_1) seriam lidos como enfase/italico.
MATH_RE = re.compile(r"(\$\$.*?\$\$|\\\(.*?\\\)|\\\[.*?\\\])", re.DOTALL)


def protect_math(text):
    placeholders = []

    def _sub(m):
        placeholders.append(m.group(0))
        return f"@@MATH{len(placeholders) - 1}@@"

    return MATH_RE.sub(_sub, text), placeholders


def restore_math(html, placeholders):
    for i, tex in enumerate(placeholders):
        html = html.replace(f"@@MATH{i}@@", tex)
    return html


KATEX_HEAD = """<link rel="stylesheet" href="vendor/katex/katex.min.css">
<script defer src="vendor/katex/katex.min.js"></script>
<script defer src="vendor/katex/auto-render.min.js"
        onload="renderMathInElement(document.body, {
          delimiters: [
            {left: '$$', right: '$$', display: true},
            {left: '\\\\(', right: '\\\\)', display: false},
            {left: '\\\\[', right: '\\\\]', display: true}
          ]
        });"></script>"""

BASE_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
html, body { width: 100%; height: 100%; background: #111; overflow: hidden; }

/* Canvas de tamanho fixo (16:9) escalado para caber na janela via JS.
   Isso mantem a proporcao e o tamanho aparente CONSISTENTE em qualquer tela. */
#deck { position: absolute; top: 0; left: 0; width: 1280px; height: 720px; transform-origin: top left; }

.slide {
  display: none;
  position: absolute;
  top: 0; left: 0; width: 1280px; height: 720px;
  background: #fff;
  overflow: hidden;
}
.slide.active { display: block; }

/* Conteudo do slide: largura fixa, altura natural; se passar de 720px o JS
   aplica um scale para caber (evita vazar da tela). */
.slide-inner {
  position: absolute; top: 0; left: 0;
  width: 1280px;
  padding: 52px 64px 44px 64px;
  transform-origin: top left;
  display: flex; flex-direction: column;
}

/* --- Slide counter --- */
.slide-num {
  position: absolute;
  bottom: 14px; right: 24px;
  font-size: 13px; color: #aaa;
}

/* --- Nav --- */
#nav {
  position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%);
  display: flex; gap: 12px; z-index: 100;
}
#nav button {
  background: rgba(255,255,255,0.15); border: 1px solid rgba(255,255,255,0.3);
  color: #fff; padding: 6px 18px; border-radius: 20px; cursor: pointer;
  font-size: 14px; backdrop-filter: blur(4px);
  transition: background 0.2s;
}
#nav button:hover { background: rgba(255,255,255,0.3); }
#progress {
  position: fixed; top: 0; left: 0; height: 3px;
  background: #74b9ff; transition: width 0.3s; z-index: 200;
}

/* ── Cover slide override ── */
section.cover {
  background: linear-gradient(135deg, #0a3d62 0%, #1e3799 100%) !important;
  color: #ffffff !important;
}
section.cover .slide-inner {
  height: 720px;
  justify-content: center !important;
  align-items: flex-start !important;
}
section.cover h1 { color: #ffffff !important; border-bottom: 3px solid #74b9ff !important; font-size: 44px; }
section.cover h2 { color: #a8d8ea !important; font-size: 26px; font-weight: 400; margin-top: 10px; }
section.cover p   { color: #dfe6e9 !important; font-size: 18px; margin-top: 20px; }
section.cover strong { color: #ffffff !important; }
section.cover .slide-num { color: rgba(255,255,255,0.3) !important; }

/* ── Section divider override ── */
section.section-divider {
  background: #1e3799 !important;
  color: #ffffff !important;
  text-align: center;
}
section.section-divider .slide-inner {
  height: 720px;
  justify-content: center !important;
  align-items: center !important;
}
section.section-divider h2 { color: #ffffff !important; font-size: 36px; }
section.section-divider h3 { color: #74b9ff !important; font-size: 26px; margin-top: 12px; }
section.section-divider p  { color: #a8d8ea !important; font-size: 20px; margin-top: 10px; }
section.section-divider strong { color: #ffffff !important; }
section.section-divider .slide-num { color: rgba(255,255,255,0.3) !important; }

/* ── General content ── */
section h1 { font-size: 36px; color: #0a3d62; border-bottom: 2px solid #0a3d62; padding-bottom: 8px; margin-bottom: 16px; }
section h2 { font-size: 28px; color: #1e3799; margin-bottom: 10px; }
section h3 { font-size: 22px; color: #0a3d62; margin-bottom: 8px; }
section p  { margin: 6px 0; line-height: 1.5; }
section ul, section ol { margin: 6px 0 6px 22px; line-height: 1.6; }
section li { margin: 3px 0; }
section strong { color: #0a3d62; }

section table { width: 100%; border-collapse: collapse; font-size: 17px; margin: 10px 0; }
section th { background: #0a3d62; color: white; padding: 7px 10px; text-align: left; }
section th strong, section th code { color: inherit; }
section td { padding: 6px 10px; border-bottom: 1px solid #ddd; }
section tr:nth-child(even) { background: #f0f4f8; }

section pre  { background: #1a1a2e; color: #ecf0f1; padding: 14px; border-radius: 6px;
               font-family: 'Consolas','Courier New',monospace; font-size: 14px;
               line-height: 1.5; overflow-x: auto; margin: 10px 0; white-space: pre; }
section code { font-family: 'Consolas','Courier New',monospace; }
section p > code { background: #eaf2ff; color: #1e3799; padding: 1px 5px; border-radius: 3px; }

section img { max-height: 440px; max-width: 100%; display: block;
              margin: 8px auto; object-fit: contain; }
section figure { margin: 6px auto; text-align: center; }
section figcaption { font-size: 14px; color: #666; margin-top: 4px; }

.box {
  border-left: 4px solid #1e3799;
  background: #eaf2ff;
  padding: 10px 16px;
  border-radius: 4px;
  margin: 10px 0;
}
.highlight { background: #27ae60; color: white; padding: 2px 7px; border-radius: 4px; font-weight: bold; }
.warn      { background: #e74c3c; color: white; padding: 2px 7px; border-radius: 4px; font-weight: bold; }
"""

DECK_JS = """
var CW = 1280, CH = 720;   // dimensoes do canvas (16:9)
var cur = 0;
var deck   = document.getElementById('deck');
var slides = document.querySelectorAll('.slide');
var total  = slides.length;
var prog   = document.getElementById('progress');
var counter= document.getElementById('counter');

// Escala o canvas inteiro para caber na janela (mantem a proporcao, centraliza).
function fitDeck() {
  var s = Math.min(window.innerWidth / CW, window.innerHeight / CH);
  var tx = (window.innerWidth  - CW * s) / 2;
  var ty = (window.innerHeight - CH * s) / 2;
  deck.style.transform = 'translate(' + tx + 'px,' + ty + 'px) scale(' + s + ')';
}

// Se o conteudo de um slide passa da altura do canvas, encolhe so aquele slide.
function fitSlide(sl) {
  var inner = sl.querySelector('.slide-inner');
  if (!inner) return;
  inner.style.transform = 'none';
  var h = inner.offsetHeight;
  if (h > CH) { inner.style.transform = 'scale(' + (CH / h).toFixed(4) + ')'; }
}

// Mede/ajusta todos os slides uma vez (precisa exibir cada um para medir a altura).
function fitAllSlides() {
  slides.forEach(function(sl) {
    var wasActive = sl.classList.contains('active');
    sl.style.display = 'block';
    fitSlide(sl);
    if (!wasActive) sl.style.display = '';
  });
}

function show(n) {
  slides[cur].classList.remove('active');
  cur = (n + total) % total;
  slides[cur].classList.add('active');
  prog.style.width = ((cur+1)/total*100) + '%';
  counter.textContent = (cur+1) + ' / ' + total;
}

function go(d) { show(cur + d); }

window.addEventListener('resize', fitDeck);
window.addEventListener('load', function() { fitAllSlides(); fitDeck(); });

document.addEventListener('keydown', function(e) {
  if (e.key === 'ArrowRight' || e.key === 'ArrowDown' || e.key === ' ') go(1);
  if (e.key === 'ArrowLeft'  || e.key === 'ArrowUp')  go(-1);
  if (e.key === 'Home') show(0);
  if (e.key === 'End')  show(total-1);
});

// Touch/swipe support
var tsx = 0;
document.addEventListener('touchstart', function(e) { tsx = e.touches[0].clientX; });
document.addEventListener('touchend',   function(e) {
  var dx = e.changedTouches[0].clientX - tsx;
  if (Math.abs(dx) > 40) go(dx < 0 ? 1 : -1);
});

fitAllSlides();
fitDeck();
show(0);
"""

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?\n)---\s*\n", re.DOTALL)
DIRECTIVE_RE = re.compile(r"^<!--\s*_([a-zA-Z]+):\s*(.*?)\s*-->\s*$")


def parse_frontmatter(text):
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    meta = yaml.safe_load(m.group(1)) or {}
    body = text[m.end():]
    return meta, body


def split_slides(body):
    # Separador de slide: linha com EXATAMENTE `---` (nunca confunde com o separador
    # de cabecalho de tabela markdown, que sempre tem `|`).
    raw = re.split(r"\n---\s*\n", "\n" + body.strip() + "\n")
    return [s.strip("\n") for s in raw]


def extract_directives(slide_text):
    """Le linhas `<!-- _class: X -->` / `<!-- _paginate: false -->` no topo do slide."""
    classes, paginate = [], None
    lines = slide_text.split("\n")
    i = 0
    while i < len(lines) and lines[i].strip() == "":
        i += 1
    while i < len(lines):
        m = DIRECTIVE_RE.match(lines[i].strip())
        if not m:
            break
        key, val = m.group(1).lower(), m.group(2).strip().lower()
        if key == "class":
            classes.extend(val.split())
        elif key == "paginate":
            paginate = val == "true"
        i += 1
    remaining = "\n".join(lines[i:])
    return classes, paginate, remaining


def render_slide(slide_text, index, page_no, total_paginated, default_paginate):
    """page_no: posicao do slide na sequencia de slides PAGINADOS (None se nao paginado).
    Replica o Marp real: o contador de pagina so avanca/existe nos slides paginados
    (ex.: a capa costuma ter `_paginate: false` e fica fora da contagem)."""
    classes, paginate_override, content_md = extract_directives(slide_text)
    paginate = default_paginate if paginate_override is None else paginate_override
    content_md, math_ph = protect_math(content_md)
    html_body = markdown.markdown(content_md, extensions=MD_EXTENSIONS)
    html_body = restore_math(html_body, math_ph)
    class_attr = " ".join(["slide"] + classes)
    footer = f'<span class="slide-num">{page_no} / {total_paginated}</span>' if paginate and page_no else ""
    return f'<section class="{class_attr}" data-index="{index}"><div class="slide-inner">{html_body}</div>{footer}</section>'


def guess_title(meta, first_slide_md):
    if meta.get("title"):
        return meta["title"]
    h1 = re.search(r"^#\s+(.+)$", first_slide_md, re.MULTILINE)
    if h1:
        return re.sub(r"[*_`]", "", h1.group(1)).strip()
    return "Apresentacao"


def render_deck(md_path: Path) -> Path:
    text = md_path.read_text(encoding="utf-8")
    meta, body = parse_frontmatter(text)
    slides_raw = split_slides(body)
    default_paginate = bool(meta.get("paginate", False))

    # Pre-computa quais slides sao paginados (direttiva por slide pode sobrescrever o
    # default do front matter) para numerar so essas, como o Marp real faz.
    paginate_flags = []
    for s in slides_raw:
        _, override, _ = extract_directives(s)
        paginate_flags.append(default_paginate if override is None else override)
    total_paginated = sum(paginate_flags)

    sections, page_no = [], 0
    for i, (s, paginated) in enumerate(zip(slides_raw, paginate_flags)):
        if paginated:
            page_no += 1
        sections.append(
            render_slide(s, i, page_no if paginated else None, total_paginated, default_paginate)
        )
    title = guess_title(meta, slides_raw[0] if slides_raw else "")
    custom_css = (meta.get("style") or "").strip()

    html_doc = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
{KATEX_HEAD}
<style>
{BASE_CSS}
/* ── Custom CSS from Marp style block ── */
{custom_css}
section .katex-display {{ margin: 8px 0; text-align: center; }}
</style>
</head>
<body>
<div id="progress"></div>
<div id="deck">
{chr(10).join(sections)}
</div>
<div id="nav">
  <button onclick="go(-1)">&#8592; Anterior</button>
  <span id="counter" style="color:#fff;font-size:14px;padding:6px 10px;"></span>
  <button onclick="go(1)">Próximo &#8594;</button>
</div>
<script>
{DECK_JS}
</script>
</body>
</html>
"""
    out_path = md_path.with_suffix(".html")
    out_path.write_text(html_doc, encoding="utf-8")
    return out_path


def main(argv):
    if not argv:
        print("uso: python scripts/render_marp.py <arquivo.md> [outro.md ...]")
        return 1
    for arg in argv:
        md_path = Path(arg)
        out_path = render_deck(md_path)
        print(f"[render_marp] {md_path} -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

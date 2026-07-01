"""
Converte o arquivo Marp Markdown em apresentação HTML standalone.
Uso: python render_marp.py
"""
import re, sys, pathlib
import markdown as md_lib

# Raiz do projeto (sobe até achar CLAUDE.md), independente de onde o script roda.
_ROOT = pathlib.Path(__file__).resolve().parent
while not (_ROOT / 'CLAUDE.md').exists() and _ROOT != _ROOT.parent:
    _ROOT = _ROOT.parent

# Arquivo de entrada: 1o argumento (relativo à raiz ou absoluto) ou o default.
if len(sys.argv) > 1:
    _arg = pathlib.Path(sys.argv[1])
    INPUT = _arg if _arg.is_absolute() else (_ROOT / _arg)
else:
    INPUT = _ROOT / 'docs' / 'apresentacao_modelo_qtd.md'
OUTPUT = INPUT.with_suffix('.html')

# ── Lê o arquivo Marp ─────────────────────────────────────────────────────────
raw = INPUT.read_text(encoding='utf-8')

# Extrai bloco YAML de front-matter
fm_match = re.match(r'^---\n(.*?)\n---\n', raw, re.DOTALL)
fm_text   = fm_match.group(1) if fm_match else ''
body      = raw[fm_match.end():] if fm_match else raw

# Extrai custom CSS do bloco style: no front matter
css_match = re.search(r'^style:\s*\|\n((?:  .+\n?)+)', fm_text, re.MULTILINE)
custom_css = ''
if css_match:
    css_raw = css_match.group(1)
    custom_css = re.sub(r'^  ', '', css_raw, flags=re.MULTILINE)

# ── Divide em slides pelo separador --- ────────────────────────────────────────
slides_raw = re.split(r'\n---\n', body)

def parse_slide(text: str) -> tuple[str, str, str]:
    """Retorna (class, paginate_flag, html_content)."""
    slide_class   = ''
    no_paginate   = False
    lines = text.splitlines()
    clean = []
    for ln in lines:
        m_class  = re.match(r'<!--\s*_class:\s*([\w-]+)\s*-->', ln)
        m_pag    = re.match(r'<!--\s*_paginate:\s*false\s*-->', ln)
        if m_class:
            slide_class = m_class.group(1)
        elif m_pag:
            no_paginate = True
        else:
            clean.append(ln)
    content_md = '\n'.join(clean).strip()

    # Converte blocos <div class="..."> que Marp suporta
    # markdown-it suporta HTML inline, mas python-markdown também
    html = md_lib.markdown(
        content_md,
        extensions=['tables', 'fenced_code', 'nl2br', 'attr_list'],
    )
    # Converte blocos de código simples com ``` que viram preformatados
    return slide_class, no_paginate, html

parsed = [parse_slide(s) for s in slides_raw if s.strip()]

# ── Monta o HTML ───────────────────────────────────────────────────────────────
SLIDE_BASE_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
html, body { width: 100%; height: 100%; background: #111; overflow: hidden; }
#deck { width: 100%; height: 100%; position: relative; }

.slide {
  display: none;
  position: absolute;
  top: 0; left: 0; width: 100%; height: 100%;
  background: #fff;
  padding: 52px 64px 44px 64px;
  overflow: hidden;
}
.slide.active { display: flex; flex-direction: column; }

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
"""

slides_html = []
total_slides = sum(1 for sc, np_, _ in parsed if not np_)
page_num = 0

for i, (slide_class, no_paginate, html_content) in enumerate(parsed):
    cls = f'slide {slide_class}' if slide_class else 'slide'
    num_html = ''
    if not no_paginate:
        page_num += 1
        num_html = f'<span class="slide-num">{page_num} / {total_slides}</span>'
    slides_html.append(
        f'<section class="{cls}" data-index="{i}">'
        f'{html_content}'
        f'{num_html}'
        f'</section>'
    )

all_slides = '\n'.join(slides_html)
n = len(parsed)

html_doc = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Modelo de Previsão Diária — Quantidade de Propostas</title>
<style>
{SLIDE_BASE_CSS}
/* ── Custom CSS from Marp style block ── */
{custom_css}

/* ── Cover slide override ── */
section.cover {{
  background: linear-gradient(135deg, #0a3d62 0%, #1e3799 100%) !important;
  color: #ffffff !important;
  justify-content: center !important;
  align-items: flex-start !important;
}}
section.cover h1 {{ color: #ffffff !important; border-bottom: 3px solid #74b9ff !important; font-size: 44px; }}
section.cover h2 {{ color: #a8d8ea !important; font-size: 26px; font-weight: 400; margin-top: 10px; }}
section.cover p   {{ color: #dfe6e9 !important; font-size: 18px; margin-top: 20px; }}
section.cover .slide-num {{ color: rgba(255,255,255,0.3) !important; }}

/* ── Section divider override ── */
section.section-divider {{
  background: #1e3799 !important;
  color: #ffffff !important;
  justify-content: center !important;
  align-items: center !important;
  text-align: center;
}}
section.section-divider h2 {{ color: #ffffff !important; font-size: 36px; }}
section.section-divider h3 {{ color: #74b9ff !important; font-size: 26px; margin-top: 12px; }}
section.section-divider p  {{ color: #a8d8ea !important; font-size: 20px; margin-top: 10px; }}
section.section-divider .slide-num {{ color: rgba(255,255,255,0.3) !important; }}

/* ── General content ── */
section h1 {{ font-size: 36px; color: #0a3d62; border-bottom: 2px solid #0a3d62; padding-bottom: 8px; margin-bottom: 16px; }}
section h2 {{ font-size: 28px; color: #1e3799; margin-bottom: 10px; }}
section h3 {{ font-size: 22px; color: #0a3d62; margin-bottom: 8px; }}
section p  {{ margin: 6px 0; line-height: 1.5; }}
section ul, section ol {{ margin: 6px 0 6px 22px; line-height: 1.6; }}
section li {{ margin: 3px 0; }}
section strong {{ color: #0a3d62; }}

section table {{ width: 100%; border-collapse: collapse; font-size: 17px; margin: 10px 0; }}
section th {{ background: #0a3d62; color: white; padding: 7px 10px; text-align: left; }}
section td {{ padding: 6px 10px; border-bottom: 1px solid #ddd; }}
section tr:nth-child(even) {{ background: #f0f4f8; }}

section pre  {{ background: #1a1a2e; color: #ecf0f1; padding: 14px; border-radius: 6px;
               font-family: 'Consolas','Courier New',monospace; font-size: 14px;
               line-height: 1.5; overflow-x: auto; margin: 10px 0; white-space: pre; }}
section code {{ font-family: 'Consolas','Courier New',monospace; }}
section p > code {{ background: #eaf2ff; color: #1e3799; padding: 1px 5px; border-radius: 3px; }}

section img {{ max-height: 62vh; max-width: 100%; display: block;
              margin: 8px auto; object-fit: contain; }}
section figure {{ margin: 6px auto; text-align: center; }}
section figcaption {{ font-size: 14px; color: #666; margin-top: 4px; }}

.box {{
  border-left: 4px solid #1e3799;
  background: #eaf2ff;
  padding: 10px 16px;
  border-radius: 4px;
  margin: 10px 0;
}}
.highlight {{ background: #27ae60; color: white; padding: 2px 7px; border-radius: 4px; font-weight: bold; }}
.warn      {{ background: #e74c3c; color: white; padding: 2px 7px; border-radius: 4px; font-weight: bold; }}
</style>
</head>
<body>
<div id="progress"></div>
<div id="deck">
{all_slides}
</div>
<div id="nav">
  <button onclick="go(-1)">&#8592; Anterior</button>
  <span id="counter" style="color:#fff;font-size:14px;padding:6px 10px;"></span>
  <button onclick="go(1)">Próximo &#8594;</button>
</div>
<script>
var cur = 0;
var slides = document.querySelectorAll('.slide');
var total  = slides.length;
var prog   = document.getElementById('progress');
var counter= document.getElementById('counter');

function show(n) {{
  slides[cur].classList.remove('active');
  cur = (n + total) % total;
  slides[cur].classList.add('active');
  prog.style.width = ((cur+1)/total*100) + '%';
  counter.textContent = (cur+1) + ' / ' + total;
}}

function go(d) {{ show(cur + d); }}

document.addEventListener('keydown', function(e) {{
  if (e.key === 'ArrowRight' || e.key === 'ArrowDown' || e.key === ' ') go(1);
  if (e.key === 'ArrowLeft'  || e.key === 'ArrowUp')  go(-1);
  if (e.key === 'Home') show(0);
  if (e.key === 'End')  show(total-1);
}});

// Touch/swipe support
var tsx = 0;
document.addEventListener('touchstart', function(e) {{ tsx = e.touches[0].clientX; }});
document.addEventListener('touchend',   function(e) {{
  var dx = e.changedTouches[0].clientX - tsx;
  if (Math.abs(dx) > 40) go(dx < 0 ? 1 : -1);
}});

show(0);
</script>
</body>
</html>
"""

OUTPUT.write_text(html_doc, encoding='utf-8')
print(f'Renderizado: {OUTPUT}')
print(f'Total de slides: {n}')

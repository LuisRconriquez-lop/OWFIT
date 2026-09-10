"""Identidad visual y componentes reutilizables de la interfaz."""

from __future__ import annotations

import numpy as np
import streamlit as st

from src.utils import money

# --------------------------------------------------------------- paleta
# Paleta editorial "activewear premium": crema/grafito como base, un solo
# acento sofisticado (vino/burgundy) y los tres semáforos de estado clásicos
# (musgo=favorable, ocre=advertencia, negativo=problema) discretos, no
# saturados. Solo se retocan los VALORES hex; ninguna clave cambia de nombre,
# así que cada referencia existente en charts.py y en las vistas sigue
# funcionando sin tocarse.
#
# Roles semánticos separados de los roles de marca/segmento (antes "rosa" y
# "musgo" significaban dos cosas a la vez):
#   - "rosa"     = SOLO marca OWFIT y acento/highlight (nunca "negativo").
#   - "musgo"    = SOLO estado positivo/ok/subir precio (ya no es un segmento).
#   - "premium"  = segmento "Premium internacional" (antes compartía musgo).
#   - "negativo" = SOLO estado negativo/alerta/bajar precio (antes compartía
#                  rosa, lo que hacía leer "OWFIT" como "algo va mal").
#   - "ocre"     = advertencia/atención (tercer semáforo, ni bien ni mal).
# Un color de marca/segmento nunca debe usarse también como estado, y viceversa.
COLORES = {
    "tinta": "#221E1A",
    "musgo": "#3B5D48",
    "salvia": "#8FA99A",
    "arena": "#EFE6D6",
    "lienzo": "#FAF7F1",
    "rosa": "#7C3548",
    "premium": "#5D7A93",
    "negativo": "#A6503A",
    "ocre": "#C1A063",
    "gris": "#7D7568",
    "linea": "#E1D9C8",
}

COLOR_SEGMENTO = {
    "OWFIT": COLORES["rosa"],
    "Premium internacional": COLORES["premium"],
    "Mid-market MX": COLORES["salvia"],
    "Emergente MX": COLORES["ocre"],
    "Sin clasificar": COLORES["gris"],
}

# Paleta decorativa para series/categorías SIN significado (términos, marcas
# genéricas, etc.): deliberadamente sin "rosa" (marca) ni "negativo" (alerta),
# para que un color de esta lista nunca se confunda con OWFIT o con "va mal".
SECUENCIA = [
    COLORES["musgo"],
    COLORES["premium"],
    COLORES["salvia"],
    COLORES["ocre"],
    COLORES["gris"],
    "#8E6E9E",
    "#7A6C5D",
]

# Iconos geométricos minimalistas para la navegación (misma familia visual que
# el favicon "◧" del set_page_config). Sin emojis: solo el bloque Unicode
# "Geometric Shapes", de soporte universal en fuentes de sistema.
ICONOS_NAV = {
    "Resumen": "◧",
    "Pricing": "◆",
    "Simulador": "◎",
    "Competencia": "◫",
    "Rentabilidad": "▲",
    "Encuesta": "▥",
    "EDA de mercado": "▤",
    "Estacionalidad": "◪",
    "Escenarios": "◨",
    "Packaging": "▧",
    "Metodología": "▦",
}


def etiqueta_nav(pagina: str) -> str:
    """Antepone el icono minimalista de la sección a su nombre, sin tocar el
    nombre en sí: los llamadores que usan el nombre como llave de diccionario
    siguen funcionando si aplican la misma función en ambos lados."""
    icono = ICONOS_NAV.get(pagina, "○")
    return f"{icono}  {pagina}"


CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,450;9..144,560;9..144,620&family=Inter+Tight:wght@300;400;500;600;700&display=swap');

:root {{
    --owfit-tinta: {COLORES['tinta']};
    --owfit-gris: {COLORES['gris']};
    --owfit-linea: {COLORES['linea']};
    --owfit-acento: {COLORES['rosa']};
    --owfit-ok: {COLORES['musgo']};
    --owfit-alerta: {COLORES['negativo']};
    --owfit-advertencia: {COLORES['ocre']};
}}

html, body, [class*="css"], .stApp {{
    font-family: 'Inter Tight', system-ui, sans-serif;
    font-feature-settings: 'tnum' 1, 'cv05' 1;
}}
.stApp {{ background: {COLORES['lienzo']}; }}
* {{ scrollbar-color: {COLORES['linea']} transparent; }}

/* ------------------------------------------------------------ layout / aire */
.main .block-container {{
    padding: 2.6rem 3.2rem 5rem 3.2rem;
    max-width: 1440px;
}}
[data-testid="stHorizontalBlock"] {{ gap: 1.5rem; }}
hr {{ margin: 2.2rem 0; border-color: {COLORES['linea']}; }}

/* ------------------------------------------------------------ tipografía */
h1 {{
    font-family: 'Fraunces', 'Inter Tight', serif; font-weight: 600;
    letter-spacing: -0.015em; color: {COLORES['tinta']}; font-size: 2.9rem;
    margin-bottom: 0.15rem; line-height: 1.08;
}}
h1 + div[data-testid="stCaptionContainer"] {{
    font-size: 1.0rem; color: {COLORES['gris']}; max-width: 62rem;
    margin-bottom: 1.5rem;
}}
h2 {{
    font-weight: 600; letter-spacing: -0.01em; color: {COLORES['tinta']}; font-size: 1.28rem;
    margin-top: 2.1rem; padding-top: 1.0rem; border-top: 1px solid {COLORES['linea']};
}}
h3 {{
    font-weight: 700; color: {COLORES['tinta']}; font-size: 1.08rem; letter-spacing: 0.01em;
    margin-top: 2.6rem !important; margin-bottom: 1.2rem !important;
    padding-top: 1.4rem; border-top: 1px solid {COLORES['linea']};
    display: flex; align-items: center; gap: 0.6rem;
}}
h3::before {{
    content: ""; flex: none; width: 9px; height: 9px; border-radius: 2.5px;
    background: {COLORES['rosa']}; transform: rotate(45deg);
}}

/* ------------------------------------------------------------ kicker (eyebrow) */
.owfit-kicker {{
    display: flex; align-items: center; gap: 0.7rem; margin-bottom: 0.55rem;
}}
.owfit-kicker-badge {{
    display: inline-flex; align-items: center; justify-content: center;
    width: 2.5rem; height: 2.5rem; border-radius: 12px; flex: none;
    background: linear-gradient(135deg, {COLORES['rosa']}, {COLORES['premium']});
    color: #FFFFFF; font-size: 1.2rem; line-height: 1;
    box-shadow: 0 8px 18px {COLORES['rosa']}38;
}}
.owfit-kicker-text {{
    font-size: 0.72rem; font-weight: 700; letter-spacing: 0.16em; text-transform: uppercase;
    color: {COLORES['gris']};
}}

.marca-titulo {{
    font-family: 'Fraunces', serif; font-size: 1.5rem; font-weight: 560; letter-spacing: 0.1em;
    color: #FFFFFF; margin-bottom: 0.1rem;
}}
.marca-sub {{ font-size: 0.76rem; color: #C9B9BC; letter-spacing: 0.05em; }}

/* ------------------------------------------------------------ sidebar */
section[data-testid="stSidebar"] {{
    background: {COLORES['tinta']};
    border-right: none;
}}
section[data-testid="stSidebar"] * {{ color: #EDEAE6; }}
section[data-testid="stSidebar"] .stRadio label {{ font-size: 0.95rem; }}

section[data-testid="stSidebar"] [data-testid="stRadio"] label {{
    padding: 0.58rem 0.75rem;
    margin-bottom: 0.18rem;
    border-radius: 9px;
    transition: background .15s ease, transform .15s ease;
}}
section[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {{
    background: rgba(255,255,255,0.09);
    transform: translateX(2px);
}}
section[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {{
    background: linear-gradient(90deg, {COLORES['rosa']}55, {COLORES['rosa']}14);
    font-weight: 700;
    box-shadow: inset 3px 0 0 {COLORES['rosa']};
}}

section[data-testid="stSidebar"] button,
section[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"] {{
    background: rgba(255,255,255,0.10);
    border: 1px solid rgba(255,255,255,0.28);
    color: #F2F0EE;
    font-weight: 500;
    transition: background .15s ease, border-color .15s ease;
}}
section[data-testid="stSidebar"] button:hover {{
    background: rgba(255,255,255,0.18);
    border-color: {COLORES['rosa']};
    color: #FFFFFF;
}}
section[data-testid="stSidebar"] summary,
section[data-testid="stSidebar"] [data-testid="stExpander"] summary {{
    color: #F2F0EE;
    font-weight: 600;
    background: rgba(255,255,255,0.06);
    border-radius: 4px;
}}
section[data-testid="stSidebar"] [data-testid="stExpander"] details {{
    border-color: rgba(255,255,255,0.24);
}}
section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {{
    background: rgba(255,255,255,0.06);
    border: 1px dashed rgba(255,255,255,0.32);
}}
section[data-testid="stSidebar"] input,
section[data-testid="stSidebar"] [data-baseweb="select"] > div {{
    background: rgba(255,255,255,0.09);
    border-color: rgba(255,255,255,0.22);
    color: #F2F0EE;
}}
section[data-testid="stSidebar"] [data-testid="stMultiSelect"] span {{
    color: {COLORES['tinta']};
}}
section[data-testid="stSidebar"] hr {{ border-color: rgba(255,255,255,0.16); }}

/* acento sutil en sliders / checkboxes / radios nativos */
input[type="range"], input[type="checkbox"] {{ accent-color: {COLORES['rosa']}; }}

/* ------------------------------------------------------------ KPI cards */
.kpi {{
    position: relative;
    background: #FFFFFF;
    border: 1px solid {COLORES['linea']};
    border-radius: 16px;
    padding: 1.2rem 1.3rem 1.25rem 1.3rem;
    height: 100%;
    box-shadow: 0 2px 6px rgba(34,30,26,0.06);
    transition: transform .2s cubic-bezier(.2,.8,.2,1), box-shadow .2s ease, border-color .2s ease;
    animation: owfit-fade-up .45s ease both;
    overflow: hidden;
}}
.kpi::before {{
    content: ""; position: absolute; top: 0; left: 0; right: 0; height: 4px;
    background: {COLORES['linea']};
}}
.kpi.acento::before {{ background: linear-gradient(90deg, {COLORES['rosa']}, {COLORES['premium']}); }}
.kpi:hover {{
    transform: translateY(-5px);
    box-shadow: 0 16px 32px rgba(34,30,26,0.13);
    border-color: {COLORES['rosa']}44;
}}
.kpi .cabecera {{ display: flex; align-items: flex-start; justify-content: space-between; gap: 0.6rem; }}
.kpi .icono-badge {{
    flex: none; display: inline-flex; align-items: center; justify-content: center;
    width: 2.15rem; height: 2.15rem; border-radius: 9px;
    background: {COLORES['arena']}; color: {COLORES['rosa']};
}}
.kpi.tono-ok .icono-badge {{ background: {COLORES['musgo']}17; color: {COLORES['musgo']}; }}
.kpi.tono-alerta .icono-badge {{ background: {COLORES['negativo']}17; color: {COLORES['negativo']}; }}
.kpi.tono-acento .icono-badge {{ background: {COLORES['rosa']}17; color: {COLORES['rosa']}; }}
.kpi .etiqueta {{
    font-size: 0.68rem; color: {COLORES['gris']}; font-weight: 700;
    letter-spacing: 0.06em; line-height: 1.25; margin-bottom: 0.5rem;
    text-transform: uppercase;
}}
.kpi .valor {{
    font-family: 'Fraunces', 'Inter Tight', serif;
    font-size: 2.05rem; font-weight: 580; color: {COLORES['tinta']};
    line-height: 1.08; letter-spacing: -0.01em;
    font-feature-settings: 'tnum' 1;
}}
.kpi .nota {{ font-size: 0.73rem; color: {COLORES['gris']}; margin-top: 0.45rem; line-height: 1.4; }}
.kpi .delta-pos {{ font-size: 0.79rem; color: {COLORES['musgo']}; font-weight: 700; margin-top: 0.2rem; }}
.kpi .delta-neg {{ font-size: 0.79rem; color: {COLORES['negativo']}; font-weight: 700; margin-top: 0.2rem; }}

[data-testid="stHorizontalBlock"] > div:nth-child(1) .kpi {{ animation-delay: 0s; }}
[data-testid="stHorizontalBlock"] > div:nth-child(2) .kpi {{ animation-delay: .05s; }}
[data-testid="stHorizontalBlock"] > div:nth-child(3) .kpi {{ animation-delay: .10s; }}
[data-testid="stHorizontalBlock"] > div:nth-child(4) .kpi {{ animation-delay: .15s; }}
[data-testid="stHorizontalBlock"] > div:nth-child(5) .kpi {{ animation-delay: .20s; }}

@keyframes owfit-fade-up {{
    from {{ opacity: 0; transform: translateY(6px); }}
    to   {{ opacity: 1; transform: translateY(0); }}
}}

/* ------------------------------------------------------------ banners */
.cinta-demo {{
    background: {COLORES['arena']};
    border: 1px solid {COLORES['linea']};
    border-left: 3px solid {COLORES['ocre']};
    padding: 0.55rem 0.85rem; border-radius: 7px;
    font-size: 0.8rem; color: #4A4026; margin-bottom: 0.9rem;
}}
.cinta-real {{
    background: #EFF3F0;
    border: 1px solid {COLORES['linea']};
    border-left: 3px solid {COLORES['musgo']};
    padding: 0.55rem 0.85rem; border-radius: 7px;
    font-size: 0.8rem; color: {COLORES['musgo']}; margin-bottom: 0.9rem;
}}
.nota-fuente {{
    font-size: 0.75rem; color: {COLORES['gris']};
    border-top: 1px solid {COLORES['linea']}; padding-top: 0.45rem; margin-top: 0.45rem;
}}
/* pie de página global: letra chica, discreto, una sola vez por vista */
.owfit-pie {{
    font-size: 0.72rem; color: {COLORES['gris']}; line-height: 1.4;
    border-top: 1px solid {COLORES['linea']};
    padding-top: 0.7rem; margin-top: 3rem;
}}

/* ------------------------------------------------------------ hallazgos */
.hallazgo {{
    background: #FFFFFF; border: 1px solid {COLORES['linea']};
    border-left: 3px solid {COLORES['musgo']};
    padding: 0.7rem 0.9rem; border-radius: 8px; margin-bottom: 0.55rem;
    font-size: 0.9rem; line-height: 1.45; color: {COLORES['tinta']};
    display: flex; align-items: flex-start; gap: 0.55rem;
    box-shadow: 0 1px 2px rgba(34,30,26,0.04);
    transition: box-shadow .15s ease;
}}
.hallazgo:hover {{ box-shadow: 0 4px 14px rgba(34,30,26,0.08); }}
.hallazgo .owfit-ico {{ flex: none; margin-top: 0.1rem; color: {COLORES['musgo']}; }}
.hallazgo.alerta {{ border-left-color: {COLORES['negativo']}; }}
.hallazgo.alerta .owfit-ico {{ color: {COLORES['negativo']}; }}
.hallazgo.advertencia {{ border-left-color: {COLORES['ocre']}; }}
.hallazgo.advertencia .owfit-ico {{ color: {COLORES['ocre']}; }}
.hallazgo.neutro {{ border-left-color: {COLORES['gris']}; }}
.hallazgo.neutro .owfit-ico {{ color: {COLORES['gris']}; }}
.hallazgo b {{ color: {COLORES['tinta']}; }}
.hallazgo .owfit-texto {{ flex: 1; }}

/* alertas comerciales de temporada (Escenarios): mismo contenedor que un
   hallazgo, con una rejilla compacta de cifras debajo del título. No es un
   componente nuevo, es el hallazgo con más densidad de datos. */
.promo-cab {{ font-weight: 700; }}
.promo-cab .periodo {{ font-weight: 500; color: {COLORES['gris']}; }}
.promo-detalle {{
    display: flex; flex-wrap: wrap; gap: 0.1rem 1.1rem; margin-top: 0.35rem;
    font-size: 0.83rem; line-height: 1.5;
}}
.promo-detalle .etq {{ color: {COLORES['gris']}; }}
.promo-detalle .val {{ font-weight: 600; }}
.promo-motivo {{ font-size: 0.75rem; color: {COLORES['gris']}; margin-top: 0.35rem; }}

div[data-testid="stMetricValue"] {{ font-size: 1.4rem; }}
.stTabs [data-baseweb="tab"] {{ font-size: 0.9rem; color: {COLORES['gris']}; }}
.stTabs [aria-selected="true"] {{ color: {COLORES['tinta']} !important; font-weight: 600; }}
.stTabs [data-baseweb="tab-highlight"] {{ background-color: {COLORES['rosa']} !important; }}
hr {{ border-color: {COLORES['linea']}; }}

/* tablas: encabezado y bordes ya se ajustan de forma centralizada en
   .streamlit/config.toml (theme.dataframeHeaderBackgroundColor / borderColor) */
[data-testid="stDataFrame"] {{
    border: 1px solid {COLORES['linea']}; border-radius: 8px; overflow: hidden;
    transition: box-shadow .18s ease;
}}
[data-testid="stDataFrame"]:hover {{ box-shadow: 0 6px 18px rgba(34,30,26,0.07); }}

/* reveal suave del contenido principal al cargar/re-ejecutar la página */
.main [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"] {{
    animation: owfit-fade-up .3s ease both;
}}

/* accesibilidad: quien pide menos movimiento en el sistema operativo no
   debería recibir fade-ins, dibujos SVG ni el carrusel de packaging en
   loop. Se colapsan a su estado final en vez de desactivarse a medias. */
@media (prefers-reduced-motion: reduce) {{
    *, *::before, *::after {{
        animation-duration: 0.001ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.001ms !important;
        scroll-behavior: auto !important;
    }}
}}
</style>
"""


def aplicar_tema():
    st.markdown(CSS, unsafe_allow_html=True)


# --------------------------------------------------------------- iconos SVG
_ICONOS_SVG = {
    "ok": (
        '<svg class="owfit-ico" width="16" height="16" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M20 6 9 17l-5-5"/></svg>'
    ),
    "alerta": (
        '<svg class="owfit-ico" width="16" height="16" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M12 9v4M12 17h.01"/>'
        '<path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z"/>'
        "</svg>"
    ),
    "advertencia": (
        '<svg class="owfit-ico" width="16" height="16" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M12 9v4M12 17h.01"/><circle cx="12" cy="12" r="9"/></svg>'
    ),
    "neutro": (
        '<svg class="owfit-ico" width="16" height="16" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<circle cx="12" cy="12" r="9"/><path d="M12 16v-5M12 8h.01"/></svg>'
    ),
}

# Iconos para el badge de las tarjetas KPI (mismo lenguaje visual: trazo,
# sin relleno, 18px). Selección deliberadamente corta: solo se usan en las
# métricas más destacadas de cada página, no en todas.
_ICONOS_KPI = {
    "dinero": (
        '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<circle cx="12" cy="12" r="9"/><path d="M12 7v10M9.5 9.5c0-1.1 1.12-2 2.5-2s2.5.9 2.5 2-1.12 2-2.5 2'
        '-2.5.9-2.5 2 1.12 2 2.5 2 2.5-.9 2.5-2"/></svg>'
    ),
    "porcentaje": (
        '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M19 5 5 19"/><circle cx="7" cy="7" r="2.5"/><circle cx="17" cy="17" r="2.5"/></svg>'
    ),
    "tendencia": (
        '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M3 17l6-6 4 4 8-8"/><path d="M15 7h6v6"/></svg>'
    ),
    "meta": (
        '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/></svg>'
    ),
    "paquete": (
        '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M21 8 12 3 3 8v8l9 5 9-5Z"/><path d="M3 8l9 5 9-5M12 13v8"/></svg>'
    ),
    "usuarios": (
        '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<circle cx="9" cy="8" r="3.2"/><path d="M2.5 20c0-3.5 3-6 6.5-6s6.5 2.5 6.5 6"/>'
        '<circle cx="17.5" cy="8.5" r="2.6"/><path d="M15.5 14.3c2.7.4 4.9 2.5 5 5.7"/></svg>'
    ),
    "calendario": (
        '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<rect x="3.5" y="5" width="17" height="16" rx="2"/><path d="M8 3v4M16 3v4M3.5 10h17"/></svg>'
    ),
    "escala": (
        '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M4 20h16M7 20V10M12 20V4M17 20v13"/></svg>'
    ),
    "alerta": _ICONOS_SVG["alerta"]
    .replace('width="16" height="16"', 'width="18" height="18"')
    .replace(' class="owfit-ico"', ""),
}


def kicker(pagina: str):
    """Franja superior de cada vista: icono de la sección + texto pequeño de
    marca, encima del st.title(). Refuerza identidad sin tocar el h1 en sí,
    para no romper el ajuste de espaciado entre h1 y st.caption."""
    icono = ICONOS_NAV.get(pagina, "○")
    st.markdown(
        f'<div class="owfit-kicker"><span class="owfit-kicker-badge">{icono}</span>'
        f'<span class="owfit-kicker-text">OWFIT · Pricing Intelligence</span></div>',
        unsafe_allow_html=True,
    )


def kpi(
    etiqueta: str,
    valor: str,
    delta: str | None = None,
    positivo: bool | None = None,
    nota: str | None = None,
    acento: bool = False,
    icono: str | None = None,
):
    """Tarjeta KPI. `icono` es opcional (clave de _ICONOS_KPI, p.ej. 'dinero',
    'porcentaje', 'tendencia', 'meta', 'paquete', 'usuarios', 'calendario',
    'escala', 'alerta'): se usa solo en las métricas más destacadas de cada
    página, no en todas, para que el acento visual siga significando algo."""
    clase_delta = "delta-pos" if positivo else "delta-neg"
    tono = (
        "tono-acento"
        if acento
        else ("tono-ok" if positivo else ("tono-alerta" if positivo is False else ""))
    )
    clases = " ".join(c for c in ["kpi", "acento" if acento else "", tono] if c)
    html = f'<div class="{clases}">'
    html += '<div class="cabecera">'
    html += f'<div class="etiqueta">{etiqueta}</div>'
    if icono and icono in _ICONOS_KPI:
        html += f'<span class="icono-badge">{_ICONOS_KPI[icono]}</span>'
    html += "</div>"
    html += f'<div class="valor">{valor}</div>'
    if delta:
        html += f'<div class="{clase_delta}">{delta}</div>'
    if nota:
        html += f'<div class="nota">{nota}</div>'
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def fila_kpis(items: list[dict]):
    cols = st.columns(len(items))
    for c, it in zip(cols, items):
        with c:
            kpi(**it)


def hallazgo(texto: str, tipo: str = "ok"):
    clase = {
        "ok": "",
        "alerta": " alerta",
        "advertencia": " advertencia",
        "neutro": " neutro",
    }.get(tipo, "")
    icono = _ICONOS_SVG.get(tipo, _ICONOS_SVG["ok"])
    st.markdown(
        f'<div class="hallazgo{clase}">{icono}<div class="owfit-texto">{texto}</div></div>',
        unsafe_allow_html=True,
    )


def alerta_promo(
    titulo: str,
    periodo: str,
    detalles: list[tuple[str, str]],
    motivo: str | None = None,
    tipo: str = "advertencia",
):
    """Alerta comercial de un periodo: título, periodo, cifras y el porqué.

    Reutiliza el contenedor y los tonos de `hallazgo` (ok / advertencia /
    alerta) para que una promoción profunda se lea con el mismo semáforo que
    el resto del dashboard, en vez de introducir otro lenguaje visual.
    """
    clase = {
        "ok": "",
        "alerta": " alerta",
        "advertencia": " advertencia",
        "neutro": " neutro",
    }.get(tipo, "")
    icono = _ICONOS_SVG.get(tipo, _ICONOS_SVG["ok"])
    cifras = "".join(
        f'<span><span class="etq">{etq}:</span> <span class="val">{val}</span></span>'
        for etq, val in detalles
    )
    html = (
        f'<div class="hallazgo{clase}">{icono}<div class="owfit-texto">'
        f'<div class="promo-cab">{titulo} <span class="periodo">· {periodo}</span></div>'
        f'<div class="promo-detalle">{cifras}</div>'
        + (f'<div class="promo-motivo">{motivo}</div>' if motivo else "")
        + "</div></div>"
    )
    st.markdown(html, unsafe_allow_html=True)


def cinta_origen(es_demo: bool, nombre: str | None = None):
    if es_demo:
        st.markdown(
            '<div class="cinta-demo"><b>DATOS DE DEMOSTRACIÓN — NO SON DATOS REALES DE OWFIT.</b> '
            "Las cifras internas (PVP, COGS, cantidades) son inventadas y sirven solo para probar "
            "el dashboard. Cargue el archivo interno de OWFIT en la barra lateral para trabajar "
            "con cifras reales.</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="cinta-real">Datos internos cargados desde <b>{nombre or "archivo del usuario"}</b>. '
            "Se procesan en memoria durante la sesión y no se guardan en el proyecto.</div>",
            unsafe_allow_html=True,
        )


def nota_fuente(texto: str):
    st.markdown(f'<div class="nota-fuente">{texto}</div>', unsafe_allow_html=True)


def pie_muestra(n_respuestas: int):
    """Pie de página global con el alcance de la encuesta. Se renderiza una
    sola vez por vista (desde app.py) para que el disclaimer no se repita como
    bullet dentro de cada sección. Sin respuestas cargadas, no se escribe nada:
    la línea se omite antes que quedar con un número vacío."""
    if not n_respuestas:
        return
    st.markdown(
        f'<div class="owfit-pie">Muestra de {n_respuestas} respuestas por conveniencia: '
        "lectura direccional del consumidor, no estimación de la demanda del mercado.</div>",
        unsafe_allow_html=True,
    )


def mostrar_validacion(
    res, titulo: str = "Validación de datos", expandido: bool = False
):
    """Muestra errores, avisos y notas de un ResultadoValidacion."""
    if res is None:
        return
    if res.errores:
        for e in res.errores:
            st.error(e)
    if res.avisos or res.notas:
        n = len(res.avisos) + len(res.notas)
        with st.expander(f"{titulo} · {n} observación(es)", expanded=expandido):
            for a in res.avisos:
                st.warning(a)
            for n_ in res.notas:
                st.caption(n_)


def sin_datos(mensaje: str):
    st.info(mensaje)


def signo(valor, invertir: bool = False) -> bool:
    if valor is None or (isinstance(valor, float) and np.isnan(valor)):
        return True
    return (valor < 0) if invertir else (valor > 0)


# --------------------------------------------------------- price target
def precio_target(
    precio_actual: float,
    precio_recomendado: float,
    p25: float | None = None,
    p50: float | None = None,
    p75: float | None = None,
    titulo: str = "Posición del precio",
):
    """Barra tipo 'target': dónde cae el precio actual frente al rango
    competitivo ya calculado (P25–P75) y frente al precio recomendado.

    No calcula nada nuevo: solo distribuye visualmente los valores que la
    página ya trae calculados (percentiles de mercado y precio recomendado).
    El semáforo es una lectura visual de esos mismos números, no una regla de
    pricing adicional.
    """
    valores = [
        v
        for v in [precio_actual, precio_recomendado, p25, p50, p75]
        if v is not None and np.isfinite(v)
    ]
    if not valores:
        sin_datos("Sin valores suficientes para ubicar el precio.")
        return

    lo = min(valores) * 0.92
    hi = max(valores) * 1.08
    rango = max(hi - lo, 1e-6)

    def ubicar(v):
        return max(0.0, min(100.0, (v - lo) / rango * 100))

    # semáforo: lectura del precio actual contra el rango competitivo ya
    # calculado (P25-P75). Si no hay rango, no hay semáforo.
    estado, texto_estado = None, None
    if (
        p25 is not None
        and p75 is not None
        and np.isfinite(p25)
        and np.isfinite(p75)
        and np.isfinite(precio_actual)
    ):
        ancho = max(p75 - p25, 1e-6)
        if p25 <= precio_actual <= p75:
            estado, texto_estado = COLORES["musgo"], "DENTRO DEL RANGO"
        elif (p25 - ancho * 0.15) <= precio_actual <= (p75 + ancho * 0.15):
            estado, texto_estado = COLORES["ocre"], "LIGERAMENTE FUERA DE RANGO"
        else:
            estado, texto_estado = COLORES["negativo"], "FUERA DE RANGO"

    banda_html = ""
    if p25 is not None and p75 is not None and np.isfinite(p25) and np.isfinite(p75):
        banda_html = (
            f'<div style="position:absolute; left:{ubicar(p25):.2f}%; width:{ubicar(p75) - ubicar(p25):.2f}%; '
            f'top:0; bottom:0; background:{COLORES["salvia"]}26; border-radius:4px;"></div>'
        )

    p50_html = ""
    if p50 is not None and np.isfinite(p50):
        p50_html = (
            f'<div style="position:absolute; left:{ubicar(p50):.2f}%; top:-4px; bottom:-4px; width:1px; '
            f'background:{COLORES["gris"]};"></div>'
            f'<div style="position:absolute; left:{ubicar(p50):.2f}%; top:26px; transform:translateX(-50%); '
            f'font-size:0.65rem; color:{COLORES["gris"]}; white-space:nowrap;">Mediana mercado {money(p50)}</div>'
        )

    marcador_actual = ""
    if precio_actual is not None and np.isfinite(precio_actual):
        color_actual = estado or COLORES["tinta"]
        marcador_actual = (
            f'<div style="position:absolute; left:{ubicar(precio_actual):.2f}%; top:50%; '
            f"transform:translate(-50%,-50%) rotate(45deg); width:11px; height:11px; "
            f'background:{color_actual}; border:2px solid #FFFFFF; box-shadow:0 0 0 1px {color_actual};"></div>'
            f'<div style="position:absolute; left:{ubicar(precio_actual):.2f}%; top:-22px; '
            f'transform:translateX(-50%); font-size:0.72rem; font-weight:600; color:{COLORES["tinta"]}; '
            f'white-space:nowrap;">Actual {money(precio_actual)}</div>'
        )

    marcador_rec = ""
    if precio_recomendado is not None and np.isfinite(precio_recomendado):
        marcador_rec = (
            f'<div style="position:absolute; left:{ubicar(precio_recomendado):.2f}%; top:50%; '
            f"transform:translate(-50%,-50%); width:14px; height:14px; border-radius:50%; "
            f'background:{COLORES["rosa"]}; border:2px solid #FFFFFF; box-shadow:0 0 0 1px {COLORES["rosa"]};"></div>'
            f'<div style="position:absolute; left:{ubicar(precio_recomendado):.2f}%; top:26px; '
            f'transform:translateX(-50%); font-size:0.72rem; font-weight:600; color:{COLORES["rosa"]}; '
            f'white-space:nowrap;">Recomendado {money(precio_recomendado)}</div>'
        )

    badge_html = ""
    if estado and texto_estado:
        badge_html = (
            f'<span style="display:inline-flex; align-items:center; gap:0.4rem; background:{estado}14; '
            f"color:{estado}; font-size:0.7rem; font-weight:700; letter-spacing:0.04em; "
            f'padding:0.25rem 0.6rem; border-radius:999px; border:1px solid {estado}44;">'
            f'<span style="width:7px; height:7px; border-radius:50%; background:{estado};"></span>'
            f"{texto_estado}</span>"
        )

    st.markdown(
        f"""
        <div style="background:#FFFFFF; border:1px solid {COLORES['linea']}; border-radius:10px;
                    padding:1.4rem 1.3rem 2.6rem 1.3rem; margin-bottom:0.6rem;
                    box-shadow:0 1px 2px rgba(34,30,26,0.05);">
            <div style="display:flex; justify-content:space-between; align-items:center;
                        margin-bottom:1.6rem;">
                <span style="font-size:0.78rem; font-weight:600; letter-spacing:0.05em;
                             color:{COLORES['gris']}; text-transform:uppercase;">{titulo}</span>
                {badge_html}
            </div>
            <div style="position:relative; height:8px; background:{COLORES['arena']};
                        border-radius:4px; margin:0 6px;">
                {banda_html}
                {p50_html}
                {marcador_actual}
                {marcador_rec}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# --------------------------------------------------------- brote interactivo
# Centros (x, y en px) de cada pétalo ya rotado, medidos con el propio
# navegador (no a mano): la <svg> de 120x180 queda centrada dentro de una
# tarjeta de _TARJETA_ANCHO de ancho, así que cada centro ya incluye ese
# desplazamiento de centrado (60px) más el margen superior de la tarjeta
# (9px). Sirven para poner un botón invisible de Streamlit exactamente
# encima de cada pétalo dibujado más abajo, dentro de la MISMA tarjeta de
# ancho fijo (fijar el ancho evita que un sidebar más angosto o más ancho
# desincronice estas coordenadas, ya calibradas para 240px).
_TARJETA_ANCHO = 240  # px
_PETALO_ANGULOS = [0, 72, 144, 216, 288]
_PETALO_POS_PX = [
    (120.0, 36.6),
    (136.0, 48.2),
    (129.9, 67.0),
    (110.1, 67.0),
    (104.0, 48.2),
]
_BOTON_LADO = 24  # px


def flor_interactiva(
    etapas: list[str] | None = None, key: str = "flor"
) -> tuple[bool, int]:
    """La flor de la barra lateral, ahora con los propios pétalos clickeables
    (nada de un botón aparte): cada pétalo es un botón de Streamlit invisible
    superpuesto justo encima del pétalo dibujado en el SVG, del mismo tamaño
    y en la misma posición. Al hacer clic, ESE pétalo desaparece para
    siempre y su etapa correspondiente se tacha en la lista de abajo -cada
    pétalo "es" una de las etapas del análisis-. Al quitar el último, la
    planta se marchita (se dobla y se seca de color) y la función devuelve
    `recien_pelada=True` esa sola vez para que quien la llama suelte el
    archivo cargado.

    Solo debe llamarse cuando ya hay un archivo cargado (no antes: con datos
    de demostración no hay nada que "analizar" ni que deshojar).

    Devuelve (recien_pelada, restantes).
    """
    etapas = etapas or [
        "Archivo",
        "Mercado",
        "Consumidor",
        "Costos",
        "Precio recomendado",
    ]
    state_key = f"_{key}_petalos"
    if state_key not in st.session_state or len(st.session_state[state_key]) != 5:
        st.session_state[state_key] = [True] * 5
    activos: list[bool] = st.session_state[state_key]

    # Ocho espacios al inicio de cada línea: deben igualar la indentación del
    # resto del bloque <style> más abajo. Streamlit "dedenta" el bloque de
    # markdown completo según la indentación MÍNIMA común a todas sus líneas;
    # una sola línea sin indentar (0 espacios) rompe ese cálculo para el resto
    # del bloque y hace que se renderice como bloque de código en vez de HTML.
    posiciones_css = "\n".join(
        f"        .st-key-owfit_{key}_ctn > "
        f'div[data-testid="stElementContainer"]:nth-child({i + 2}) {{ '
        f"left:{x - _BOTON_LADO / 2:.1f}px; top:{y - _BOTON_LADO / 2:.1f}px; }}"
        for i, (x, y) in enumerate(_PETALO_POS_PX)
    )

    cont = st.container(key=f"owfit_{key}_ctn")
    with cont:
        # El marcador se crea AHORA (para que ocupe el primer lugar en el
        # DOM, del que depende el CSS de más abajo) pero se llena DESPUÉS de
        # procesar el clic de este mismo rerun: así el SVG que se dibuja ya
        # refleja el pétalo recién quitado, en vez de ir siempre un clic
        # atrás.
        marcador = st.empty()

        clicked = None
        for i in range(5):
            if st.button(
                "​", key=f"owfit_{key}_petalo_{i + 1}", disabled=not activos[i]
            ):
                clicked = i

        recien_pelada = False
        if clicked is not None and activos[clicked]:
            activos[clicked] = False
            st.session_state[state_key] = activos
            if sum(activos) == 0:
                recien_pelada = True

        petalos_svg = "".join(
            f'<g transform="rotate({ang} 50 42)"><ellipse class="owfit-petalo p{i + 1}" cx="50" cy="28" rx="6.5" ry="15"/></g>'
            for i, ang in enumerate(_PETALO_ANGULOS)
            if activos[i]
        )
        restantes = sum(activos)
        centro_svg = (
            '<circle class="owfit-centro" cx="50" cy="42" r="5"/>'
            if restantes > 0
            else ""
        )
        marchita = restantes == 0
        titulo = (
            "Analizando tu archivo" if not marchita else "Pelona… se fue el archivo"
        )
        filas = "".join(
            f'<div class="owfit-etapa{"" if activos[i] else " hecha"}" '
            f'style="animation-delay:{0.30 + i * 0.18:.2f}s">'
            f'<span class="owfit-punto"></span><span>{e}</span></div>'
            for i, e in enumerate(etapas)
        )

        marcador.markdown(
            f"""
        <style>
        .owfit-brote {{
            display:flex; flex-direction:column; align-items:center;
            background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.14);
            border-radius:12px; padding:0; margin:0.5rem 0 0.85rem; overflow:hidden;
        }}
        .owfit-brote svg {{ display:block; }}
        .owfit-brote-titulo {{
            font-size:0.65rem; font-weight:700; letter-spacing:0.08em; text-transform:uppercase;
            color:#B9B2A9; margin:0.3rem 0 0;
        }}
        .owfit-etapas {{ display:flex; flex-direction:column; align-items:center; gap:0.24rem;
            margin:0.35rem 0 0.85rem; }}
        .owfit-etapa {{
            display:flex; align-items:center; gap:0.4rem; font-size:0.7rem;
            color:#A79F95; font-weight:500; letter-spacing:0.01em;
            opacity:0; animation: owfit-etapa-in .5s ease forwards;
            transition: opacity .4s ease, text-decoration-color .4s ease;
        }}
        .owfit-etapa:last-child {{ color:#FFFFFF; font-weight:700; }}
        .owfit-etapa.hecha {{ opacity:.4 !important; text-decoration: line-through; }}
        .owfit-punto {{
            width:4px; height:4px; border-radius:50%; background:rgba(255,255,255,0.22); flex:none;
        }}
        .owfit-etapa:last-child .owfit-punto {{ background:{COLORES['rosa']}; }}
        @keyframes owfit-etapa-in {{
            from {{ opacity:0; transform:translateY(-3px); }}
            to   {{ opacity:1; transform:translateY(0); }}
        }}
        .owfit-planta {{ transform-box: fill-box; transform-origin: 50% 100%; }}
        .owfit-tallo {{
            stroke:{COLORES['salvia']}; stroke-width:2.4; fill:none; stroke-linecap:round;
            stroke-dasharray:140; stroke-dashoffset:140;
            animation: owfit-dibujar 1.1s .2s ease forwards;
            transition: stroke 1s ease;
        }}
        .owfit-hoja {{
            fill:{COLORES['salvia']}; opacity:0; transform-origin:center;
            animation: owfit-hoja-in .55s ease forwards;
            transition: fill 1s ease;
        }}
        .owfit-hoja.i1 {{ animation-delay: .85s; }}
        .owfit-hoja.i2 {{ animation-delay: 1.0s; }}
        .owfit-raiz {{
            stroke:{COLORES['salvia']}; stroke-width:1.5; fill:none; stroke-linecap:round;
            opacity:0; animation: owfit-hoja-in .5s .95s ease forwards;
        }}
        .owfit-suelo {{ fill:rgba(255,255,255,0.07); }}
        .owfit-petalo {{
            fill:{COLORES['rosa']}; opacity:0; transform-origin:50px 42px;
            animation: owfit-petalo-in .45s ease forwards;
        }}
        .owfit-petalo.p1 {{ animation-delay: 1.3s; }}
        .owfit-petalo.p2 {{ animation-delay: 1.4s; }}
        .owfit-petalo.p3 {{ animation-delay: 1.5s; }}
        .owfit-petalo.p4 {{ animation-delay: 1.6s; }}
        .owfit-petalo.p5 {{ animation-delay: 1.7s; }}
        .owfit-centro {{
            fill:{COLORES['ocre']}; opacity:0; transform-origin:50px 42px;
            animation: owfit-centro-in .4s 1.85s ease forwards;
        }}
        .owfit-semilla {{
            fill:{COLORES['ocre']}; opacity:0;
            animation: owfit-hoja-in .4s ease forwards;
        }}
        @keyframes owfit-dibujar {{ to {{ stroke-dashoffset:0; }} }}
        @keyframes owfit-hoja-in {{
            from {{ opacity:0; transform:scale(.4); }}
            to   {{ opacity:1; transform:scale(1); }}
        }}
        @keyframes owfit-petalo-in {{
            from {{ opacity:0; transform:scale(.3); }}
            to   {{ opacity:.95; transform:scale(1); }}
        }}
        @keyframes owfit-centro-in {{
            from {{ opacity:0; transform:scale(0); }}
            to   {{ opacity:1; transform:scale(1); }}
        }}
        /* marchita: la planta se dobla y se seca en cuanto se va el último pétalo */
        .owfit-marchita .owfit-planta {{ animation: owfit-marchitar 1.1s ease forwards; }}
        .owfit-marchita .owfit-tallo {{ stroke:#8A6F45; }}
        .owfit-marchita .owfit-hoja {{ fill:#8A6F45; }}
        @keyframes owfit-marchitar {{
            from {{ transform: rotate(0deg); }}
            to   {{ transform: rotate(13deg); }}
        }}
        /* botones-pétalo: los widgets reales de Streamlit se superponen,
           invisibles, justo encima de cada pétalo del SVG de abajo */
        .st-key-owfit_{key}_ctn {{
            position: relative; gap: 0 !important; margin-bottom: 0.5rem;
            width: {_TARJETA_ANCHO}px;
        }}
        .st-key-owfit_{key}_ctn > div[data-testid="stElementContainer"]:nth-child(n+2) {{
            position: absolute; width:{_BOTON_LADO}px; height:{_BOTON_LADO}px; z-index: 5;
        }}
        {posiciones_css}
        .st-key-owfit_{key}_ctn > div[data-testid="stElementContainer"]:nth-child(n+2) button {{
            width:100%; height:100%; min-height:0; padding:0; margin:0; border:none;
            background:transparent; box-shadow:none; border-radius:50%; cursor:pointer;
        }}
        .st-key-owfit_{key}_ctn > div[data-testid="stElementContainer"]:nth-child(n+2) button:hover {{
            background: rgba(255,255,255,0.10);
        }}
        .st-key-owfit_{key}_ctn > div[data-testid="stElementContainer"]:nth-child(n+2) button:disabled {{
            cursor: default;
        }}
        .st-key-owfit_{key}_ctn > div[data-testid="stElementContainer"]:nth-child(n+2) button p {{
            display:none;
        }}
        </style>
        <div class="owfit-brote{' owfit-marchita' if marchita else ''}">
            <svg width="120" height="180" viewBox="0 0 100 150">
                <g class="owfit-planta">
                    <ellipse class="owfit-suelo" cx="50" cy="143" rx="13" ry="3"/>
                    <path class="owfit-raiz" d="M50,139 C46,143 42,146 37,148"/>
                    <path class="owfit-raiz" d="M50,139 C54,143 58,146 63,148"/>
                    <ellipse class="owfit-semilla" cx="50" cy="140" rx="4.2" ry="3.2"/>
                    <path class="owfit-tallo" d="M50,140 C48,120 52,102 50,82 C48,68 52,58 50,45"/>
                    <!-- Un elemento con animación CSS de "transform" (scale/translate) reemplaza
                         por completo el atributo SVG transform="rotate(...)" del mismo elemento
                         (así lo define CSS Transforms sobre SVG). Por eso la rotación estática de
                         hojas y pétalos vive en un <g> envolvente que la CSS nunca toca: adentro,
                         el elemento solo escala/aparece en su propio sistema de coordenadas. -->
                    <g transform="rotate(-24 34 103)"><ellipse class="owfit-hoja i1" cx="34" cy="103" rx="12" ry="6"/></g>
                    <g transform="rotate(24 66 88)"><ellipse class="owfit-hoja i2" cx="66" cy="88" rx="12" ry="6"/></g>
                    <g>{petalos_svg}{centro_svg}</g>
                </g>
            </svg>
            <div class="owfit-brote-titulo">{titulo}</div>
            <div class="owfit-etapas">{filas}</div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    return recien_pelada, restantes


# --------------------------------------------------------- identidad packaging
def icono_packaging(texto: str | None = None):
    """Ilustración mínima de una caja que se 'abre' una sola vez al cargar la
    página: identidad visual propia para el módulo de Packaging. Solo SVG/CSS,
    sin animación ligada a los controles (evita recalcular nada extra).

    `texto` es la línea que acompaña al icono y debe venir armada con las cifras
    del escenario. Si no se pasa nada, el icono va solo: antes había aquí una
    frase genérica que repetía el caption del título, y se eliminó."""
    leyenda = (
        f'<span style="font-size:0.9rem; color:{COLORES["tinta"]}; max-width:46rem; '
        f'line-height:1.5;">{texto}</span>'
        if texto
        else ""
    )
    st.markdown(
        f"""
        <style>
        .owfit-caja-wrap {{ display:flex; align-items:center; gap:1rem; margin-bottom:0.3rem; }}
        .owfit-tapa {{
            transform-origin: 8px 40px; animation: owfit-tapa-abre 1s .2s cubic-bezier(.34,1.56,.64,1) forwards;
        }}
        .owfit-listón {{ opacity:0; animation: owfit-listón-in .5s .9s ease forwards; }}
        @keyframes owfit-tapa-abre {{
            from {{ transform: rotate(0deg); }}
            to   {{ transform: rotate(-35deg); }}
        }}
        @keyframes owfit-listón-in {{
            from {{ opacity:0; }}
            to   {{ opacity:1; }}
        }}
        </style>
        <div class="owfit-caja-wrap">
            <svg width="56" height="56" viewBox="0 0 64 64">
                <rect x="10" y="26" width="44" height="30" rx="2" fill="none"
                      stroke="{COLORES['musgo']}" stroke-width="2.2"/>
                <line x1="10" y1="38" x2="54" y2="38" stroke="{COLORES['linea']}" stroke-width="1.4"/>
                <rect class="owfit-listón" x="30" y="26" width="4" height="30" fill="{COLORES['rosa']}"/>
                <path class="owfit-tapa" d="M8,26 L32,26 L56,26 L52,16 L12,16 Z" fill="none"
                      stroke="{COLORES['musgo']}" stroke-width="2.2" stroke-linejoin="round"/>
            </svg>
            {leyenda}
        </div>
        """,
        unsafe_allow_html=True,
    )

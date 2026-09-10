"""Packaging premium para conjuntos: escenario actual contra escenario con empaque."""

from __future__ import annotations

import base64
import io
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from config import settings
from src import pricing, ui
from src.ui import COLORES
from src.utils import money, pct

_EXT_FOTO = (".jpg", ".jpeg", ".png", ".webp")


def _fotos(carpeta_rel: str) -> list[Path]:
    """Rutas de imagen de assets/images/<carpeta_rel>, ordenadas por nombre."""
    carpeta = settings.ROOT / "assets" / "images" / carpeta_rel
    if not carpeta.is_dir():
        return []
    return sorted(p for p in carpeta.iterdir() if p.suffix.lower() in _EXT_FOTO)


@st.cache_data(show_spinner=False)
def _data_uri(ruta: str, mtime: float, ancho_max: int = 900) -> str:
    """Imagen lista para incrustar, reducida a `ancho_max` px de ancho y
    cacheada por (ruta, mtime). Los originales pesan ~2 MB cada uno y el HTML
    del carrusel se reenvía entero en cada rerun de la página, así que sin
    reducirlas cada movimiento del slider arrastraría varios MB."""
    datos = Path(ruta).read_bytes()
    try:
        from PIL import Image

        img = Image.open(io.BytesIO(datos))
        if img.width > ancho_max:
            alto = round(img.height * ancho_max / img.width)
            img = img.resize((ancho_max, alto), Image.LANCZOS)
        buf = io.BytesIO()
        img.convert("RGB").save(buf, format="JPEG", quality=82, optimize=True)
        datos, tipo = buf.getvalue(), "jpeg"
    except Exception:  # sin Pillow o formato no soportado: se manda tal cual
        suf = Path(ruta).suffix.lower().lstrip(".")
        tipo = "jpeg" if suf == "jpg" else suf
    return f"data:image/{tipo};base64,{base64.b64encode(datos).decode()}"


def _carrusel_fotos(
    carpeta_rel: str, clave: str, titulo: str | None = None, segundos: int = 6
):
    """Fotos de referencia de una carpeta, en rotación automática.

    Solo lee archivos de assets/images/<carpeta_rel>: no toca datos ni cálculos.
    `clave` da nombres únicos a la clase y a los keyframes, para que dos
    carruseles en la misma página no compartan la animación (cada uno tiene su
    propio número de fotos y por tanto sus propios porcentajes de fade).
    """
    fotos = _fotos(carpeta_rel)
    if not fotos:
        return

    n = len(fotos)
    capas = []
    for i, foto in enumerate(fotos):
        uri = _data_uri(str(foto), foto.stat().st_mtime)
        capas.append(
            f'<img src="{uri}" alt="{foto.stem}" '
            f'style="animation-delay:{-i * segundos}s;" />'
        )

    # Con una sola foto no hay nada que rotar: se deja fija en lugar de
    # dejarla parpadear contra sí misma.
    # Selector compuesto a propósito: cada carrusel reemite las reglas base, y
    # con un solo `.owfit-carrusel-x img` el bloque del segundo pisaría el
    # `opacity: 0` sobre el primero (misma especificidad, gana el último).
    sel = f".owfit-carrusel.owfit-carrusel-{clave} img"
    if n == 1:
        anim = f"{sel} {{ opacity: 1; animation: none; }}"
        keyframes = ""
    else:
        duracion = n * segundos
        borde = min(4.0, 100 / n / 2)
        anim = (
            f"{sel} {{ animation: owfit-fade-{clave} "
            f"{duracion}s infinite ease-in-out; }}"
        )
        keyframes = (
            f"@keyframes owfit-fade-{clave} {{"
            f"0% {{ opacity: 0; }}"
            f"{borde:.2f}% {{ opacity: 1; }}"
            f"{100 / n - borde:.2f}% {{ opacity: 1; }}"
            f"{100 / n:.2f}% {{ opacity: 0; }}"
            f"100% {{ opacity: 0; }}"
            f"}}"
        )

    # Las dos reglas van en una sola línea del bloque: con una sola foto
    # `keyframes` queda vacío y una línea en blanco dentro del f-string rompe
    # el dedent de st.markdown (el HTML terminaría renderizado como texto).
    reglas = f"{anim} {keyframes}".strip()
    rotulo = f'<div class="owfit-carrusel-tit">{titulo}</div>' if titulo else ""
    st.markdown(
        f"""
        <style>
        .owfit-carrusel {{
            position: relative; width: 100%; max-width: 380px; aspect-ratio: 3 / 4;
            margin: 0 auto; border-radius: 10px; overflow: hidden;
            border: 1px solid {COLORES['linea']}; background: {COLORES['arena']};
            box-shadow: 0 1px 3px rgba(22,33,28,0.08);
        }}
        .owfit-carrusel img {{
            position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover;
            opacity: 0;
        }}
        .owfit-carrusel-tit {{
            text-align: center; font-size: 0.65rem; font-weight: 700;
            letter-spacing: 0.08em; text-transform: uppercase;
            color: {COLORES['gris']}; margin-bottom: 0.45rem;
        }}
        {reglas}
        </style>
        {rotulo}
        <div class="owfit-carrusel owfit-carrusel-{clave}">{''.join(capas)}</div>
        """,
        unsafe_allow_html=True,
    )


def render(ctx):
    ui.kicker("Packaging")
    st.title("Packaging para sets")
    ui.cinta_origen(ctx.es_demo, ctx.nombre_archivo)

    cf1, cf2 = st.columns(2)
    with cf1:
        _carrusel_fotos("productsA", "a", "Productos A")
    with cf2:
        _carrusel_fotos("productB", "b", "Productos B")
    st.caption("Packaging de referencia")
    st.markdown("---")

    if not ctx.val_internos.ok or ctx.tabla.empty:
        st.stop()

    t = ctx.tabla
    p = ctx.params

    categorias = sorted(t["Categoría"].dropna().unique().astype(str).tolist())
    default = "Sets/Conjuntos" if "Sets/Conjuntos" in categorias else categorias[0]
    c1, c2, c3 = st.columns([1.4, 1, 1])
    with c1:
        categoria = st.selectbox(
            "Categoría a evaluar", categorias, index=categorias.index(default)
        )
    with c2:
        costo = st.number_input(
            "Costo adicional del packaging ($ por unidad)",
            0.0,
            500.0,
            settings.PACKAGING_DEFAULT["costo_packaging_mxn"],
            5.0,
        )
    with c3:
        incremento = st.slider(
            "Incremento de precio propuesto (%)",
            0.0,
            40.0,
            settings.PACKAGING_DEFAULT["incremento_precio_pct"],
            0.5,
        )

    usar_rec = st.checkbox(
        "Partir del precio recomendado en lugar del precio actual",
        value=False,
        help="Permite evaluar el packaging sobre la estructura de precios que ya se propuso.",
    )

    esc = pricing.escenario_packaging(t, p, costo, incremento, categoria, usar_rec)
    if esc.empty:
        ui.sin_datos(f"No hay productos de '{categoria}' en el archivo interno.")
        return

    # ------------------------------------------------------------- KPIs
    tiene_cantidad = esc["Cantidad"].notna().any()
    w = esc["Cantidad"].fillna(0) if tiene_cantidad else pd.Series(1.0, index=esc.index)

    def prom(col):
        s = esc[col]
        m = s.notna() & (w > 0) if tiene_cantidad else s.notna()
        if not m.any():
            return np.nan
        return (
            float(np.average(s[m], weights=w[m]))
            if tiene_cantidad
            else float(s[m].mean())
        )

    delta_util = prom("Δ Utilidad")
    delta_margen = prom("Δ Margen (pp)")

    # Línea única del módulo, armada con las cifras del escenario. Sustituye a
    # las dos frases genéricas que antes decían lo mismo sin ningún número. Si
    # falta cualquiera de las variables, la línea completa se omite.
    margen_actual = prom("Margen contribución actual %")
    margen_resultante = prom("Margen contribución con packaging %")
    pisos_meta = [
        pricing.precio_piso_por_margen(
            t.loc[t["Producto"] == r["Producto"], "COGS"].iloc[0] + costo, p
        )
        for _, r in esc.iterrows()
        if (t["Producto"] == r["Producto"]).any()
    ]
    pisos_meta = [x for x in pisos_meta if np.isfinite(x)]
    precio_meta = float(np.mean(pisos_meta)) if pisos_meta else np.nan

    if all(
        np.isfinite(v) for v in (costo, margen_actual, margen_resultante, precio_meta)
    ):
        ui.icono_packaging(
            f"Empaque premium para {categoria.lower()}: <b>+{money(costo)}</b> por unidad lleva el "
            f"margen de <b>{pct(margen_actual)}</b> a <b>{pct(margen_resultante)}</b>; requiere subir "
            f"el precio a <b>{money(precio_meta)}</b> para sostener la meta de "
            f"{pct(p.margen_objetivo_pct, 0)}."
        )

    st.markdown("### Escenario actual frente a escenario con packaging premium")
    ui.fila_kpis(
        [
            dict(
                etiqueta="Productos evaluados",
                valor=f"{len(esc)}",
                nota=f"Categoría {categoria}",
            ),
            dict(
                etiqueta="Costo adicional del packaging",
                valor=money(costo),
                nota="Por unidad, se suma al COGS",
            ),
            dict(
                etiqueta="Precio promedio",
                valor=money(prom("Precio con packaging")),
                delta=f"desde {money(prom('Precio actual'))}",
                positivo=True,
                acento=True,
            ),
        ]
    )
    ui.fila_kpis(
        [
            dict(
                etiqueta="Utilidad promedio por unidad",
                valor=money(prom("Utilidad con packaging")),
                delta=f"{'+' if delta_util >= 0 else ''}{money(delta_util)} vs actual",
                positivo=delta_util >= 0,
            ),
            dict(
                etiqueta="Margen de contribución",
                valor=pct(prom("Margen contribución con packaging %")),
                delta=f"{'+' if delta_margen >= 0 else ''}{delta_margen:.1f} pp",
                positivo=delta_margen >= 0,
            ),
        ]
    )

    # ------------------------------------------------------------- veredicto
    if delta_util >= 0 and delta_margen >= 0:
        ui.hallazgo(
            f"Con un incremento de precio de {pct(incremento, 1)}, el packaging de {money(costo)} "
            f"<b>mejora tanto la utilidad por unidad ({money(delta_util)}) como el margen "
            f"({delta_margen:+.1f} pp)</b>. La condición es que el aumento de precio no reduzca la "
            "conversión: eso no se puede verificar con los datos actuales y requiere una prueba real.",
            "ok",
        )
    elif delta_util >= 0:
        ui.hallazgo(
            f"El packaging <b>aumenta la utilidad por unidad ({money(delta_util)}) pero diluye el "
            f"margen porcentual ({delta_margen:+.1f} pp)</b>. Es viable si el objetivo es utilidad "
            "absoluta, no ratio de margen.",
            "neutro",
        )
    else:
        ui.hallazgo(
            f"Con estos parámetros el packaging <b>destruye rentabilidad</b>: la utilidad por unidad "
            f"cae {money(abs(delta_util))} y el margen {abs(delta_margen):.1f} pp. El incremento de "
            "precio no compensa el costo del empaque.",
            "alerta",
        )

    # ------------------------------------ incremento mínimo para no perder margen
    st.markdown("### ¿Cuánto tendría que subir el precio?")
    filas = []
    for _, r in esc.iterrows():
        base = t[t["Producto"] == r["Producto"]].iloc[0]
        minimo = pricing.precio_minimo_packaging(
            r["Precio actual"], base["COGS"], costo, p
        )
        filas.append(
            {
                "Producto": r["Producto"],
                "Precio actual": r["Precio actual"],
                "Precio mínimo para mantener el margen": minimo,
                "Incremento mínimo %": (
                    (minimo / r["Precio actual"] - 1) * 100
                    if np.isfinite(minimo) and r["Precio actual"]
                    else np.nan
                ),
                "Incremento propuesto %": incremento,
            }
        )
    minimos = pd.DataFrame(filas)
    minimos["Alcanza"] = np.where(
        minimos["Incremento propuesto %"] >= minimos["Incremento mínimo %"], "Sí", "No"
    )
    st.dataframe(
        minimos,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Precio actual": st.column_config.NumberColumn(format="$%,.0f"),
            "Precio mínimo para mantener el margen": st.column_config.NumberColumn(
                format="$%,.0f"
            ),
            "Incremento mínimo %": st.column_config.NumberColumn(format="%.1f%%"),
            "Incremento propuesto %": st.column_config.NumberColumn(format="%.1f%%"),
        },
    )
    minimo_prom = minimos["Incremento mínimo %"].mean()
    if np.isfinite(minimo_prom):
        ui.nota_fuente(
            f"En promedio, el precio debe subir {minimo_prom:.1f}% para que el margen porcentual "
            f"quede igual que hoy. El incremento propuesto es {incremento:.1f}%."
        )

    # ------------------------------------------------------------- detalle
    st.markdown("### Detalle por producto")
    st.dataframe(
        esc,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Precio actual": st.column_config.NumberColumn(format="$%,.0f"),
            "Precio con packaging": st.column_config.NumberColumn(format="$%,.0f"),
            "COGS actual": st.column_config.NumberColumn(format="$%,.0f"),
            "COGS con packaging": st.column_config.NumberColumn(format="$%,.0f"),
            "Utilidad actual": st.column_config.NumberColumn(format="$%,.0f"),
            "Utilidad con packaging": st.column_config.NumberColumn(format="$%,.0f"),
            "Δ Utilidad": st.column_config.NumberColumn(format="$%,.0f"),
            "Margen contribución actual %": st.column_config.NumberColumn(
                "Margen actual", format="%.1f%%"
            ),
            "Margen contribución con packaging %": st.column_config.NumberColumn(
                "Margen con packaging", format="%.1f%%"
            ),
            "Δ Margen (pp)": st.column_config.NumberColumn(format="%.1f"),
        },
    )

    # ------------------------------------------------------------- encuesta
    if "Packaging_Importance" in ctx.encuesta.columns:
        s = ctx.encuesta["Packaging_Importance"].dropna()
        if not s.empty:
            st.markdown("### Qué dice la encuesta sobre el empaque")
            alto = (s >= 4).mean() * 100
            ui.fila_kpis(
                [
                    dict(
                        etiqueta="Importancia promedio del empaque",
                        valor=f"{s.mean():.2f} de 5",
                    ),
                    dict(etiqueta="Le dan importancia alta (4-5)", valor=pct(alto, 0)),
                    dict(
                        etiqueta="Le dan importancia baja (1-2)",
                        valor=pct((s <= 2).mean() * 100, 0),
                    ),
                    dict(etiqueta="Respuestas", valor=f"{len(s)}"),
                ]
            )
            if alto < 40:
                ui.hallazgo(
                    f"Solo {alto:.0f}% de la muestra califica el empaque con 4 o 5. La encuesta no "
                    "respalda que el empaque sea, por sí solo, un motor de disposición a pagar en "
                    "este grupo. Tiene más sentido como refuerzo de marca y de la experiencia de "
                    "unboxing que como justificación directa de un precio mayor.",
                    "alerta",
                )
            else:
                ui.hallazgo(
                    f"{alto:.0f}% de la muestra le da importancia alta al empaque, lo que da algún "
                    "sustento a la hipótesis de percepción de valor. Aun así, importancia declarada "
                    "no equivale a disposición a pagar: conviene probarlo con un test A/B de precio.",
                    "ok",
                )
            ui.nota_fuente(
                "La pregunta midió importancia general del empaque, no la reacción a un empaque "
                "premium concreto ni a un precio mayor por él."
            )

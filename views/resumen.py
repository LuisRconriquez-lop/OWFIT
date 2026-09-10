"""Resumen ejecutivo: KPIs de portafolio y hallazgos sustentados en los datos."""

from __future__ import annotations

import numpy as np
import streamlit as st

from config import settings
from src import charts, insights, market, ui
from src.ui import COLORES
from src.utils import money, num, pct, reporte_faltantes


def _recomendacion_boton(cambio_pct: float):
    if not np.isfinite(cambio_pct) or abs(cambio_pct) < 1:
        return "MANTENER PRECIO", COLORES["gris"]
    if cambio_pct > 0:
        return "↑ SUBIR PRECIO", COLORES["musgo"]
    return "↓ BAJAR PRECIO", COLORES["negativo"]


def _salud_datos(internos) -> tuple[str, str] | None:
    """Cuántos productos internos no tienen COGS o Cantidad. Reutiliza
    reporte_faltantes (src/utils.py); no agrega cálculos nuevos."""
    if internos is None or internos.empty:
        return None
    faltantes = reporte_faltantes(internos)
    total = len(internos)

    def _faltan(columna: str) -> int:
        fila = faltantes[faltantes["Columna"] == columna]
        return int(fila["Faltantes"].iloc[0]) if not fila.empty else 0

    sin_cogs = _faltan("COGS")
    sin_cantidad = _faltan("Cantidad") if "Cantidad" in internos.columns else None

    partes = []
    if sin_cogs:
        partes.append(
            f"{sin_cogs} de {total} sin COGS (no calculan margen ni utilidad)"
        )
    if sin_cantidad:
        partes.append(
            f"{sin_cantidad} de {total} sin Cantidad (no entran en promedios ponderados ni utilidad total)"
        )

    if not partes:
        return (
            "<b>Salud de datos: completa.</b> Todos los productos internos tienen COGS"
            + (" y Cantidad" if "Cantidad" in internos.columns else "")
            + " cargados.",
            "ok",
        )
    return ("<b>Salud de datos:</b> " + "; ".join(partes) + ".", "alerta")


def render(ctx):
    ui.kicker("Resumen")
    st.title("Resumen ejecutivo")
    st.caption(
        "Posición de precio de OWFIT frente al mercado mexicano de ropa deportiva femenina, "
        "y efecto de los precios recomendados sobre la rentabilidad unitaria."
    )
    ui.cinta_origen(ctx.es_demo, ctx.nombre_archivo)

    ui.mostrar_validacion(ctx.val_internos, "Archivo interno")
    if not ctx.val_internos.ok:
        st.stop()

    salud = _salud_datos(ctx.internos)
    if salud:
        ui.hallazgo(*salud)

    k = ctx.kpis
    p = ctx.params

    # ---------------------------------------------------------- vista rápida
    categorias = (
        sorted(ctx.tabla["Categoría"].dropna().unique().astype(str))
        if not ctx.tabla.empty
        else []
    )

    # Valor de inventario declarado = PVP x piezas del archivo interno. Es una
    # foto del stock a precio de lista, no ingreso realizado: la nota lo dice
    # explícitamente para que nadie lo lea como venta. Sin columna 'Cantidad'
    # no hay piezas que valorar, y la tarjeta vuelve al conteo de categorías.
    valor_inv = k.get("valor_inventario_pvp", np.nan)
    piezas = k.get("piezas_totales", np.nan)
    if valor_inv is not None and np.isfinite(valor_inv) and valor_inv > 0:
        kpi_inventario = dict(
            etiqueta="Valor de inventario declarado",
            valor=money(valor_inv),
            icono="paquete",
            nota=f"PVP × {num(piezas)} piezas · no es venta histórica",
        )
    else:
        kpi_inventario = dict(
            etiqueta="Categorías en el portafolio",
            valor=num(len(categorias)),
            icono="paquete",
            nota=(
                ", ".join(categorias)[:60]
                if categorias
                else "Sin categorías en el archivo interno"
            ),
        )
    ui.fila_kpis(
        [
            dict(
                etiqueta="Precio promedio",
                valor=money(k["precio_actual_prom"]),
                icono="dinero",
                nota=(
                    "Ponderado por piezas"
                    if k["ponderado_por_volumen"]
                    else "Promedio simple"
                ),
            ),
            dict(
                etiqueta="Margen de contribución",
                valor=pct(k["margen_contrib_prom"]),
                icono="porcentaje",
                nota="(PVP − COGS − variables) / PVP",
            ),
            kpi_inventario,
        ]
    )

    resumen_cat = insights.oportunidad_por_categoria(ctx.tabla)
    if not resumen_cat.empty:
        fig = charts.barras_comparacion(
            resumen_cat,
            "Categoría",
            ["Precio actual", "Precio recomendado"],
            "Precio actual y recomendado por categoría",
            horizontal=True,
        )
        st.plotly_chart(fig, use_container_width=True)

    cambio = k["cambio_pct_prom"]
    etiqueta_boton, color_boton = _recomendacion_boton(cambio)
    st.markdown(
        f"""
        <div style="border:1px solid {COLORES['linea']}; border-radius:6px; padding:1rem 1.2rem;
                    background:#FFFFFF; margin-top:0.4rem;">
            <div style="font-size:0.8rem; color:{COLORES['gris']}; font-weight:500;
                        letter-spacing:0.03em; text-transform:uppercase;">Recomendación</div>
            <div style="font-size:1.6rem; font-weight:600; color:{COLORES['tinta']}; margin:0.2rem 0 0.9rem 0;">
                Precio recomendado: {money(k['precio_rec_prom'])}
                <span style="font-size:0.95rem; font-weight:500; color:{COLORES['gris']};">
                    ({'+' if cambio > 0 else ''}{cambio:.1f}% vs. actual, P{p.percentil_objetivo})
                </span>
            </div>
            <div style="text-align:center;">
                <span style="background:{color_boton}; color:#FFFFFF; font-weight:700;
                            padding:0.7rem 2.2rem; border-radius:999px; font-size:0.95rem;
                            letter-spacing:0.04em; display:inline-block;">{etiqueta_boton}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    ui.nota_fuente(
        "Dirección sugerida a partir del cambio promedio ponderado entre el precio actual y el "
        "recomendado del portafolio. El detalle por producto está en la página Pricing."
    )

    st.markdown("---")

    # ---------------------------------------------------------- KPIs alcance
    st.subheader("Alcance del análisis")
    ui.fila_kpis(
        [
            dict(
                etiqueta="Productos internos analizados",
                valor=num(k["productos"]),
                icono="paquete",
                nota=f"{k['con_recomendacion']} con precio recomendado",
            ),
            dict(
                etiqueta="Marcas en la base de mercado",
                valor=num(ctx.mercado_productos["Marca"].nunique()),
                icono="usuarios",
                nota=f"{num(len(ctx.comparables))} productos comparables",
            ),
            dict(
                etiqueta="Competidores en el conjunto elegido",
                valor=num(len(ctx.competencia)),
                nota=", ".join(sorted(ctx.competencia["Marca"].unique()))[:60] or "—",
            ),
        ]
    )
    col_a, col_b = st.columns([1, 1])
    with col_a:
        ui.kpi(
            "Respuestas de encuesta",
            num(len(ctx.encuesta)),
            nota="Muestra por conveniencia",
        )
    with col_b:
        ui.kpi(
            "Meses de Google Trends",
            num(len(ctx.trends)) if not ctx.trends.empty else "—",
            nota=(
                f"{ctx.trends.shape[1]} términos"
                if not ctx.trends.empty
                else "sin datos"
            ),
        )
        termino_ppal = None
        if not ctx.trends.empty:
            ref = settings.CATEGORIA_REFERENCIA_ENCUESTA.lower()
            coincide = [c for c in ctx.trends.columns if ref in str(c).lower()]
            termino_ppal = coincide[0] if coincide else ctx.trends.columns[0]
        if termino_ppal:
            serie_ppal = ctx.trends[termino_ppal].dropna()
            if len(serie_ppal) >= 6:
                mitad = min(6, len(serie_ppal) // 2)
                reciente = serie_ppal.iloc[-mitad:].mean()
                previo = serie_ppal.iloc[-2 * mitad : -mitad].mean()
                direccion = (
                    "subiendo"
                    if reciente > previo
                    else "bajando" if reciente < previo else "estable"
                )
                color_linea = (
                    COLORES["musgo"] if reciente >= previo else COLORES["negativo"]
                )
                st.plotly_chart(
                    charts.sparkline(serie_ppal.tail(24), color=color_linea),
                    use_container_width=True,
                    config={"displayModeBar": False},
                )
                st.caption(
                    f"'{termino_ppal}' {direccion} en los últimos {mitad} meses vs. los {mitad} anteriores."
                )

    # ---------------------------------------------------------- KPIs precio
    st.subheader("Precio y rentabilidad")
    cambio = k["cambio_pct_prom"]
    delta_margen = k["margen_contrib_rec_prom"] - k["margen_contrib_prom"]
    cat_todas = insights.oportunidad_por_categoria(ctx.tabla)
    cat_alerta = (
        cat_todas[
            cat_todas["Margen contribución recomendado %"] < p.margen_objetivo_pct
        ]
        if not cat_todas.empty
        and "Margen contribución recomendado %" in cat_todas.columns
        else cat_todas.iloc[0:0]
    )
    ui.fila_kpis(
        [
            dict(
                etiqueta="Precio actual promedio",
                valor=money(k["precio_actual_prom"]),
                icono="dinero",
                nota=(
                    "Ponderado por piezas"
                    if k["ponderado_por_volumen"]
                    else "Promedio simple"
                ),
            ),
            dict(
                etiqueta=f"Precio recomendado promedio (P{p.percentil_objetivo})",
                valor=money(k["precio_rec_prom"]),
                icono="meta",
                delta=f"{'+' if cambio > 0 else ''}{cambio:.1f}% vs actual",
                positivo=cambio >= 0,
                acento=True,
            ),
            dict(
                etiqueta="Margen bruto promedio",
                valor=pct(k["margen_bruto_prom"]),
                icono="porcentaje",
                nota="(PVP − COGS) / PVP",
            ),
        ]
    )
    ui.fila_kpis(
        [
            dict(
                etiqueta="Margen de contribución estimado",
                valor=pct(k["margen_contrib_prom"]),
                delta=f"{'+' if delta_margen > 0 else ''}{delta_margen:.1f} pp con precio recomendado",
                positivo=delta_margen >= 0,
                nota="No es margen neto: excluye costos fijos y operación",
            ),
            dict(
                etiqueta="Utilidad por unidad",
                valor=money(k["utilidad_prom"]),
                delta=f"{money(k['utilidad_rec_prom'])} recomendada",
                positivo=k["utilidad_rec_prom"] >= k["utilidad_prom"],
            ),
            dict(
                etiqueta="Categorías con alerta de margen",
                valor=f"{len(cat_alerta)}",
                nota=(
                    f"de {len(cat_todas)}: siguen bajo el {pct(p.margen_objetivo_pct, 0)} objetivo "
                    "aun con precio recomendado"
                    if not cat_todas.empty
                    else "sin categorías para evaluar"
                ),
            ),
        ]
    )

    col1, col2 = st.columns([1, 1])
    with col1:
        pos = k["percentil_prom"]
        etiqueta = market.etiqueta_posicion(pos)
        ui.kpi(
            "Posición competitiva del portafolio",
            f"P{pos:.0f}" if np.isfinite(pos) else "—",
            nota=f"{etiqueta} · percentil promedio dentro de las categorías comparables",
            acento=True,
        )
    with col2:
        if not cat_todas.empty:
            top = cat_todas.iloc[0]
            extra = ""
            if "Impacto en utilidad ($)" in cat_todas.columns and np.isfinite(
                top.get("Impacto en utilidad ($)", np.nan)
            ):
                extra = f" · {money(top['Impacto en utilidad ($)'])} de utilidad adicional sobre el inventario declarado"
            ui.kpi(
                "Categoría con mayor oportunidad",
                str(top["Categoría"]),
                nota=f"{pct(top['Cambio %'])} de ajuste sugerido{extra}",
            )

    # ---------------------------------------------------------- hallazgos
    st.subheader("Lectura de los resultados")
    lista = insights.hallazgos_portafolio(ctx.tabla, k, p)
    comparacion = market.owfit_vs_mercado(
        ctx.comparables[
            (ctx.comparables["Marca"] == settings.MARCA_OWFIT)
            | (ctx.comparables["Marca"].isin(ctx.competencia["Marca"].unique()))
        ],
        balanceado=p.balancear_marcas,
    )
    impactos = {}
    if not cat_todas.empty and "Impacto en utilidad ($)" in cat_todas.columns:
        impactos = dict(
            zip(cat_todas["Categoría"], cat_todas["Impacto en utilidad ($)"])
        )
    lista += insights.hallazgos_mercado(ctx.comparables, comparacion, impactos)

    precio_ref = np.nan
    ref_cat = ctx.tabla[
        ctx.tabla["Categoría"] == settings.CATEGORIA_REFERENCIA_ENCUESTA
    ]
    if not ref_cat.empty:
        precio_ref = float(ref_cat["PVP actual"].median())
    lista += insights.hallazgos_encuesta(ctx.encuesta, ctx.vw, ctx.gg, precio_ref)

    if not lista:
        ui.sin_datos("No hay hallazgos que se sostengan con los datos cargados.")

    # Solo los cinco de mayor impacto quedan a la vista; el resto no se borra,
    # se guarda en un expander cerrado.
    visibles, resto = insights.dividir_por_prioridad(lista, maximo=5)
    for texto, tipo, _ in visibles:
        ui.hallazgo(texto, tipo)
    if resto:
        with st.expander(f"Ver detalle · {len(resto)} hallazgo(s) más"):
            for texto, tipo, _ in resto:
                ui.hallazgo(texto, tipo)

    ui.mostrar_validacion(ctx.val_mercado, "Base de mercado")

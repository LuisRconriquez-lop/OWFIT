"""Rentabilidad: estructura de costos, márgenes y utilidad del portafolio."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src import charts, pricing, ui
from src.ui import COLORES
from src.utils import money, pct


def render(ctx):
    ui.kicker("Rentabilidad")
    st.title("Rentabilidad")
    st.caption(
        "El COGS que se carga ya incluye fabricación, importación, transporte, aranceles y bodega: "
        "la prenda embolsada y lista para entregar. Aquí solo se agregan los costos posteriores a la venta."
    )
    ui.cinta_origen(ctx.es_demo, ctx.nombre_archivo)

    if not ctx.val_internos.ok or ctx.tabla.empty:
        st.stop()

    t = ctx.tabla
    p = ctx.params
    k = ctx.kpis

    st.markdown("### Estructura de costos configurada")
    ui.fila_kpis(
        [
            dict(etiqueta="Pasarela", valor=pct(p.pasarela_pct, 1)),
            dict(etiqueta="Publicidad", valor=pct(p.publicidad_pct, 1)),
            dict(etiqueta="Otros variables", valor=pct(p.otros_variables_pct, 1)),
        ]
    )
    ui.fila_kpis(
        [
            dict(
                etiqueta="Envío",
                valor=money(p.envio_mxn),
                nota=f"{p.pct_envio_absorbido:.0f}% absorbido",
            ),
            dict(etiqueta="Material de envío", valor=money(p.material_envio_mxn)),
        ]
    )

    st.markdown(
        f"Costo fijo por unidad: **{money(p.costo_fijo_unitario)}** · "
        f"Costos proporcionales al precio: **{pct(p.pct_variables * 100, 1)}**"
    )

    # ------------------------------------------------------------- KPIs
    st.markdown("### Resultado del portafolio")
    ui.fila_kpis(
        [
            dict(
                etiqueta="Margen bruto promedio",
                valor=pct(k["margen_bruto_prom"]),
                icono="porcentaje",
            ),
            dict(
                etiqueta="Margen de contribución estimado",
                valor=pct(k["margen_contrib_prom"]),
                icono="tendencia",
                nota="No es margen neto",
            ),
            dict(
                etiqueta="Utilidad promedio por unidad",
                valor=money(k["utilidad_prom"]),
                icono="dinero",
            ),
        ]
    )
    ui.fila_kpis(
        [
            dict(
                etiqueta="Utilidad total sobre piezas declaradas",
                valor=money(k["utilidad_total_actual"]),
                icono="meta",
                delta=f"{money(k['utilidad_total_rec'] - k['utilidad_total_actual'])} con precio recomendado",
                positivo=k["utilidad_total_rec"] >= k["utilidad_total_actual"],
                acento=True,
            ),
            dict(
                etiqueta="Productos por debajo del costo variable",
                valor=f"{k['productos_bajo_costo']}",
                icono="alerta",
                positivo=k["productos_bajo_costo"] == 0,
                nota="Utilidad por unidad negativa",
            ),
        ]
    )

    if k["ponderado_por_volumen"]:
        ui.nota_fuente(
            "Los promedios se ponderan por las piezas declaradas en el archivo interno. "
            "La utilidad total supone que se vende el inventario completo al precio indicado; "
            "no es un pronóstico de ventas."
        )
    else:
        ui.nota_fuente(
            "Sin columna 'Cantidad': todos los promedios son simples, sin ponderar por volumen."
        )

    # ------------------------------------------------------------- tabla
    st.markdown("### Detalle por producto")
    detalle = t[
        [
            "Producto",
            "Categoría",
            "PVP actual",
            "COGS",
            "Utilidad actual",
            "Margen bruto actual %",
            "Margen contribución actual %",
            "Cantidad",
        ]
    ].copy()
    detalle["Costos variables $"] = detalle["PVP actual"] * p.pct_variables
    detalle["Envío + material $"] = p.costo_fijo_unitario
    if detalle["Cantidad"].notna().any():
        detalle["Utilidad total $"] = detalle["Utilidad actual"] * detalle["Cantidad"]

    st.dataframe(
        detalle.sort_values("Margen contribución actual %"),
        use_container_width=True,
        hide_index=True,
        column_config={
            "PVP actual": st.column_config.NumberColumn(format="$%,.0f"),
            "COGS": st.column_config.NumberColumn(format="$%,.0f"),
            "Costos variables $": st.column_config.NumberColumn(format="$%,.0f"),
            "Envío + material $": st.column_config.NumberColumn(format="$%,.0f"),
            "Utilidad actual": st.column_config.NumberColumn(format="$%,.0f"),
            "Utilidad total $": st.column_config.NumberColumn(format="$%,.0f"),
            "Margen bruto actual %": st.column_config.NumberColumn(
                "Margen bruto", format="%.1f%%"
            ),
            "Margen contribución actual %": st.column_config.NumberColumn(
                "Margen contribución", format="%.1f%%"
            ),
        },
    )

    # ------------------------------------------------------------- gráficas
    c1, c2 = st.columns(2)
    with c1:
        prom = t[["PVP actual", "COGS"]].mean()
        pvp_m = float(prom["PVP actual"])
        cogs_m = float(prom["COGS"])
        eco = pricing.economia_unitaria(pvp_m, cogs_m, p)
        st.plotly_chart(
            charts.cascada_costos(
                pvp_m,
                cogs_m,
                eco["costo_variable_pct"],
                eco["costo_envio"],
                eco["utilidad_unidad"],
            ),
            use_container_width=True,
        )
        ui.nota_fuente(
            "Producto promedio del archivo interno, con los parámetros activos."
        )

    with c2:
        d = t.dropna(subset=["Margen contribución actual %"]).sort_values(
            "Margen contribución actual %"
        )
        fig = go.Figure(
            go.Bar(
                x=d["Margen contribución actual %"],
                y=d["Producto"],
                orientation="h",
                marker_color=[
                    (
                        COLORES["negativo"]
                        if v < p.margen_objetivo_pct
                        else COLORES["musgo"]
                    )
                    for v in d["Margen contribución actual %"]
                ],
            )
        )
        fig.add_vline(
            x=p.margen_objetivo_pct,
            line_dash="dash",
            line_color=COLORES["tinta"],
            annotation_text=f"Objetivo {p.margen_objetivo_pct:.0f}%",
            annotation_font_size=10,
        )
        fig.update_layout(
            title="Margen de contribución por producto",
            xaxis_title="%",
            yaxis_title=None,
        )
        st.plotly_chart(
            charts._estilo(fig, alto=max(320, 26 * len(d) + 90), leyenda=False),
            use_container_width=True,
        )


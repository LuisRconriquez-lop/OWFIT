"""Pricing: precio recomendado por producto y por categoría."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src import charts, pricing, ui
from src.utils import money, pct

COLUMNAS_TABLA = [
    "Producto",
    "Categoría",
    "PVP actual",
    "COGS",
    "Precio recomendado",
    "Cambio $",
    "Cambio %",
    "Utilidad actual",
    "Utilidad recomendada",
    "Margen contribución actual %",
    "Margen contribución recomendado %",
    "Competidores comparables",
    "Criterio",
]


def render(ctx):
    ui.kicker("Pricing")
    st.title("Pricing")
    st.caption(
        "Precio recomendado producto por producto. Cada precio combina la referencia "
        "competitiva de su categoría con el piso de rentabilidad que exige el margen objetivo."
    )
    ui.cinta_origen(ctx.es_demo, ctx.nombre_archivo)

    ui.mostrar_validacion(ctx.val_internos, "Archivo interno")
    if not ctx.val_internos.ok or ctx.tabla.empty:
        st.stop()

    t = ctx.tabla
    p = ctx.params

    st.markdown(
        f"**Configuración activa:** percentil objetivo P{p.percentil_objetivo} · margen objetivo "
        f"{pct(p.margen_objetivo_pct, 0)} · costos variables "
        f"{pct(p.pasarela_pct + p.publicidad_pct + p.otros_variables_pct, 1)} del precio + "
        f"{money(p.costo_fijo_unitario)} de envío por unidad · criterio: {p.modo.lower()}. "
        "Ajústelo desde la barra lateral."
    )

    tab1, tab2 = st.tabs(["Por producto", "Por categoría"])

    # ------------------------------------------------------------- producto
    with tab1:
        c1, c2, c3 = st.columns([2, 2, 1.4])
        with c1:
            cats = ["Todas"] + sorted(
                t["Categoría"].dropna().unique().astype(str).tolist()
            )
            cat_sel = st.selectbox("Categoría", cats)
        with c2:
            criterios = ["Todos"] + sorted(
                t["Criterio"].dropna().unique().astype(str).tolist()
            )
            crit_sel = st.selectbox("Criterio que definió el precio", criterios)
        with c3:
            solo_cambio = st.checkbox("Solo con cambio sugerido > 5%", value=False)

        d = t.copy()
        if cat_sel != "Todas":
            d = d[d["Categoría"] == cat_sel]
        if crit_sel != "Todos":
            d = d[d["Criterio"] == crit_sel]
        if solo_cambio:
            d = d[d["Cambio %"].abs() > 5]

        orden = st.selectbox(
            "Ordenar por",
            [
                "Cambio %",
                "Cambio $",
                "Utilidad actual",
                "Margen contribución actual %",
                "PVP actual",
                "Producto",
            ],
        )
        asc = orden == "Producto"
        d = d.sort_values(orden, ascending=asc, na_position="last")

        st.dataframe(
            d[COLUMNAS_TABLA],
            use_container_width=True,
            hide_index=True,
            column_config={
                "PVP actual": st.column_config.NumberColumn(format="$%,.0f"),
                "COGS": st.column_config.NumberColumn(format="$%,.0f"),
                "Precio recomendado": st.column_config.NumberColumn(format="$%,.0f"),
                "Cambio $": st.column_config.NumberColumn(format="$%,.0f"),
                "Cambio %": st.column_config.NumberColumn(format="%.1f%%"),
                "Utilidad actual": st.column_config.NumberColumn(format="$%,.0f"),
                "Utilidad recomendada": st.column_config.NumberColumn(format="$%,.0f"),
                "Margen contribución actual %": st.column_config.NumberColumn(
                    "Margen contrib. actual", format="%.1f%%"
                ),
                "Margen contribución recomendado %": st.column_config.NumberColumn(
                    "Margen contrib. recomendado", format="%.1f%%"
                ),
                "Competidores comparables": st.column_config.NumberColumn(
                    "Comparables", format="%d"
                ),
            },
            height=min(620, 42 + 35 * max(len(d), 1)),
        )

        st.download_button(
            "Descargar tabla en CSV",
            d.to_csv(index=False).encode("utf-8-sig"),
            file_name="owfit_pricing_por_producto.csv",
            mime="text/csv",
        )
        ui.nota_fuente(
            "Margen de contribución = utilidad por unidad / PVP. No incluye costos fijos, "
            "nómina ni operación, por lo que no debe leerse como margen neto."
        )

    # ------------------------------------------------------------ categoría
    with tab2:
        resumen = pricing.resumen_por_categoria(t)
        if resumen.empty:
            ui.sin_datos("No hay categorías con datos suficientes.")
        else:
            st.dataframe(
                resumen,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Precio actual": st.column_config.NumberColumn(format="$%,.0f"),
                    "Precio recomendado": st.column_config.NumberColumn(
                        format="$%,.0f"
                    ),
                    "Cambio %": st.column_config.NumberColumn(format="%.1f%%"),
                    "Margen contribución actual %": st.column_config.NumberColumn(
                        "Margen contrib. actual", format="%.1f%%"
                    ),
                    "Margen contribución recomendado %": st.column_config.NumberColumn(
                        "Margen contrib. recomendado", format="%.1f%%"
                    ),
                    "Utilidad actual": st.column_config.NumberColumn(format="$%,.0f"),
                    "Utilidad recomendada": st.column_config.NumberColumn(
                        format="$%,.0f"
                    ),
                    "Impacto en utilidad ($)": st.column_config.NumberColumn(
                        format="$%,.0f"
                    ),
                },
            )
            c1, c2 = st.columns(2)
            with c1:
                st.plotly_chart(
                    charts.barras_comparacion(
                        resumen,
                        "Categoría",
                        ["Precio actual", "Precio recomendado"],
                        "Precio por categoría",
                        horizontal=True,
                    ),
                    use_container_width=True,
                )
            with c2:
                st.plotly_chart(
                    charts.barras_comparacion(
                        resumen,
                        "Categoría",
                        [
                            "Margen contribución actual %",
                            "Margen contribución recomendado %",
                        ],
                        "Margen de contribución por categoría",
                        eje_y="%",
                        horizontal=True,
                    ),
                    use_container_width=True,
                )
            ui.nota_fuente(
                "Solo aparecen las categorías presentes en el archivo interno. "
                "No se crean categorías que no existan en los datos."
            )

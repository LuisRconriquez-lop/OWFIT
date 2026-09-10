"""Competencia: posición de OWFIT contra el mercado, por categoría comparable."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config import settings
from src import charts, market, ui
from src.ui import COLORES, COLOR_SEGMENTO
from src.utils import money, pct


def render(ctx):
    ui.kicker("Competencia")
    st.title("Competencia")
    st.caption(
        "Comparaciones dentro de la misma categoría: leggings contra leggings, tops contra tops. "
        "Los precios en dólares se convierten a pesos con el tipo de cambio de la barra lateral."
    )

    productos = ctx.comparables
    p = ctx.params

    marcas_incluidas = sorted(ctx.competencia["Marca"].unique().tolist())
    st.markdown(
        f"**Conjunto competitivo activo:** {', '.join(marcas_incluidas) or 'ninguno'} · "
        f"{'marcas balanceadas' if p.balancear_marcas else 'sin balancear marcas'}."
    )
    if not p.balancear_marcas:
        ui.hallazgo(
            "Sin balancear marcas, la marca con el catálogo más grande define casi sola los "
            "percentiles del mercado. Actívelo en la barra lateral si quiere que cada marca pese igual.",
            "alerta",
        )

    tab1, tab2, tab3 = st.tabs(["OWFIT vs mercado", "Por categoría", "Mapa de marcas"])

    # --------------------------------------------------------- vs mercado
    with tab1:
        universo = productos[
            (productos["Marca"] == settings.MARCA_OWFIT)
            | (productos["Marca"].isin(marcas_incluidas))
        ]
        comp = market.owfit_vs_mercado(universo, balanceado=p.balancear_marcas)
        if comp.empty:
            ui.sin_datos(
                "No hay categorías comparables con el conjunto competitivo elegido."
            )
        else:
            st.dataframe(
                comp,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Mediana OWFIT": st.column_config.NumberColumn(format="$%,.0f"),
                    "Mediana mercado": st.column_config.NumberColumn(format="$%,.0f"),
                    "Diferencia $": st.column_config.NumberColumn(format="$%,.0f"),
                    "Diferencia %": st.column_config.NumberColumn(format="%.1f%%"),
                    "Percentil de OWFIT": st.column_config.NumberColumn(format="%.0f"),
                },
            )
            d = comp.dropna(subset=["Diferencia %"]).sort_values("Diferencia %")
            fig = go.Figure(
                go.Bar(
                    x=d["Diferencia %"],
                    y=d["Categoría"],
                    orientation="h",
                    marker_color=[
                        COLORES["negativo"] if v < 0 else COLORES["musgo"]
                        for v in d["Diferencia %"]
                    ],
                    texttemplate="%{x:.0f}%",
                    textposition="outside",
                )
            )
            fig.add_vline(x=0, line_color=COLORES["gris"])
            fig.update_layout(
                title="Diferencia de la mediana de OWFIT contra la del mercado",
                xaxis_title="% respecto a la mediana del mercado",
                yaxis_title=None,
            )
            st.plotly_chart(
                charts._estilo(fig, alto=380, leyenda=False), use_container_width=True
            )
            ui.nota_fuente(
                "Valores negativos indican que OWFIT cobra menos que la mediana de la categoría. "
                "Las categorías donde OWFIT no tiene productos aparecen sin diferencia."
            )

    # --------------------------------------------------------- por categoría
    with tab2:
        cats = sorted(
            productos.loc[productos["es_prenda"], "Categoria_norm"]
            .dropna()
            .unique()
            .tolist()
        )
        cat = st.selectbox(
            "Categoría", cats, index=cats.index("Leggings") if "Leggings" in cats else 0
        )

        ref, pesos = market.referencia_precios(ctx.competencia, cat, p.balancear_marcas)
        owfit_cat = productos[
            (productos["Marca"] == settings.MARCA_OWFIT)
            & (productos["Categoria_norm"] == cat)
        ]["Precio_MXN"].dropna()

        if ref.empty:
            ui.sin_datos(
                f"No hay comparables de '{cat}' en el conjunto competitivo elegido."
            )
        else:
            quantiles = {
                f"P{q}": market.cuantil_ponderado(ref, pesos, q / 100)
                for q in (25, 50, 75, 90)
            }
            ui.fila_kpis(
                [
                    dict(
                        etiqueta="Mediana del mercado",
                        valor=money(quantiles["P50"]),
                        nota=f"{len(ref)} productos de {ctx.competencia[ctx.competencia['Categoria_norm'] == cat]['Marca'].nunique()} marca(s)",
                    ),
                    dict(
                        etiqueta=f"Percentil objetivo P{p.percentil_objetivo}",
                        valor=money(
                            market.cuantil_ponderado(
                                ref, pesos, p.percentil_objetivo / 100
                            )
                        ),
                        acento=True,
                    ),
                    dict(
                        etiqueta="Mediana de OWFIT",
                        valor=money(owfit_cat.median()) if not owfit_cat.empty else "—",
                        nota=f"{len(owfit_cat)} producto(s) en catálogo público",
                    ),
                    dict(
                        etiqueta="Posición de OWFIT",
                        valor=(
                            f"P{market.posicion_percentil(owfit_cat.median(), ref, pesos):.0f}"
                            if not owfit_cat.empty
                            else "—"
                        ),
                        nota=(
                            market.etiqueta_posicion(
                                market.posicion_percentil(
                                    owfit_cat.median(), ref, pesos
                                )
                            )
                            if not owfit_cat.empty
                            else "Sin productos"
                        ),
                    ),
                ]
            )

            precio_rec = np.nan
            if not ctx.tabla.empty:
                sel = ctx.tabla[ctx.tabla["Categoría"] == cat]
                if not sel.empty:
                    precio_rec = float(sel["Precio recomendado"].median())

            st.plotly_chart(
                charts.posicion_competitiva(
                    ref,
                    float(owfit_cat.median()) if not owfit_cat.empty else np.nan,
                    precio_rec,
                    cat,
                    quantiles,
                ),
                use_container_width=True,
            )

            fig = charts.precio_por_marca_categoria(
                productos[
                    (productos["Categoria_norm"] == cat)
                    & (
                        productos["Marca"].isin(
                            marcas_incluidas + [settings.MARCA_OWFIT]
                        )
                    )
                ],
                cat,
            )
            if fig:
                st.plotly_chart(fig, use_container_width=True)

            seg = (
                productos[
                    (productos["Categoria_norm"] == cat)
                    & (
                        productos["Marca"].isin(
                            marcas_incluidas + [settings.MARCA_OWFIT]
                        )
                    )
                ]
                .groupby("Segmento")["Precio_MXN"]
                .agg(["count", "median", "min", "max"])
                .reset_index()
                .rename(
                    columns={
                        "count": "Productos",
                        "median": "Mediana",
                        "min": "Mínimo",
                        "max": "Máximo",
                    }
                )
            )
            st.markdown("**Precios por segmento en esta categoría**")
            st.dataframe(
                seg,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Mediana": st.column_config.NumberColumn(format="$%,.0f"),
                    "Mínimo": st.column_config.NumberColumn(format="$%,.0f"),
                    "Máximo": st.column_config.NumberColumn(format="$%,.0f"),
                },
            )
            ui.nota_fuente(
                "La asignación de segmento por marca es un supuesto del proyecto y se documenta "
                "en Metodología. Se puede editar en config/settings.py."
            )

    # --------------------------------------------------------- mapa
    with tab3:
        matriz = market.matriz_marca_categoria(
            productos[
                productos["es_prenda"]
                & productos["Marca"].isin(marcas_incluidas + [settings.MARCA_OWFIT])
            ]
        )
        st.markdown("**Mediana de precio por marca y categoría (MXN)**")
        st.dataframe(
            matriz.style.format("${:,.0f}", na_rep="—"), use_container_width=True
        )
        ui.nota_fuente(
            "Las celdas vacías indican que la marca no ofrece esa categoría en el catálogo "
            "capturado. No se rellenan con ceros ni con promedios."
        )

        resumen_marca = market.resumen_precio_por(
            productos[
                productos["es_prenda"]
                & productos["Marca"].isin(marcas_incluidas + [settings.MARCA_OWFIT])
            ],
            "Marca",
        )
        st.markdown("**Distribución de precio por marca**")
        st.dataframe(
            resumen_marca.round(0),
            use_container_width=True,
            hide_index=True,
            column_config={
                c: st.column_config.NumberColumn(format="$%,.0f")
                for c in [
                    "media",
                    "mediana",
                    "desv_est",
                    "min",
                    "P25",
                    "P50",
                    "P75",
                    "P90",
                    "max",
                ]
            },
        )

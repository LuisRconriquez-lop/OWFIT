"""EDA de la base de mercado."""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from config import settings
from src import charts, market, ui
from src.utils import describe_numerica, money, num, pct, reporte_faltantes


def render(ctx):
    ui.kicker("EDA de mercado")
    st.title("EDA de mercado")
    st.caption(
        "Exploración de la base de catálogos capturados. El análisis se hace a nivel producto: "
        "las tallas y colores de un mismo modelo se agrupan para que una marca con catálogo "
        "extenso no distorsione las distribuciones."
    )
    ui.mostrar_validacion(ctx.val_mercado, "Base de mercado", expandido=True)

    variantes = ctx.mercado_variantes
    productos = ctx.mercado_productos

    ui.fila_kpis(
        [
            dict(
                etiqueta="Filas de variante",
                valor=num(len(variantes)),
                nota="Cada talla o color es una fila",
            ),
            dict(etiqueta="Productos únicos", valor=num(len(productos))),
            dict(etiqueta="Marcas", valor=num(productos["Marca"].nunique())),
        ]
    )
    ui.fila_kpis(
        [
            dict(
                etiqueta="Categorías", valor=num(productos["Categoria_norm"].nunique())
            ),
            dict(
                etiqueta="Productos comparables",
                valor=num(len(ctx.comparables)),
                nota="Prendas con precio válido",
            ),
        ]
    )

    tabs = st.tabs(
        [
            "Precio",
            "Comparaciones",
            "Variantes y disponibilidad",
            "Calidad de datos",
        ]
    )

    # ------------------------------------------------------------- precio
    with tabs[0]:
        base = ctx.comparables
        st.markdown("### Distribución de precios (prendas, MXN)")

        d = describe_numerica(base["Precio_MXN"])
        c = st.columns(6)
        for col, (etiqueta, clave) in zip(
            c,
            [
                ("Media", "media"),
                ("Mediana", "mediana"),
                ("Desv. estándar", "desv_est"),
                ("Mínimo", "min"),
                ("Máximo", "max"),
                ("Coef. de variación", "coef_variacion"),
            ],
        ):
            valor = d.get(clave, np.nan)
            col.metric(
                etiqueta, money(valor) if clave != "coef_variacion" else f"{valor:.2f}"
            )

        st.markdown("**Percentiles**")
        perc = pd.DataFrame(
            [{k: v for k, v in d.items() if k.startswith("P")}]
        ).T.reset_index()
        perc.columns = ["Percentil", "Precio (MXN)"]
        st.dataframe(
            perc,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Precio (MXN)": st.column_config.NumberColumn(format="$%,.0f")
            },
        )

        c1, c2 = st.columns(2)
        with c1:
            log = st.checkbox(
                "Escala logarítmica en los boxplots",
                value=True,
                help="Los precios abarcan dos órdenes de magnitud entre marcas "
                "de entrada y premium.",
            )
            st.plotly_chart(charts.histograma_precios(base), use_container_width=True)
        with c2:
            st.plotly_chart(
                charts.boxplot_por(base, "Segmento", "Precio por segmento", log=log),
                use_container_width=True,
            )

        st.plotly_chart(
            charts.boxplot_por(base, "Categoria_norm", "Precio por categoría", log=log),
            use_container_width=True,
        )
        st.plotly_chart(
            charts.boxplot_por(base, "Marca", "Precio por marca", log=log),
            use_container_width=True,
        )
        ui.nota_fuente(
            "Los boxplots excluyen accesorios y productos sin categorizar, y los registros con "
            "precio cero (artículos de regalo). Esos registros no se eliminaron de la base: "
            "están marcados y contabilizados en la pestaña de calidad de datos."
        )

    # ------------------------------------------------------------- comparaciones
    with tabs[1]:
        st.markdown("### Precio por marca")
        st.dataframe(
            market.resumen_precio_por(ctx.comparables, "Marca").round(0),
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

        st.markdown("### Precio por categoría")
        st.dataframe(
            market.resumen_precio_por(ctx.comparables, "Categoria_norm").round(0),
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

        st.markdown("### Precio por segmento")
        st.dataframe(
            market.resumen_precio_por(ctx.comparables, "Segmento").round(0),
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

        st.markdown("### Percentiles por categoría dentro del conjunto competitivo")
        pc = market.percentiles_categoria(
            ctx.competencia, balanceado=ctx.params.balancear_marcas
        )
        if pc.empty:
            ui.sin_datos("El conjunto competitivo elegido no tiene productos.")
        else:
            st.dataframe(
                pc.round(0),
                use_container_width=True,
                hide_index=True,
                column_config={
                    c: st.column_config.NumberColumn(format="$%,.0f")
                    for c in pc.columns
                    if c.startswith("P")
                },
            )
            ui.nota_fuente(
                "Con las marcas balanceadas, cada marca aporta el mismo peso a la distribución "
                "sin importar cuántas referencias tenga en catálogo."
            )

        st.markdown("### OWFIT frente al mercado")
        comp = market.owfit_vs_mercado(
            ctx.comparables, balanceado=ctx.params.balancear_marcas
        )
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

    # ------------------------------------------------------------- variantes
    with tabs[2]:
        st.markdown("### Número de variantes por producto")
        v = productos[productos["es_prenda"]]
        st.dataframe(
            v.groupby("Marca")["n_variantes"].describe().round(1),
            use_container_width=True,
        )
        st.plotly_chart(
            charts.boxplot_por(
                v.assign(Precio_MXN=v["n_variantes"]),
                "Marca",
                "Variantes por producto (tallas y colores)",
            ),
            use_container_width=True,
        )
        ui.nota_fuente(
            "El eje muestra el número de variantes, no el precio: se reutiliza la misma gráfica "
            "de distribución. Un catálogo con muchas variantes por modelo suele indicar una "
            "operación con más inventario por referencia."
        )

        st.markdown("### Disponibilidad")
        if productos["pct_agotado"].notna().any():
            disp = (
                productos[productos["es_prenda"]]
                .groupby("Marca")
                .agg(
                    Productos=("Producto", "count"),
                    **{"% de variantes agotadas": ("pct_agotado", "mean")},
                )
                .reset_index()
                .sort_values("% de variantes agotadas", ascending=False)
            )
            st.dataframe(
                disp,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "% de variantes agotadas": st.column_config.NumberColumn(
                        format="%.1f%%"
                    )
                },
            )
            ui.hallazgo(
                "La proporción de variantes agotadas es un indicio de rotación, no una medida de "
                "ventas: también puede reflejar problemas de surtido o de reabastecimiento.",
                "neutro",
            )
        else:
            ui.sin_datos("La base no incluye información de disponibilidad utilizable.")

    # ------------------------------------------------------------- calidad
    with tabs[3]:
        st.markdown("### Valores faltantes por columna")
        st.caption("No se eliminan filas con faltantes ni se sustituyen por cero.")
        st.dataframe(
            reporte_faltantes(ctx.mercado_variantes),
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("### Registros marcados")
        marcados = pd.DataFrame(
            [
                {
                    "Situación": "Accesorios y productos sin categorizar",
                    "Filas de variante": int(
                        (~ctx.mercado_variantes["es_prenda"]).sum()
                    ),
                    "Tratamiento": "Se excluyen de las comparaciones por categoría, se conservan en la base",
                },
                {
                    "Situación": "Precio cero o faltante",
                    "Filas de variante": int(
                        (ctx.mercado_variantes["Precio_MXN"].fillna(-1) <= 0).sum()
                    ),
                    "Tratamiento": "Se marcan como precio no válido; suelen ser regalos o promociones",
                },
                {
                    "Situación": "Catálogo en dólares",
                    "Filas de variante": int(
                        (ctx.mercado_variantes["Moneda"] == "USD").sum()
                    ),
                    "Tratamiento": f"Convertidos a MXN con el tipo de cambio de la barra lateral",
                },
            ]
        )
        st.dataframe(marcados, use_container_width=True, hide_index=True)

        st.markdown("### Precios extremos")
        top = ctx.mercado_productos.nlargest(10, "Precio_MXN")[
            ["Marca", "Producto", "Categoria_norm", "Precio_MXN", "n_variantes"]
        ]
        st.dataframe(
            top,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Precio_MXN": st.column_config.NumberColumn(
                    "Precio (MXN)", format="$%,.0f"
                )
            },
        )
        ui.nota_fuente(
            "Los precios más altos suelen corresponder a accesorios de piel y artículos que no "
            "son prenda deportiva; por eso se separan antes de comparar categorías."
        )

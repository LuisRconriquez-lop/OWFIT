"""Encuesta de consumidor: descriptivos, disposición a pagar y diagnóstico de segmentación."""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from config import settings
from src import charts, insights, survey, ui
from src.ui import COLORES
from src.utils import money, pct


def render(ctx):
    ui.kicker("Encuesta")
    st.title("Encuesta de consumidor")
    df = ctx.encuesta

    if df is None or df.empty:
        ui.sin_datos("No hay respuestas de encuesta cargadas.")
        return

    # El alcance de la muestra ya se declara una sola vez en el pie de página
    # global (ui.pie_muestra); aquí no se repite.
    ui.mostrar_validacion(ctx.val_encuesta, "Encuesta")

    tabs = st.tabs(
        [
            "Perfil",
            "Importancia de atributos",
            "Intención de compra",
        ]
    )

    # ------------------------------------------------------------- perfil
    with tabs[0]:
        c1, c2 = st.columns(2)
        preguntas = [
            ("Age", "Edad", None),
            ("Buys_Sportswear", "Compra ropa deportiva", None),
            ("Sportswear_Purchase_Frequency", "Frecuencia de compra", None),
            ("Usual_Spending", "Gasto habitual por compra", None),
            ("Main_Purchase_Channel", "Canal principal", None),
            ("Purchase_Channels", "Canales utilizados", ";"),
        ]
        for i, (col, titulo, sep) in enumerate(preguntas):
            d = survey.distribucion_categorica(df, col, sep)
            if d.empty:
                continue
            destino = c1 if i % 2 == 0 else c2
            with destino:
                st.plotly_chart(
                    charts.barras_horizontales(
                        d,
                        "Respuesta",
                        "%",
                        titulo,
                        color=COLORES["musgo"] if i % 2 == 0 else COLORES["salvia"],
                    ),
                    use_container_width=True,
                )
        ui.nota_fuente(
            "En 'Canales utilizados' los porcentajes suman más de 100% porque cada persona "
            "podía elegir varias opciones."
        )

    # ------------------------------------------------------------- atributos
    with tabs[1]:
        imp = survey.importancia_atributos(df)
        if imp.empty:
            ui.sin_datos(
                "La encuesta no incluye las variables de ranking de atributos."
            )
        else:
            ui.hallazgo(
                "El ranking es <b>forzado</b>: cada persona ordenó los cinco atributos del 1 al 5, "
                "por lo que las posiciones suman siempre lo mismo. Se puede leer qué pesa más en "
                "términos relativos, pero no cuánta importancia absoluta tiene cada atributo.",
                "neutro",
            )
            st.dataframe(
                imp,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Posición promedio": st.column_config.NumberColumn(format="%.2f"),
                    "% en 1er lugar": st.column_config.NumberColumn(format="%.0f%%"),
                    "% en top 2": st.column_config.NumberColumn(format="%.0f%%"),
                    "% en último lugar": st.column_config.NumberColumn(format="%.0f%%"),
                },
            )
            c1, c2 = st.columns(2)
            with c1:
                d = imp.copy()
                d["Prioridad"] = 6 - d["Posición promedio"]
                st.plotly_chart(
                    charts.barras_horizontales(
                        d,
                        "Atributo",
                        "Prioridad",
                        "Prioridad relativa (mayor = más importante)",
                        eje="Escala invertida del ranking",
                    ),
                    use_container_width=True,
                )
            with c2:
                st.plotly_chart(
                    charts.barras_horizontales(
                        imp,
                        "Atributo",
                        "% en 1er lugar",
                        "Porcentaje que lo puso en primer lugar",
                        color=COLORES["salvia"],
                    ),
                    use_container_width=True,
                )

        if "Packaging_Importance" in df.columns:
            s = df["Packaging_Importance"].dropna()
            if not s.empty:
                st.markdown("**Importancia del empaque (escala 1 a 5)**")
                ui.fila_kpis(
                    [
                        dict(etiqueta="Promedio", valor=f"{s.mean():.2f}"),
                        dict(etiqueta="Mediana", valor=f"{s.median():.0f}"),
                        dict(
                            etiqueta="Lo califican 4 o 5",
                            valor=pct((s >= 4).mean() * 100, 0),
                        ),
                        dict(
                            etiqueta="Lo califican 1 o 2",
                            valor=pct((s <= 2).mean() * 100, 0),
                        ),
                    ]
                )
                ui.nota_fuente(
                    "Este dato alimenta el módulo de Packaging: mide interés declarado, "
                    "no disposición a pagar por un empaque premium."
                )

    # ------------------------------------------------------------- intención
    with tabs[2]:
        gg = ctx.gg
        if gg.empty:
            ui.sin_datos(
                "La encuesta no incluye preguntas de intención de compra por precio."
            )
        else:
            st.dataframe(
                gg.drop(columns=["Ingreso relativo"], errors="ignore"),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Precio": st.column_config.NumberColumn(format="$%,.0f"),
                    "Intención promedio (1-5)": st.column_config.NumberColumn(
                        format="%.2f"
                    ),
                    "% top-2-box": st.column_config.NumberColumn(
                        "Intención alta (4-5)", format="%.1f%%"
                    ),
                    "% que respondería 3 o más": st.column_config.NumberColumn(
                        format="%.1f%%"
                    ),
                    "Ingreso relativo (índice)": st.column_config.NumberColumn(
                        format="%.0f"
                    ),
                },
            )
            st.plotly_chart(charts.curva_gabor_granger(gg), use_container_width=True)

            e = survey.elasticidad_aparente(gg)
            if e is not None:
                ui.hallazgo(
                    f"La elasticidad declarada es de <b>{e:.2f}</b>: cada 1% de aumento de precio "
                    f"se asocia a una caída de {abs(e):.2f}% en la proporción con intención alta, "
                    "dentro del rango preguntado. Es intención declarada, no comportamiento de compra "
                    "observado; la conversión real suele diferir.",
                    "neutro",
                )
            mejor = gg.loc[gg["Ingreso relativo"].idxmax()]
            ui.nota_fuente(
                f"El ingreso esperado relativo se maximiza en {money(mejor['Precio'])} dentro de los "
                f"cinco precios probados. Fuera de ese rango no hay evidencia: la encuesta no preguntó "
                "por precios menores a $699 ni mayores a $1,099."
            )

    st.markdown("### Lectura general")
    precio_ref = np.nan
    if not ctx.tabla.empty:
        sel = ctx.tabla[
            ctx.tabla["Categoría"] == settings.CATEGORIA_REFERENCIA_ENCUESTA
        ]
        if not sel.empty:
            precio_ref = float(sel["PVP actual"].median())
    for texto, tipo, _ in insights.hallazgos_encuesta(df, ctx.vw, ctx.gg, precio_ref):
        ui.hallazgo(texto, tipo)

    with st.expander("Glosario de variables de la encuesta"):
        if ctx.glosario is not None and not ctx.glosario.empty:
            st.dataframe(ctx.glosario, use_container_width=True, hide_index=True)
        else:
            st.caption("El archivo de encuesta no incluye hoja de glosario.")

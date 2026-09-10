"""Estacionalidad del interés de búsqueda y selección de modelo por backtesting."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config import settings
from src import charts, trends, ui
from src.ui import COLORES


@st.cache_data(show_spinner=False)
def _backtesting(serie: pd.Series):
    """Cachea el backtesting: reajustar SARIMA por rejilla en cada interacción es lento."""
    return trends.backtesting(
        serie, settings.MODELOS_SERIES, settings.BACKTEST_HOLDOUT_MESES
    )


ETIQUETA_PROMEDIO = "Promedio de todos los términos"


def _columnas_termino(region: pd.DataFrame) -> list[str]:
    return (
        [c for c in region.columns if c != "Estado"]
        if region is not None and not region.empty
        else []
    )


def _serie_region(region: pd.DataFrame, termino: str) -> pd.DataFrame:
    """Devuelve (Estado, valor) para un término o para el promedio de todos.

    El promedio es solo una lectura agregada de las columnas que ya trae el
    export; no re-escala ni pondera nada.
    """
    columnas = _columnas_termino(region)
    if not columnas:
        return pd.DataFrame()
    d = region[["Estado"]].copy()
    d["valor"] = (
        region[columnas].mean(axis=1)
        if termino == ETIQUETA_PROMEDIO
        else region[termino]
    )
    return d.dropna(subset=["valor"])


def _resumen_region(region: pd.DataFrame, termino: str) -> dict | None:
    """Ranking, concentración y estados de bajo interés, sobre los valores del
    export tal cual. Si no hay datos, devuelve None y la línea se omite."""
    d = _serie_region(region, termino)
    if d.empty:
        return None
    d = d.sort_values("valor", ascending=False)
    total = float(d["valor"].sum())
    top3 = d.head(3)
    return {
        "orden": d,
        "top": d.iloc[0],
        "top3": top3,
        "share_top3": (float(top3["valor"].sum()) / total * 100) if total else np.nan,
        "bajos": int((d["valor"] < settings.UMBRAL_INTERES_BAJO).sum()),
        "estados": len(d),
    }


def _termino_lider(region: pd.DataFrame) -> str | None:
    """Término con mayor interés promedio nacional dentro del export."""
    columnas = _columnas_termino(region)
    if not columnas:
        return None
    return region[columnas].mean().idxmax()


def _suma_por_estado(region: pd.DataFrame) -> float | None:
    """Si el export compara varios términos, Google reparte 100 puntos entre
    ellos DENTRO de cada estado: las filas suman una constante y el promedio de
    todos los términos es el mismo número en los 32 estados (100/n), es decir un
    mapa de un solo color. Devuelve esa constante cuando existe, o None."""
    columnas = _columnas_termino(region)
    if len(columnas) < 2:
        return None
    sumas = region[columnas].sum(axis=1)
    if sumas.empty or not np.isfinite(sumas).all():
        return None
    return float(sumas.iloc[0]) if float(sumas.std()) < 0.5 else None


def _opciones_termino(region: pd.DataFrame) -> list[str]:
    """El promedio solo se ofrece si de verdad varía entre estados."""
    columnas = _columnas_termino(region)
    if _suma_por_estado(region) is not None:
        return columnas
    return ([ETIQUETA_PROMEDIO] + columnas) if len(columnas) > 1 else columnas


def render(ctx):
    ui.kicker("Estacionalidad")
    st.title("Estacionalidad")
    st.caption(
        "Series de Google Trends: índice de interés de búsqueda de 0 a 100, re-escalado por Google "
        "en cada consulta. No son ventas, ni unidades, ni participación de mercado."
    )
    ui.mostrar_validacion(ctx.val_trends, "Google Trends", expandido=False)

    df = ctx.trends
    if df is None or df.empty:
        ui.sin_datos(
            "No hay series de Google Trends cargadas. Coloque los archivos exportados en "
            "data/google_trends/ (uno o varios, CSV o Excel) y recargue la página."
        )
        return

    ui.hallazgo(
        "<b>El índice mide interés de búsqueda, no demanda.</b> Un pico en un término puede venir de "
        "una campaña, una tendencia de moda o una noticia. Úselo para planear inventario y "
        "campañas, no para estimar ventas.",
        "neutro",
    )

    terminos = list(df.columns)
    seleccion = st.multiselect("Términos a comparar", terminos, default=terminos)
    if not seleccion:
        ui.sin_datos("Seleccione al menos un término.")
        return

    tabs = st.tabs(
        ["Tendencia", "Perfil estacional", "Modelos y pronóstico", "Interés por estado"]
    )

    # ------------------------------------------------------------- tendencia
    with tabs[0]:
        st.plotly_chart(charts.serie_trends(df, seleccion), use_container_width=True)

        st.markdown("### Evolución anual")
        filas = []
        for t in seleccion:
            anual = trends.tendencia_anual(df[t])
            if anual.empty:
                continue
            primero, ultimo = anual.iloc[0], anual.iloc[-1]
            años = ultimo["año"] - primero["año"]
            cagr = (
                ((ultimo["mean"] / primero["mean"]) ** (1 / años) - 1) * 100
                if años > 0 and primero["mean"]
                else np.nan
            )
            filas.append(
                {
                    "Término": t,
                    "Promedio primer año": primero["mean"],
                    "Promedio último año": ultimo["mean"],
                    "Cambio total %": (
                        (ultimo["mean"] / primero["mean"] - 1) * 100
                        if primero["mean"]
                        else np.nan
                    ),
                    "Crecimiento anual %": cagr,
                    "Máximo histórico": df[t].max(),
                    "Mes del máximo": (
                        df[t].idxmax().strftime("%b %Y") if df[t].notna().any() else "—"
                    ),
                }
            )
        resumen = pd.DataFrame(filas)
        st.dataframe(
            resumen,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Promedio primer año": st.column_config.NumberColumn(format="%.1f"),
                "Promedio último año": st.column_config.NumberColumn(format="%.1f"),
                "Cambio total %": st.column_config.NumberColumn(format="%.1f%%"),
                "Crecimiento anual %": st.column_config.NumberColumn(format="%.1f%%"),
            },
        )
        # Lectura geográfica: dónde está ese interés. Ambas líneas se arman con
        # el export por subregión; si no hay datos, no se escribe nada.
        lider = _termino_lider(ctx.region)
        rr = _resumen_region(ctx.region, lider) if lider else None
        if rr is not None and len(rr["top3"]) == 3:
            t3 = rr["top3"]
            ui.hallazgo(
                f"El interés por <b>{lider}</b> se concentra en <b>{t3.iloc[0]['Estado']}</b> "
                f"({t3.iloc[0]['valor']:.0f}/100), seguido de {t3.iloc[1]['Estado']} y "
                f"{t3.iloc[2]['Estado']}.",
                "ok",
            )
            ui.hallazgo(
                f"{', '.join(t3['Estado'].astype(str))} concentran el "
                f"<b>{rr['share_top3']:.0f}%</b> del interés nacional; {rr['bajos']} estados quedan "
                f"por debajo de {settings.UMBRAL_INTERES_BAJO}/100.",
                "neutro",
            )

        caen = resumen[resumen["Crecimiento anual %"] < -3]
        if len(caen):
            ui.hallazgo(
                "<b>Términos con interés a la baja:</b> "
                + ", ".join(
                    f"{r['Término']} ({r['Crecimiento anual %']:.1f}% anual)"
                    for _, r in caen.iterrows()
                ),
                "alerta",
            )

    # ------------------------------------------------------------- perfil
    with tabs[1]:
        perfiles = {t: trends.perfil_mensual(df[t]) for t in seleccion}
        perfiles = {k: v for k, v in perfiles.items() if not v.empty}
        if not perfiles:
            ui.sin_datos(
                "No hay suficientes observaciones para construir el perfil mensual."
            )
        else:
            st.plotly_chart(
                charts.perfil_estacional(perfiles), use_container_width=True
            )

            filas = []
            for t, p in perfiles.items():
                alto = p.loc[p["Índice estacional"].idxmax()]
                bajo = p.loc[p["Índice estacional"].idxmin()]
                fuerza = trends.fuerza_estacional(df[t])
                filas.append(
                    {
                        "Término": t,
                        "Mes de mayor interés": alto["Mes"],
                        "Índice del mes alto": alto["Índice estacional"],
                        "Mes de menor interés": bajo["Mes"],
                        "Índice del mes bajo": bajo["Índice estacional"],
                        "Amplitud (pp)": alto["Índice estacional"]
                        - bajo["Índice estacional"],
                        "Fuerza estacional": fuerza,
                    }
                )
            tabla = pd.DataFrame(filas)
            st.dataframe(
                tabla,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Índice del mes alto": st.column_config.NumberColumn(format="%.0f"),
                    "Índice del mes bajo": st.column_config.NumberColumn(format="%.0f"),
                    "Amplitud (pp)": st.column_config.NumberColumn(format="%.0f"),
                    "Fuerza estacional": st.column_config.NumberColumn(format="%.2f"),
                },
            )
            ui.nota_fuente(
                "Índice 100 equivale al promedio anual del término. La fuerza estacional va de 0 "
                "(sin patrón anual) a 1 (patrón anual dominante); se calcula descomponiendo la serie."
            )

            fuertes = tabla[tabla["Fuerza estacional"] > 0.6]
            if len(fuertes):
                detalle = "; ".join(
                    f"{r['Término']} concentra su pico en {r['Mes de mayor interés']} y su piso en "
                    f"{r['Mes de menor interés']}"
                    for _, r in fuertes.iterrows()
                )
                ui.hallazgo(
                    f"<b>Estacionalidad marcada en {len(fuertes)} término(s).</b> {detalle}. "
                    "Sirve para calendarizar compra de inventario y campañas, con el margen de que "
                    "el interés de búsqueda antecede pero no equivale a la venta.",
                    "ok",
                )
            débiles = tabla[tabla["Fuerza estacional"] < 0.3]
            if len(débiles):
                ui.hallazgo(
                    "<b>Sin estacionalidad aprovechable:</b> "
                    + ", ".join(débiles["Término"].astype(str))
                    + ". El patrón anual explica poco de su variación.",
                    "neutro",
                )

    # ------------------------------------------------------------- modelos
    with tabs[2]:
        st.markdown("### Selección de modelo por backtesting")
        st.caption(
            f"Validación estrictamente temporal: se entrena con todo menos los últimos "
            f"{settings.BACKTEST_HOLDOUT_MESES} meses y se evalúa contra esos meses reales (nunca "
            "aleatoria). Se compara Seasonal Naive, ETS y SARIMA; se descarta cualquier modelo cuyo "
            "pronóstico resulte esencialmente plano antes de decidir por error — ver Metodología."
        )

        termino = st.selectbox("Término", seleccion)
        serie = df[termino].dropna()

        with st.spinner(
            "Evaluando modelos (SARIMA y ETS ajustan una rejilla acotada por AICc)…"
        ):
            tabla, _ = _backtesting(serie)

        if tabla.empty:
            ui.sin_datos(
                f"La serie no tiene suficientes observaciones para un holdout de "
                f"{settings.BACKTEST_HOLDOUT_MESES} meses (se requieren al menos 24 meses de entrenamiento)."
            )
            return

        eleccion = trends.seleccionar_modelo(tabla)
        tipo_msg = "alerta" if eleccion["sin_senal"] else "ok"
        ui.hallazgo(
            f"<b>Modelo seleccionado: {eleccion['modelo']}</b>. {eleccion['explicacion']}",
            tipo_msg,
        )

        c1, c2 = st.columns([1.2, 1])
        with c1:
            st.dataframe(
                tabla,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "MAE": st.column_config.NumberColumn(format="%.2f"),
                    "RMSE": st.column_config.NumberColumn(format="%.2f"),
                    "MAPE %": st.column_config.NumberColumn(format="%.1f%%"),
                    "sMAPE %": st.column_config.NumberColumn(format="%.1f%%"),
                    "corr_forma": st.column_config.NumberColumn(format="%.2f"),
                    "rango_forecast": st.column_config.NumberColumn(format="%.1f"),
                    "rango_pct": st.column_config.NumberColumn(
                        "rango_pct %", format="%.1f%%"
                    ),
                    "descartado": st.column_config.CheckboxColumn(),
                },
            )
        with c2:
            st.plotly_chart(
                charts.comparacion_modelos(tabla, "RMSE"), use_container_width=True
            )
        ui.nota_fuente(
            "corr_forma: correlación entre el pronóstico y el valor real en el holdout (mide si se "
            "acierta la forma del año, no solo el nivel). rango_pct: amplitud del pronóstico como % "
            "de la media de la serie — cerca de 0 delata un pronóstico plano."
        )

        meses = st.slider("Meses a proyectar", 3, 24, 12)
        futuro = trends.pronostico_final(serie, eleccion["modelo"], meses)
        st.plotly_chart(
            charts.pronostico(serie, futuro, eleccion["modelo"]),
            use_container_width=True,
        )

        if not futuro.empty:
            f = futuro.copy()
            f["Mes"] = f["Fecha"].dt.strftime("%b %Y")
            pico = f.loc[f["Pronóstico"].idxmax()]
            valle = f.loc[f["Pronóstico"].idxmin()]
            fila_ganadora = eleccion["fila"]
            ui.fila_kpis(
                [
                    dict(
                        etiqueta="Mes con mayor interés histórico proyectado",
                        valor=pico["Mes"],
                        nota=f"Índice {pico['Pronóstico']:.0f} — ventana favorable para marketing",
                    ),
                    dict(
                        etiqueta="Mes con menor interés histórico proyectado",
                        valor=valle["Mes"],
                        nota=f"Índice {valle['Pronóstico']:.0f}",
                    ),
                    dict(
                        etiqueta="Error típico del modelo (holdout)",
                        valor=(
                            f"{fila_ganadora['MAE']:.1f} puntos de índice"
                            if fila_ganadora is not None
                            else "—"
                        ),
                        nota=(
                            f"RMSE {fila_ganadora['RMSE']:.1f}"
                            if fila_ganadora is not None
                            else ""
                        ),
                    ),
                ]
            )
            cols_mostrar = ["Mes", "Pronóstico"]
            if futuro["CI_inf"].notna().any():
                f["CI_inf"] = futuro["CI_inf"]
                f["CI_sup"] = futuro["CI_sup"]
                cols_mostrar += ["CI_inf", "CI_sup"]
            st.dataframe(
                f[cols_mostrar],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Pronóstico": st.column_config.NumberColumn(format="%.1f"),
                    "CI_inf": st.column_config.NumberColumn(
                        "IC 95% inferior", format="%.1f"
                    ),
                    "CI_sup": st.column_config.NumberColumn(
                        "IC 95% superior", format="%.1f"
                    ),
                },
            )
        ui.nota_fuente(
            "El pronóstico proyecta interés de búsqueda, no ventas: un mes con índice alto presenta "
            "históricamente mayor interés de búsqueda y podría ser una ventana favorable para "
            "marketing, no una promesa de que ese mes venderá más."
        )

    # --------------------------------------------------------- mapa por estado
    with tabs[3]:
        ui.mostrar_validacion(ctx.val_region, "Interés por subregión")
        columnas_region = _columnas_termino(ctx.region)

        if not columnas_region:
            ui.sin_datos(
                "No hay export de 'Interés por subregión' de Google Trends. Coloque el archivo en "
                "data/ (por ejemplo data/google_trends/OWFIT_REGIÓN.csv) y recargue la página."
            )
        elif not ctx.geojson_estados:
            ui.sin_datos(
                f"Falta el GeoJSON de estados en {settings.PATH_GEOJSON_ESTADOS}: el mapa no se "
                "puede dibujar."
            )
        else:
            opciones = _opciones_termino(ctx.region)
            lider_mapa = _termino_lider(ctx.region)
            termino_mapa = opciones[0]
            if len(opciones) > 1:
                termino_mapa = st.selectbox(
                    "Término de búsqueda",
                    opciones,
                    index=opciones.index(lider_mapa) if lider_mapa in opciones else 0,
                    key="mapa_termino",
                )

            d = _serie_region(ctx.region, termino_mapa).rename(
                columns={"valor": "Índice"}
            )
            fig = charts.mapa_mexico(d, ctx.geojson_estados, "Índice")
            if fig is not None:
                st.plotly_chart(
                    fig,
                    use_container_width=True,
                    config={"displayModeBar": False, "scrollZoom": False},
                )

            rr = _resumen_region(ctx.region, termino_mapa)
            if rr is not None:
                ui.fila_kpis(
                    [
                        dict(
                            etiqueta="Estado con mayor interés",
                            valor=str(rr["top"]["Estado"]),
                            icono="tendencia",
                            nota=f"Índice {rr['top']['valor']:.0f}/100",
                        ),
                        dict(
                            etiqueta="Concentración del top 3",
                            valor=f"{rr['share_top3']:.0f}%",
                            icono="porcentaje",
                            acento=True,
                            nota="del interés nacional · "
                            + ", ".join(rr["top3"]["Estado"].astype(str)),
                        ),
                        dict(
                            etiqueta=f"Estados por debajo de {settings.UMBRAL_INTERES_BAJO}/100",
                            valor=f"{rr['bajos']}",
                            icono="escala",
                            nota=f"de {rr['estados']} estados con dato",
                        ),
                    ]
                )

                with st.expander("Ver tabla por estado"):
                    tabla_region = (
                        rr["orden"]
                        .rename(columns={"valor": "Índice de interés"})
                        .reset_index(drop=True)
                    )
                    tabla_region.insert(0, "Ranking", range(1, len(tabla_region) + 1))
                    st.dataframe(
                        tabla_region,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "Índice de interés": st.column_config.NumberColumn(
                                format="%.0f"
                            ),
                        },
                    )

            suma = _suma_por_estado(ctx.region)
            nota = (
                "Índice de interés de búsqueda por estado (0-100), re-escalado por Google dentro de "
                "cada consulta: mide dónde se busca más el término, no dónde se vende más ni cuánto."
            )
            if suma is not None:
                nota += (
                    f" En este export los {len(columnas_region)} términos suman {suma:.0f} en cada "
                    "estado: son el reparto del interés entre ellos, no volúmenes independientes, "
                    "así que el mapa compara estados dentro de un término y no términos entre sí."
                )
            ui.nota_fuente(nota)

"""Gráficas del dashboard. Todas comparten tipografía, paleta y ejes."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from src.ui import COLORES, COLOR_SEGMENTO, SECUENCIA

FUENTE = dict(
    family="Inter Tight, system-ui, sans-serif", size=12, color=COLORES["tinta"]
)
FUENTE_EJE = dict(
    family="Inter Tight, system-ui, sans-serif", size=11, color=COLORES["gris"]
)


def _estilo(fig, alto: int = 380, leyenda: bool = True):
    fig.update_layout(
        font=FUENTE,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#FFFFFF",
        margin=dict(l=10, r=10, t=78 if leyenda else 48, b=10),
        height=alto,
        showlegend=leyenda,
        title=dict(
            y=0.98,
            yanchor="top",
            x=0,
            xanchor="left",
            font=dict(
                size=15,
                weight=600,
                family="Inter Tight, system-ui, sans-serif",
                color=COLORES["tinta"],
            ),
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.01,
            x=0,
            title=None,
            font=dict(size=12, color=COLORES["tinta"]),
        ),
        hoverlabel=dict(
            font_size=12,
            font_family="Inter Tight",
            bgcolor="#FFFFFF",
            bordercolor=COLORES["linea"],
            font_color=COLORES["tinta"],
        ),
        # transición suave cuando el simulador recalcula la misma figura con
        # nuevos valores: no cambia ningún dato, solo cómo se ve el cambio.
        transition=dict(duration=350, easing="cubic-in-out"),
    )
    fig.update_xaxes(
        showgrid=False,
        linecolor=COLORES["linea"],
        ticks="outside",
        tickcolor=COLORES["linea"],
        tickfont=FUENTE_EJE,
        title_font=dict(size=12, color=COLORES["gris"]),
    )
    fig.update_yaxes(
        gridcolor=COLORES["linea"],
        zeroline=False,
        tickfont=FUENTE_EJE,
        title_font=dict(size=12, color=COLORES["gris"]),
    )
    return fig


def sparkline(serie: pd.Series, color: str | None = None, alto: int = 60):
    """Mini gráfica de tendencia, sin ejes ni leyenda: solo la forma reciente de la serie."""
    fig = go.Figure(
        go.Scatter(
            x=list(range(len(serie))),
            y=serie.to_numpy(dtype=float),
            mode="lines",
            line=dict(color=color or COLORES["musgo"], width=2),
            hoverinfo="skip",
        )
    )
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        height=alto,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
    )
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return fig


# ------------------------------------------------------------------ mercado
def histograma_precios(
    df: pd.DataFrame,
    columna: str = "Precio_MXN",
    nbins: int = 40,
    titulo: str = "Distribución de precios",
):
    fig = px.histogram(
        df, x=columna, nbins=nbins, color_discrete_sequence=[COLORES["musgo"]]
    )
    mediana = df[columna].median()
    fig.add_vline(
        x=mediana,
        line_dash="dash",
        line_color=COLORES["rosa"],
        annotation_text=f"Mediana ${mediana:,.0f}",
        annotation_position="top right",
    )
    fig.update_layout(title=titulo, xaxis_title="Precio (MXN)", yaxis_title="Productos")
    return _estilo(fig, leyenda=False)


def boxplot_por(df: pd.DataFrame, dimension: str, titulo: str, log: bool = False):
    orden = df.groupby(dimension)["Precio_MXN"].median().sort_values().index.tolist()
    fig = px.box(
        df,
        x=dimension,
        y="Precio_MXN",
        points=False,
        category_orders={dimension: orden},
        color=dimension if dimension == "Segmento" else None,
        color_discrete_map=COLOR_SEGMENTO if dimension == "Segmento" else None,
        color_discrete_sequence=SECUENCIA,
    )
    if dimension != "Segmento":
        fig.update_traces(marker_color=COLORES["musgo"], line_color=COLORES["musgo"])
    fig.update_layout(title=titulo, xaxis_title=None, yaxis_title="Precio (MXN)")
    if log:
        fig.update_yaxes(type="log")
    return _estilo(fig, leyenda=dimension == "Segmento")


def precio_por_marca_categoria(df: pd.DataFrame, categoria: str):
    d = df[df["Categoria_norm"] == categoria]
    if d.empty:
        return None
    orden = d.groupby("Marca")["Precio_MXN"].median().sort_values().index.tolist()
    fig = px.box(
        d,
        x="Marca",
        y="Precio_MXN",
        color="Segmento",
        points="outliers",
        category_orders={"Marca": orden},
        color_discrete_map=COLOR_SEGMENTO,
    )
    fig.update_layout(
        title=f"Precios en {categoria} por marca",
        xaxis_title=None,
        yaxis_title="Precio (MXN)",
    )
    return _estilo(fig, alto=420)


def posicion_competitiva(
    ref: pd.Series,
    precio_owfit: float,
    precio_rec: float | None,
    categoria: str,
    percentiles: dict | None = None,
):
    """Distribución de la categoría con la posición de OWFIT marcada."""
    fig = go.Figure()
    fig.add_trace(
        go.Histogram(
            x=ref,
            nbinsx=30,
            marker_color=COLORES["salvia"],
            opacity=0.75,
            name="Competencia",
        )
    )
    if percentiles:
        for etiqueta, valor in percentiles.items():
            fig.add_vline(
                x=valor,
                line_width=1,
                line_dash="dot",
                line_color=COLORES["gris"],
                annotation_text=etiqueta,
                annotation_font_size=10,
                annotation_font_color=COLORES["gris"],
                annotation_position="bottom left",
            )
    if precio_owfit and np.isfinite(precio_owfit):
        fig.add_vline(
            x=precio_owfit,
            line_width=2.5,
            line_color=COLORES["rosa"],
            annotation_text=f"OWFIT ${precio_owfit:,.0f}",
            annotation_position="top left",
            annotation_font_size=11,
        )
    if precio_rec and np.isfinite(precio_rec):
        fig.add_vline(
            x=precio_rec,
            line_width=2.5,
            line_dash="dash",
            line_color=COLORES["musgo"],
            annotation_text=f"Recomendado ${precio_rec:,.0f}",
            annotation_position="bottom right",
            annotation_font_size=11,
        )
    fig.update_layout(
        title=f"Posición en {categoria}",
        xaxis_title="Precio (MXN)",
        yaxis_title="Productos de la competencia",
    )
    return _estilo(fig, leyenda=False)


def barras_comparacion(
    df: pd.DataFrame,
    x: str,
    series: list[str],
    titulo: str,
    eje_y: str = "MXN",
    horizontal: bool = False,
):
    fig = go.Figure()
    for i, s in enumerate(series):
        if horizontal:
            fig.add_trace(
                go.Bar(
                    y=df[x],
                    x=df[s],
                    name=s,
                    orientation="h",
                    marker_color=SECUENCIA[i % len(SECUENCIA)],
                )
            )
        else:
            fig.add_trace(
                go.Bar(
                    x=df[x], y=df[s], name=s, marker_color=SECUENCIA[i % len(SECUENCIA)]
                )
            )
    fig.update_layout(
        title=titulo,
        barmode="group",
        xaxis_title=None if not horizontal else eje_y,
        yaxis_title=eje_y if not horizontal else None,
    )
    return _estilo(fig)


def dispersión_precio_margen(tabla: pd.DataFrame):
    d = tabla.dropna(subset=["PVP actual", "Margen contribución actual %"])
    if d.empty:
        return None
    fig = px.scatter(
        d,
        x="PVP actual",
        y="Margen contribución actual %",
        color="Categoría",
        size=d["Cantidad"].fillna(1) if "Cantidad" in d else None,
        hover_name="Producto",
        color_discrete_sequence=SECUENCIA,
    )
    fig.add_hline(y=0, line_color=COLORES["negativo"], line_width=1)
    fig.update_layout(
        title="Precio contra margen de contribución por producto",
        xaxis_title="PVP actual (MXN)",
        yaxis_title="Margen de contribución (%)",
    )
    return _estilo(fig, alto=430)


def cascada_costos(
    pvp: float, cogs: float, costo_var: float, costo_envio: float, utilidad: float
):
    valores = [pvp, -cogs, -costo_var, -costo_envio, utilidad]
    fig = go.Figure(
        go.Waterfall(
            orientation="v",
            measure=["absolute", "relative", "relative", "relative", "total"],
            x=[
                "PVP",
                "COGS",
                "Pasarela + publicidad",
                "Envío + material",
                "Utilidad por unidad",
            ],
            y=[pvp, -cogs, -costo_var, -costo_envio, 0],
            text=[f"${v:,.0f}" for v in valores],
            connector=dict(line=dict(color=COLORES["linea"])),
            decreasing=dict(marker=dict(color=COLORES["salvia"])),
            increasing=dict(marker=dict(color=COLORES["musgo"])),
            totals=dict(
                marker=dict(
                    color=COLORES["negativo"] if utilidad < 0 else COLORES["musgo"]
                )
            ),
            textposition="outside",
        )
    )
    fig.update_layout(
        title="De precio de venta a utilidad por unidad", yaxis_title="MXN"
    )
    return _estilo(fig, alto=380, leyenda=False)


# ------------------------------------------------------------------ encuesta
def curvas_van_westendorp(vw: dict):
    fig = go.Figure()
    colores = {
        "Demasiado barato": COLORES["gris"],
        "Barato / buena relación": COLORES["salvia"],
        "Caro": COLORES["ocre"],
        "Demasiado caro": COLORES["negativo"],
    }
    for nombre, y in vw["curvas"].items():
        fig.add_trace(
            go.Scatter(
                x=vw["malla"],
                y=y,
                name=nombre,
                mode="lines",
                line=dict(color=colores[nombre], width=2),
            )
        )
    for etiqueta, valor in vw["puntos"].items():
        fig.add_vline(
            x=valor,
            line_dash="dot",
            line_width=1,
            line_color=COLORES["tinta"],
            annotation_text=f"{etiqueta} ${valor:,.0f}",
            annotation_font_size=10,
        )
    fig.update_layout(
        title="Sensibilidad al precio (Van Westendorp)",
        xaxis_title="Precio (MXN)",
        yaxis_title="% de encuestados",
    )
    return _estilo(fig, alto=420)


def curva_gabor_granger(gg: pd.DataFrame):
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=gg["Precio"],
            y=gg["% top-2-box"],
            mode="lines+markers",
            name="Intención alta (4-5)",
            line=dict(color=COLORES["musgo"], width=2.5),
        )
    )
    if "Ingreso relativo (índice)" in gg:
        fig.add_trace(
            go.Scatter(
                x=gg["Precio"],
                y=gg["Ingreso relativo (índice)"],
                mode="lines+markers",
                name="Ingreso esperado (índice)",
                line=dict(color=COLORES["premium"], width=2, dash="dash"),
            )
        )
    fig.update_layout(
        title="Intención de compra por punto de precio",
        xaxis_title="Precio (MXN)",
        yaxis_title="%",
    )
    return _estilo(fig)


def barras_horizontales(
    df: pd.DataFrame,
    categoria: str,
    valor: str,
    titulo: str,
    color: str = None,
    eje: str = "%",
):
    d = df.sort_values(valor)
    fig = px.bar(
        d,
        x=valor,
        y=categoria,
        orientation="h",
        color_discrete_sequence=[color or COLORES["musgo"]],
    )
    fig.update_layout(title=titulo, xaxis_title=eje, yaxis_title=None)
    return _estilo(fig, alto=max(240, 34 * len(d) + 90), leyenda=False)


# ------------------------------------------------------------------ región
# Escala secuencial claro -> azul intenso. Se declara en cinco tramos duros
# (cada color ocupa exactamente un quinto) para que el mapa lea como cinco
# clases y no como un degradado continuo.
ESCALA_REGION = ["#E3ECF4", "#B4CCE2", "#7FA6CC", "#4B7CB0", "#1F4E79"]
_MAPA_FONDO = "#161B21"


def _escala_escalonada(colores: list[str]) -> list[list]:
    n = len(colores)
    escala = []
    for i, c in enumerate(colores):
        escala.append([i / n, c])
        escala.append([(i + 1) / n, c])
    return escala


def mapa_mexico(
    df: pd.DataFrame,
    geojson: dict,
    columna: str,
    columna_estado: str = "Estado",
    titulo: str | None = None,
):
    """Choropleth de los 32 estados con el índice de interés de búsqueda.

    `df` ya viene empatado contra el GeoJSON por `loaders.cargar_region`; aquí
    solo se calculan el ranking y la diferencia contra la mediana nacional para
    mostrarlos en el hover. No se altera ningún valor del índice.
    """
    if df.empty or columna not in df.columns or not geojson:
        return None

    d = df[[columna_estado, columna]].dropna().copy()
    if d.empty:
        return None

    mediana = float(d[columna].median())
    d["_ranking"] = d[columna].rank(ascending=False, method="min").astype(int)
    d["_vs_mediana"] = d[columna] - mediana
    total = len(d)

    fig = px.choropleth(
        d,
        geojson=geojson,
        locations=columna_estado,
        featureidkey="properties.name",
        color=columna,
        color_continuous_scale=_escala_escalonada(ESCALA_REGION),
        custom_data=["_ranking", "_vs_mediana"],
    )
    fig.update_traces(
        marker_line_color="rgba(255,255,255,0.32)",
        marker_line_width=0.5,
        hovertemplate=(
            "<b>%{location}</b><br>"
            "Índice de interés: %{z:.0f}/100<br>"
            "Ranking: #%{customdata[0]} de " + str(total) + "<br>"
            "Contra la mediana nacional: %{customdata[1]:+.0f} puntos"
            "<extra></extra>"
        ),
    )
    fig.update_geos(
        fitbounds="locations",
        visible=False,
        bgcolor=_MAPA_FONDO,
        showframe=False,
        showcoastlines=False,
        showland=False,
    )
    # `title` solo se incluye si hay texto: pasar title=None deja un dict vacío
    # en el layout y Plotly.js dibuja la cadena "undefined" sobre el mapa.
    if titulo:
        fig.update_layout(
            title=dict(
                text=titulo,
                y=0.98,
                yanchor="top",
                x=0,
                xanchor="left",
                font=dict(size=15, weight=600, color=COLORES["tinta"]),
            )
        )
    fig.update_layout(
        font=FUENTE,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=46 if titulo else 8, b=0),
        height=520,
        hoverlabel=dict(
            font_size=12,
            font_family="Inter Tight",
            bgcolor="#FFFFFF",
            bordercolor=COLORES["linea"],
            font_color=COLORES["tinta"],
        ),
        coloraxis_colorbar=dict(
            orientation="h",
            y=-0.06,
            yanchor="top",
            x=0.5,
            xanchor="center",
            thickness=10,
            len=0.62,
            outlinewidth=0,
            ticks="outside",
            ticklen=4,
            tickfont=dict(size=10, color=COLORES["gris"]),
            title=dict(
                text="Menor interés  →  Mayor interés",
                side="top",
                font=dict(size=11, color=COLORES["gris"]),
            ),
        ),
    )
    return fig


# ------------------------------------------------------------------ trends
def serie_trends(df: pd.DataFrame, columnas: list[str]):
    fig = go.Figure()
    for i, c in enumerate(columnas):
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df[c],
                name=c,
                mode="lines",
                line=dict(width=2, color=SECUENCIA[i % len(SECUENCIA)]),
            )
        )
    fig.update_layout(
        title="Índice de interés de búsqueda",
        xaxis_title=None,
        yaxis_title="Índice (0-100)",
    )
    return _estilo(fig, alto=380)


def perfil_estacional(perfiles: dict[str, pd.DataFrame]):
    fig = go.Figure()
    for i, (nombre, p) in enumerate(perfiles.items()):
        fig.add_trace(
            go.Scatter(
                x=p["Mes"],
                y=p["Índice estacional"],
                name=nombre,
                mode="lines+markers",
                line=dict(width=2, color=SECUENCIA[i % len(SECUENCIA)]),
            )
        )
    fig.add_hline(
        y=100,
        line_dash="dot",
        line_color=COLORES["gris"],
        annotation_text="Promedio del año",
        annotation_font_size=10,
    )
    fig.update_layout(
        title="Perfil estacional por mes",
        xaxis_title=None,
        yaxis_title="Índice (100 = promedio anual)",
    )
    return _estilo(fig)


def pronostico(historico: pd.Series, futuro: pd.DataFrame, nombre_modelo: str):
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=historico.index,
            y=historico.values,
            name="Histórico",
            line=dict(color=COLORES["musgo"], width=2),
        )
    )
    if not futuro.empty:
        puente_x = [historico.index[-1]] + list(futuro["Fecha"])
        puente_y = [historico.iloc[-1]] + list(futuro["Pronóstico"])
        if "CI_inf" in futuro and futuro["CI_inf"].notna().any():
            puente_inf = [historico.iloc[-1]] + list(futuro["CI_inf"])
            puente_sup = [historico.iloc[-1]] + list(futuro["CI_sup"])
            fig.add_trace(
                go.Scatter(
                    x=puente_x,
                    y=puente_sup,
                    name="IC 95% superior",
                    line=dict(width=0),
                    showlegend=False,
                    hoverinfo="skip",
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=puente_x,
                    y=puente_inf,
                    name="IC 95%",
                    fill="tonexty",
                    fillcolor="rgba(176,52,92,0.12)",
                    line=dict(width=0),
                    hoverinfo="skip",
                )
            )
        fig.add_trace(
            go.Scatter(
                x=puente_x,
                y=puente_y,
                name=f"Pronóstico ({nombre_modelo})",
                line=dict(color=COLORES["rosa"], width=2, dash="dash"),
            )
        )
    fig.update_layout(
        title="Interés de búsqueda observado y proyectado",
        xaxis_title=None,
        yaxis_title="Índice (0-100)",
    )
    return _estilo(fig)


def pronostico_escenario(
    historico: pd.Series,
    futuro_base: pd.DataFrame,
    futuro_ajustado: pd.DataFrame,
    nombre_modelo: str,
    nombre_escenario: str,
):
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=historico.index,
            y=historico.values,
            name="Histórico",
            line=dict(color=COLORES["musgo"], width=2),
        )
    )
    if not futuro_base.empty:
        puente_x = [historico.index[-1]] + list(futuro_base["Fecha"])
        puente_y_base = [historico.iloc[-1]] + list(futuro_base["Pronóstico"])
        fig.add_trace(
            go.Scatter(
                x=puente_x,
                y=puente_y_base,
                name=f"Pronóstico base ({nombre_modelo})",
                line=dict(color=COLORES["gris"], width=2, dash="dot"),
            )
        )
        puente_y_adj = [historico.iloc[-1]] + list(futuro_ajustado["Pronóstico"])
        fig.add_trace(
            go.Scatter(
                x=puente_x,
                y=puente_y_adj,
                name=f"Ajustado · {nombre_escenario}",
                line=dict(color=COLORES["rosa"], width=2, dash="dash"),
            )
        )
    fig.update_layout(
        title="Interés de búsqueda: pronóstico base vs. ajuste cualitativo por escenario",
        xaxis_title=None,
        yaxis_title="Índice (0-100)",
    )
    return _estilo(fig)


def comparacion_modelos(tabla: pd.DataFrame, metrica: str = "MAE"):
    d = tabla.sort_values(metrica, ascending=False)
    tiene_descarte = "descartado" in d.columns
    if tiene_descarte:
        elegibles = d[~d["descartado"]]
        mejor = elegibles.iloc[-1]["Modelo"] if not elegibles.empty else None
        colores = [
            (
                COLORES["gris"]
                if row["descartado"]
                else (COLORES["musgo"] if row["Modelo"] == mejor else COLORES["salvia"])
            )
            for _, row in d.iterrows()
        ]
    else:
        colores = [
            COLORES["musgo"] if m == d.iloc[-1]["Modelo"] else COLORES["salvia"]
            for m in d["Modelo"]
        ]
    fig = go.Figure(
        go.Bar(
            x=d[metrica],
            y=d["Modelo"],
            orientation="h",
            marker_color=colores,
            texttemplate="%{x:.2f}",
            textposition="outside",
        )
    )
    fig.update_layout(
        title=f"Error de pronóstico por modelo ({metrica}, menor es mejor"
        + (" · gris = descartado por pronóstico plano)" if tiene_descarte else ")"),
        xaxis_title=metrica,
        yaxis_title=None,
    )
    return _estilo(fig, alto=300, leyenda=False)


# ------------------------------------------------------------------ promociones
# Relleno de la banda de cada periodo promocional. El color va con la
# profundidad del descuento: ocre = atención (15/20%), rojo = tramo más bajo
# del proxy (25%), consistente con el semáforo del resto del dashboard.
_RELLENO_PROMO = {
    15.0: "rgba(193,160,99,0.13)",
    20.0: "rgba(193,160,99,0.24)",
    25.0: "rgba(166,80,58,0.16)",
}


def _color_promo(descuento: float) -> str:
    return COLORES["negativo"] if descuento >= 25 else COLORES["ocre"]


def promociones_escenario(
    plan: pd.DataFrame,
    historico_proxy: pd.Series | None,
    nombre_escenario: str,
    umbral: float = 0.70,
    meses_contexto: int = 12,
):
    """Serie del proxy de demanda con la regla de temporada dibujada encima.

    No sustituye a `pronostico_escenario` (índice 0-100, base vs. ajustado):
    esta trabaja sobre el proxy 0-1 del escenario y responde otra pregunta —en
    qué meses se activa una promoción y de cuánto—, con la línea del umbral
    como referencia de lectura inmediata.
    """
    fig = go.Figure()
    if plan is None or plan.empty:
        return _estilo(fig, alto=430)

    # Banda de cada periodo promocional: medio mes a cada lado de la marca,
    # para que se lea como "el mes de abril", no como "el instante 1-abr".
    for _, r in plan[plan["Estado"] == "Temporada baja"].iterrows():
        centro = pd.Timestamp(r["Fecha"])
        fig.add_vrect(
            x0=centro - pd.Timedelta(days=15),
            x1=centro + pd.Timedelta(days=15),
            fillcolor=_RELLENO_PROMO.get(
                float(r["Descuento %"]), "rgba(193,160,99,0.16)"
            ),
            line_width=0,
            layer="below",
        )

    if historico_proxy is not None and len(historico_proxy) > 0:
        ctx_serie = historico_proxy.iloc[-meses_contexto:]
        fig.add_trace(
            go.Scatter(
                x=ctx_serie.index,
                y=ctx_serie.to_numpy(dtype=float),
                name="Histórico observado",
                mode="lines",
                line=dict(color=COLORES["salvia"], width=1.8),
                hovertemplate="%{x|%b %Y}<br>Proxy de demanda: %{y:.2f}<extra></extra>",
            )
        )

    # Puente visual entre el último dato observado y el primer pronóstico: sin
    # él la línea del escenario arranca flotando en el aire.
    x_linea, y_linea = list(plan["Fecha"]), list(plan["Proxy"])
    if historico_proxy is not None and len(historico_proxy) > 0:
        x_linea = [historico_proxy.index[-1]] + x_linea
        y_linea = [float(historico_proxy.iloc[-1])] + y_linea
    fig.add_trace(
        go.Scatter(
            x=x_linea,
            y=y_linea,
            name=f"Proxy proyectado · {nombre_escenario}",
            mode="lines",
            line=dict(color=COLORES["musgo"], width=2.2, dash="dash"),
            hoverinfo="skip",
        )
    )

    hover = (
        "<b>%{customdata[0]}</b><br>"
        "Proxy de demanda: %{y:.2f}<br>"
        "Estado: %{customdata[1]}<br>"
        "Descuento: %{customdata[2]}<br>"
        "PVP: %{customdata[3]}<br>"
        "Precio promocional: %{customdata[4]}<br>"
        "Ingreso estimado: %{customdata[5]}<br>"
        "Utilidad estimada: %{customdata[6]}"
        "<extra></extra>"
    )

    def _cd(d: pd.DataFrame):
        def m(x, dec=0):
            return "—" if not np.isfinite(x) else f"${x:,.{dec}f}"

        return [
            [
                r["Periodo"],
                r["Estado"],
                f"{r['Descuento %']:.0f}%",
                m(r["PVP"]),
                m(r["Precio promocional"]),
                m(r["Ingreso estimado"]),
                m(r["Utilidad estimada"]),
            ]
            for _, r in d.iterrows()
        ]

    altas = plan[plan["Estado"] == "Temporada alta"]
    if not altas.empty:
        fig.add_trace(
            go.Scatter(
                x=altas["Fecha"],
                y=altas["Proxy"],
                name="Temporada alta · precio regular",
                mode="markers",
                marker=dict(
                    color=COLORES["musgo"],
                    size=10,
                    line=dict(color="#FFFFFF", width=1.5),
                ),
                customdata=_cd(altas),
                hovertemplate=hover,
            )
        )

    bajas = plan[plan["Estado"] == "Temporada baja"]
    if not bajas.empty:
        fig.add_trace(
            go.Scatter(
                x=bajas["Fecha"],
                y=bajas["Proxy"],
                name="Temporada baja · promoción activada",
                mode="markers+text",
                text=[f"PROMO {d:.0f}%" for d in bajas["Descuento %"]],
                textposition="bottom center",
                textfont=dict(
                    size=10,
                    color=COLORES["negativo"],
                    family="Inter Tight, system-ui, sans-serif",
                ),
                marker=dict(
                    color=[_color_promo(d) for d in bajas["Descuento %"]],
                    size=12,
                    symbol="circle",
                    line=dict(color="#FFFFFF", width=1.5),
                ),
                customdata=_cd(bajas),
                hovertemplate=hover,
            )
        )

    fig.add_hline(
        y=umbral,
        line_dash="dash",
        line_width=1.6,
        line_color=COLORES["rosa"],
        annotation_text=f"Umbral {umbral:.2f} · arriba precio regular, abajo promoción",
        annotation_position="top left",
        annotation_font_size=11,
        annotation_font_color=COLORES["rosa"],
    )
    fig.update_layout(
        title=f"Proxy de demanda y activación de promociones · {nombre_escenario}",
        xaxis_title=None,
        yaxis_title="Proxy de demanda (0-1)",
    )
    fig.update_yaxes(range=[-0.06, 1.12], dtick=0.2)
    return _estilo(fig, alto=430)

"""Simulador de pricing producto por producto."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config import settings
from src import charts, market, pricing, ui
from src.ui import COLORES
from src.utils import money, pct


def render(ctx):
    ui.kicker("Simulador")
    st.title("Simulador")
    st.caption(
        "Mueva los parámetros y observe el efecto inmediato sobre el precio recomendado, "
        "la utilidad por unidad y la posición frente a la competencia."
    )
    ui.cinta_origen(ctx.es_demo, ctx.nombre_archivo)

    if not ctx.val_internos.ok or ctx.tabla.empty:
        st.stop()

    t = ctx.tabla
    p = ctx.params

    productos = t["Producto"].dropna().astype(str).tolist()
    col_a, col_b = st.columns([2, 1])
    with col_a:
        producto = st.selectbox("Producto", productos)
    fila = t[t["Producto"].astype(str) == producto].iloc[0]
    cat = fila["Categoría"]
    with col_b:
        st.markdown(f"**Categoría:** {cat}  \n**COGS:** {money(fila['COGS'])}")

    ref, pesos = market.referencia_precios(ctx.competencia, cat, p.balancear_marcas)
    percentiles_cat = (
        {q: market.cuantil_ponderado(ref, pesos, q / 100) for q in (25, 50, 75)}
        if not ref.empty
        else {}
    )

    # ------------------------------------------------------------- controles
    st.markdown("### Controles")
    st.caption(
        "Parten de los valores de la barra lateral. Lo que cambie aquí es solo para esta "
        "simulación: no se guarda ni afecta el Resumen, Pricing ni ninguna otra página."
    )
    c1, c2 = st.columns(2)
    with c1:
        percentil = st.select_slider(
            "Percentil competitivo",
            options=settings.PERCENTILES_OBJETIVO,
            value=p.percentil_objetivo,
            format_func=lambda v: f"P{v}",
            key="sim_percentil",
        )
    with c2:
        margen_obj = st.slider(
            "Margen objetivo (%)",
            0,
            70,
            int(p.margen_objetivo_pct),
            1,
            key="sim_margen",
        )

    with st.expander("Ajustar costos solo para esta simulación", expanded=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            pasarela = st.number_input(
                "Pasarela (%)",
                0.0,
                30.0,
                float(p.pasarela_pct),
                0.5,
                key="sim_pasarela",
            )
            publicidad = st.number_input(
                "Publicidad (%)",
                0.0,
                50.0,
                float(p.publicidad_pct),
                0.5,
                key="sim_publicidad",
            )
        with c2:
            envio = st.number_input(
                "Envío ($)", 0.0, 1000.0, float(p.envio_mxn), 1.0, key="sim_envio"
            )
            material = st.number_input(
                "Material de envío ($)",
                0.0,
                500.0,
                float(p.material_envio_mxn),
                1.0,
                key="sim_material",
            )
        with c3:
            otros = st.number_input(
                "Otros variables (%)",
                0.0,
                50.0,
                float(p.otros_variables_pct),
                0.5,
                key="sim_otros",
            )
            absorbido = st.slider(
                "Envío absorbido (%)",
                0,
                100,
                int(p.pct_envio_absorbido),
                5,
                key="sim_absorbido",
            )

    sim = pricing.Parametros(
        pasarela_pct=pasarela,
        publicidad_pct=publicidad,
        otros_variables_pct=otros,
        envio_mxn=envio,
        material_envio_mxn=material,
        pct_envio_absorbido=absorbido,
        margen_objetivo_pct=margen_obj,
        percentil_objetivo=percentil,
        redondeo=p.redondeo,
        min_comparables=p.min_comparables,
        balancear_marcas=p.balancear_marcas,
        modo=p.modo,
    )

    # ------------------------------------------------------------- cálculo
    interno_fila = ctx.internos[ctx.internos["Producto"].astype(str) == producto]
    res = pricing.calcular_precio_recomendado(interno_fila, ctx.competencia, sim)
    r = res.iloc[0]

    pvp_actual = (
        float(fila["PVP actual"]) if np.isfinite(fila["PVP actual"]) else np.nan
    )
    precio_rec = (
        float(r["Precio recomendado"])
        if np.isfinite(r["Precio recomendado"])
        else np.nan
    )

    st.markdown("### Resultado")
    dif_abs = (
        precio_rec - pvp_actual
        if np.isfinite(precio_rec) and np.isfinite(pvp_actual)
        else np.nan
    )
    dif_pct = (
        (precio_rec / pvp_actual - 1) * 100
        if np.isfinite(dif_abs) and pvp_actual
        else np.nan
    )
    eco_rec = pricing.economia_unitaria(precio_rec, r["COGS"], sim)
    eco_act = pricing.economia_unitaria(pvp_actual, r["COGS"], sim)

    ui.fila_kpis(
        [
            dict(etiqueta="Precio actual", valor=money(pvp_actual)),
            dict(
                etiqueta=f"Precio recomendado (P{percentil})",
                valor=money(precio_rec),
                delta=(
                    f"{'+' if dif_pct > 0 else ''}{dif_pct:.1f}%"
                    if np.isfinite(dif_pct)
                    else None
                ),
                positivo=bool(np.isfinite(dif_pct) and dif_pct >= 0),
                acento=True,
            ),
            dict(etiqueta="Diferencia", valor=money(dif_abs), nota=f"{r['Criterio']}"),
            dict(
                etiqueta="Utilidad por unidad",
                valor=money(eco_rec["utilidad_unidad"]),
                delta=f"{money(eco_act['utilidad_unidad'])} hoy",
                positivo=eco_rec["utilidad_unidad"] >= eco_act["utilidad_unidad"],
            ),
        ]
    )
    ui.fila_kpis(
        [
            dict(
                etiqueta="Margen bruto",
                valor=pct(eco_rec["margen_bruto"] * 100),
                nota="(PVP − COGS) / PVP",
            ),
            dict(
                etiqueta="Margen de contribución estimado",
                valor=pct(eco_rec["margen_contribucion"] * 100),
                delta=f"{pct(eco_act['margen_contribucion'] * 100)} hoy",
                positivo=eco_rec["margen_contribucion"]
                >= eco_act["margen_contribucion"],
            ),
            dict(
                etiqueta="Posición frente a la competencia",
                valor=(
                    f"P{r['Percentil recomendado']:.0f}"
                    if np.isfinite(r["Percentil recomendado"])
                    else "—"
                ),
                nota=(
                    f"Hoy en P{r['Percentil actual']:.0f} · {r['Posición actual']}"
                    if np.isfinite(r["Percentil actual"])
                    else "Sin comparables suficientes"
                ),
            ),
            dict(
                etiqueta="Comparables en la categoría",
                valor=f"{int(r['Competidores comparables'])}",
                nota=f"{int(r['Marcas comparables'])} marca(s)",
            ),
        ]
    )

    if r["Conflicto"]:
        ui.hallazgo(r["Conflicto"], "alerta")

    if percentiles_cat:
        ui.precio_target(
            pvp_actual,
            precio_rec,
            p25=percentiles_cat.get(25),
            p50=percentiles_cat.get(50),
            p75=percentiles_cat.get(75),
            titulo=f"Posición del precio en {cat}",
        )

    # ------------------------------------------------------------- gráficas
    c1, c2 = st.columns([1, 1])
    with c1:
        if np.isfinite(precio_rec):
            st.plotly_chart(
                charts.cascada_costos(
                    precio_rec,
                    r["COGS"],
                    eco_rec["costo_variable_pct"],
                    eco_rec["costo_envio"],
                    eco_rec["utilidad_unidad"],
                ),
                use_container_width=True,
            )
    with c2:
        if not ref.empty:
            percentiles = {f"P{q}": v for q, v in percentiles_cat.items()}
            st.plotly_chart(
                charts.posicion_competitiva(
                    ref, pvp_actual, precio_rec, cat, percentiles
                ),
                use_container_width=True,
            )
        else:
            ui.sin_datos(
                f"No hay comparables de '{cat}' en el conjunto competitivo elegido."
            )

    # ------------------------------------------------ sensibilidad al precio
    st.markdown("### Sensibilidad al precio")
    if np.isfinite(pvp_actual) and pvp_actual > 0:
        lo, hi = pvp_actual * 0.6, max(
            pvp_actual * 1.8, precio_rec * 1.2 if np.isfinite(precio_rec) else 0
        )
        malla = np.linspace(lo, hi, 80)
        utilidades = [
            pricing.economia_unitaria(x, r["COGS"], sim)["utilidad_unidad"]
            for x in malla
        ]
        margenes = [
            pricing.economia_unitaria(x, r["COGS"], sim)["margen_contribucion"] * 100
            for x in malla
        ]

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=malla,
                y=utilidades,
                name="Utilidad por unidad ($)",
                line=dict(color=COLORES["musgo"], width=2.5),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=malla,
                y=margenes,
                name="Margen de contribución (%)",
                line=dict(color=COLORES["salvia"], width=2, dash="dot"),
                yaxis="y2",
            )
        )
        fig.add_vline(
            x=pvp_actual,
            line_color=COLORES["gris"],
            line_dash="dash",
            annotation_text="Precio actual",
            annotation_font_size=10,
        )
        if np.isfinite(precio_rec):
            fig.add_vline(
                x=precio_rec,
                line_color=COLORES["rosa"],
                annotation_text="Recomendado",
                annotation_font_size=10,
            )
        fig.add_hline(y=0, line_color=COLORES["negativo"], line_width=1)
        fig.update_layout(
            title="Cómo cambian utilidad y margen con el precio",
            xaxis_title="Precio de venta (MXN)",
            yaxis=dict(title="Utilidad por unidad (MXN)"),
            yaxis2=dict(
                title="Margen de contribución (%)",
                overlaying="y",
                side="right",
                showgrid=False,
            ),
        )
        st.plotly_chart(charts._estilo(fig, alto=400), use_container_width=True)

        punto_equilibrio = pricing.precio_piso_por_margen(r["COGS"], sim, 0.0)
        ui.nota_fuente(
            f"El precio de equilibrio (utilidad cero por unidad) con estos parámetros es "
            f"{money(punto_equilibrio)}. Por debajo de ese precio cada venta resta utilidad."
        )

    # ------------------------------------------------ escenarios de percentil
    st.markdown("### Precio recomendado según el percentil objetivo")
    filas = []
    for q in settings.PERCENTILES_OBJETIVO:
        sim_q = pricing.Parametros(**{**sim.como_dict(), "percentil_objetivo": q})
        rq = pricing.calcular_precio_recomendado(
            interno_fila, ctx.competencia, sim_q
        ).iloc[0]
        filas.append(
            {
                "Percentil": f"P{q}",
                "Precio recomendado": rq["Precio recomendado"],
                "Cambio % vs actual": rq["Cambio %"],
                "Utilidad por unidad": rq["Utilidad recomendada"],
                "Margen de contribución %": rq["Margen contribución recomendado %"],
                "Criterio": rq["Criterio"],
            }
        )
    st.dataframe(
        pd.DataFrame(filas),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Precio recomendado": st.column_config.NumberColumn(format="$%,.0f"),
            "Cambio % vs actual": st.column_config.NumberColumn(format="%.1f%%"),
            "Utilidad por unidad": st.column_config.NumberColumn(format="$%,.0f"),
            "Margen de contribución %": st.column_config.NumberColumn(format="%.1f%%"),
        },
    )
    ui.nota_fuente(
        "Si varios percentiles devuelven el mismo precio, el piso de rentabilidad está mandando "
        "sobre la referencia de mercado con los costos configurados."
    )

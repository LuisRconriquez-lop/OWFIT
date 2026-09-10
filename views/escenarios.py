"""Escenarios de planeación estratégica para OWFIT / Grupo Garmac.

Cuatro escenarios cualitativos (no son un pronóstico estadístico) que combinan
el canal B2C (marca OWFIT) y el canal B2B (maquila Garmac / Garmac Wear) bajo
distintos supuestos de mercado, costos y ejecución. Sirven para estresar el
pricing y la planeación de inventario contra contextos razonables, del más
adverso al más favorable.

El pronóstico de interés de búsqueda (ARIMA/SARIMA, elegido por backtesting en
la página Estacionalidad) se puede ajustar con un multiplicador cualitativo por
escenario solo para ilustrar la dirección del efecto — nunca es una predicción
de ventas.
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pandas as pd
import streamlit as st

from config import settings
from src import charts, pricing, promos, trends, ui
from src.utils import money, num, pct

ESCENARIOS = [
    {
        "id": "pesimista",
        "numero": 1,
        "nombre": "Presión Externa y Márgenes Estrangulados",
        "tono": "Pesimista",
        "canal": "Mixto (B2C + B2B)",
        "multiplicador": 0.85,
        # Supuestos de costo/margen leídos de la narrativa de ESTE escenario (no
        # declarados por el usuario ni estimados de los datos): se usan para el
        # precio recomendado por prenda de "Plan promocional por temporada".
        "parametros": {
            "margen_objetivo_pct": 25.0,  # texto: margen unitario "< 30%", al costo
            "publicidad_pct": 20.0,  # texto: CAC insostenible por pauta digital directa
            "material_envio_mxn": 15.0,  # texto: "bolsa plástica convencional" (bajo el estándar de $27)
            "percentil_objetivo": 30,  # texto: "pricing de penetración agresivo"
        },
        "kpis": [
            dict(
                etiqueta="Margen unitario",
                valor="< 30%",
                nota="Pricing de penetración, al costo",
            ),
            dict(
                etiqueta="Canal de adquisición",
                valor="Pauta digital directa",
                nota="CAC insostenible vs. ticket bajo",
            ),
            dict(
                etiqueta="Empaque",
                valor="Bolsa plástica convencional",
                nota="Se mancha en tránsito",
            ),
            dict(
                etiqueta="Reposición desde Colombia",
                valor="35–45 días",
                nota="Lotes piloto pequeños, revisión manual",
            ),
        ],
        "texto": """El proyecto arranca en un entorno adverso donde la importación de materia prima enfrenta un
encarecimiento severo por fluctuaciones cambiarias y sobrecostos en fletes internacionales. Esta
fricción de abastecimiento se agrava porque las marcas deportivas transnacionales consolidadas
(como Nike, Puma o Adidas) saturan los escaparates liquidando saldos con descuentos predatorios,
orillando a las consumidoras a una postura defensiva que prioriza prendas básicas únicamente por
necesidad de reemplazo económico.

Ante este panorama hostil, Grupo Garmac restringe su manufactura a lotes piloto pequeños con
revisión manual para mitigar riesgos de inventario, viéndose obligado a fijar un pricing de
penetración agresivo con márgenes unitarios raspados al costo (inferiores al 30%). Sin margen
para absorber promociones, el proyecto vuelca sus esfuerzos en pauta digital directa en redes
sociales, lo que dispara el costo de adquisición de clientes (CAC) a niveles insostenibles frente
al bajo ticket obtenido en su tienda en línea.

A esto se suma el impacto negativo en la percepción del consumidor al recibir las prendas en
bolsas plásticas convencionales que se manchan con el roce del transporte, mientras que los
tiempos de reposición desde Colombia se dilatan entre 35 y 45 días. El resultado es un flujo de
efectivo deficitario donde la división tradicional de maquila B2B se ve forzada a transferir
capital para subsidiar las pérdidas operativas de la marca.""",
    },
    {
        "id": "base",
        "numero": 2,
        "nombre": "E-commerce Inercial con Fricción Comercial",
        "tono": "Tendencial / Base",
        "canal": "B2C",
        "multiplicador": 1.0,
        # Cifras exactas del texto: "empaque comercial estándar de $7.87 MXN" y
        # "logística nacional de paquetería de $129 a $130 MXN" (promedio).
        "parametros": {
            "material_envio_mxn": 7.87,
            "envio_mxn": 129.5,
        },
        "kpis": [
            dict(
                etiqueta="Rango de precio",
                valor="$450–$750 MXN",
                nota="Precio analítico de rango medio",
            ),
            dict(
                etiqueta="Envío gratis desde",
                valor="$700 MXN",
                nota="Empuja la segunda prenda",
            ),
            dict(etiqueta="Empaque", valor="$7.87 MXN", nota="Comercial estándar"),
            dict(etiqueta="Envío nacional", valor="$129–$130 MXN", nota="Por envío"),
            dict(
                etiqueta="Resultado",
                valor="Punto de equilibrio",
                nota="Sin excedente para Garmac Wear",
            ),
        ],
        "texto": """La empresa opera sobre una cadena de importación textil estable y predecible desde Colombia,
pero se enfrenta a una proliferación constante de marcas independientes mexicanas que compiten
activamente por visibilidad en canales digitales. La demanda en el segmento meta femenino de 23 a
30 años se orienta hacia prendas funcionales para uso diario en dinámicas de athleisure, lo que
lleva a la fábrica a implementar una manufactura de flexibilidad modular, adaptando ágilmente las
líneas de corte entre prendas deportivas y piezas casuales según las tendencias del mes.

La estrategia comercial establece un precio analítico de rango medio ($450 a $750 MXN), respaldado
por la regla de envío gratis a partir de compras mayores a $700 MXN para estimular la adquisición
de una segunda prenda. No obstante, la inversión en pauta publicitaria se mantiene al mínimo,
dejando la tracción casi enteramente al boca a boca orgánico entre las clientas. La distribución
se sostiene a través de un esquema dual que combina la tienda en línea propia con puntos de venta
físicos dentro de estudios y gimnasios asociados, recurriendo al empaque comercial estándar de
$7.87 MXN y una logística nacional de paquetería de $129 a $130 MXN por envío.

En este escenario, Owfit logra un punto de equilibrio operativo estable, pero la liquidez generada
apenas cubre la reposición de stock, sin arrojar excedentes significativos para fondear el
lanzamiento de la línea masculina Garmac Wear.""",
    },
    {
        "id": "apuesta",
        "numero": 3,
        "nombre": "Consolidación Premium a Precio Justo",
        "tono": "Apuesta / Meta OWFIT",
        "canal": "Mixto (B2C + B2B)",
        "multiplicador": 1.15,
        "parametros": {
            "margen_objetivo_pct": 50.0,  # texto: "márgenes de contribución superiores al 50%"
            # texto: "empaque biodegradable" premium; mismo costo que ya usa el
            # módulo Packaging para empaque premium (settings.PACKAGING_DEFAULT),
            # en vez de inventar una segunda cifra para lo mismo.
            "material_envio_mxn": settings.PACKAGING_DEFAULT["costo_packaging_mxn"],
            "percentil_objetivo": 70,  # texto: posicionamiento en la brecha premium del mercado
        },
        "kpis": [
            dict(
                etiqueta="Corte y confección",
                valor="Puebla (propio)",
                nota="Telas colombianas de especialidad",
            ),
            dict(
                etiqueta="Gramaje de tela",
                valor="220–270 g",
                nota="Sensación fría, opacidad absoluta",
            ),
            dict(
                etiqueta="Estrategia de precio",
                valor="Sets y combos",
                nota="Eleva el ticket promedio",
            ),
            dict(
                etiqueta="Empaque biodegradable",
                valor="≤ $50,000 MXN",
                nota="Dentro del presupuesto inicial",
            ),
            dict(etiqueta="Entrega", valor="3–5 días", nota="Alianzas de paquetería"),
            dict(
                etiqueta="Margen de contribución",
                valor="> 50%",
                nota="Financia Garmac Wear",
            ),
        ],
        "texto": """La organización consolida un modelo operativo mixto: aprovecha la calidad de telas especializadas
colombianas pero traslada formalmente los procesos de corte y confección a sus instalaciones en
Puebla. Esta integración permite a Owfit posicionarse con precisión en la brecha que divide al
mercado entre las firmas de lujo inalcanzables (que cobran más de $1,200 MXN por un legging) y las
marcas de importación desechables que se descosen a la segunda lavada.

La propuesta resuena con un público exigente que prioriza telas de alto gramaje (220 a 270 g) con
propiedades de sensación fría, opacidad absoluta a contraluz y ajuste que estiliza la figura.
Respaldada por sus certificaciones internacionales de calidad y cumplimiento ético, la marca
despliega una estrategia de pricing orientada a conjuntos y paquetes (como sets de top y legging o
combos de playeras básicas), elevando el valor transaccional del carrito. La tracción comercial se
apoya en embajadoras locales y entrenadoras de disciplinas como pilates y funcional, complementada
por una plataforma web optimizada para dispositivos móviles con soporte en puntos deportivos
estratégicos.

El cumplimiento del compromiso sustentable se materializa con la introducción de un empaque
biodegradable que se mantiene dentro del presupuesto inicial de $50,000 MXN, mientras que las
alianzas con paqueterías fijan entregas en plazos de 3 a 5 días. La marca logra márgenes de
contribución superiores al 50% y un flujo de caja saludable, generando las utilidades necesarias
para financiar la producción de la primera colección de Garmac Wear.""",
    },
    {
        "id": "optimista",
        "numero": 4,
        "nombre": "Expansión Acelerada y Escalamiento Multicanal",
        "tono": "Optimista con trade-offs",
        "canal": "Mixto (B2C + B2B)",
        "multiplicador": 1.3,
        "parametros": {
            # texto: "precio de posicionamiento aspiracional superior a $1,000 MXN
            # ... frente a marcas de prestigio global"
            "percentil_objetivo": 75,
            # texto: canales "Mayoreo + Amazon + Mercado Libre" -> comisión de
            # marketplace adicional a la pasarela normal
            "otros_variables_pct": 15.0,
            "envio_mxn": 180.0,  # texto: entregas "< 48 horas", logística exprés
        },
        "kpis": [
            dict(
                etiqueta="Proveeduría",
                valor="Nacional mexicana",
                nota="Sustituye insumo importado",
            ),
            dict(
                etiqueta="Volumen pico",
                valor="> 12,000 prendas/semana",
                nota="Hot Sale y Buen Fin",
            ),
            dict(
                etiqueta="Precio de posicionamiento",
                valor="> $1,000 MXN",
                nota="Aspiracional, vs. marcas globales",
            ),
            dict(
                etiqueta="Canales",
                valor="Mayoreo + Amazon + Mercado Libre",
                nota="Contratos con cadenas de gimnasios",
            ),
            dict(etiqueta="Entrega", valor="< 48 horas", nota="Ciudades principales"),
            dict(
                etiqueta="Trade-off",
                valor="Rotación de inventario lenta",
                nota="Liquidez comprometida temporalmente",
            ),
        ],
        "texto": """Se materializa una sustitución integral de insumos mediante el desarrollo de proveeduría
nacional mexicana capaz de igualar la tecnología textil importada, en un entorno donde los
gigantes multinacionales saturan los canales digitales con descuentos agresivos de temporada. La
demanda de las compradoras responde con fuerza durante eventos de alta concentración comercial
como Hot Sale y Buen Fin, lo que impulsa a Grupo Garmac a comprometer líneas completas de costura
a gran escala para sostener volúmenes de más de 12,000 prendas por semana.

La dirección apuesta por un pricing de posicionamiento aspiracional superior a los $1,000 MXN
para medirse frente a marcas de prestigio global, complementado por contratos de distribución
mayorista con cadenas de gimnasios y la comercialización en marketplaces como Amazon y Mercado
Libre.

Para afianzar la identidad prémium, se implementa un empaque circular elaborado con retazos de
tela reciclada que las clientas reutilizan como bolsa de gimnasio, al tiempo que la red logística
local asegura entregas en menos de 48 horas en las principales ciudades. Sin embargo, la
combinación de una producción masiva con precios altos de salida genera un trade-off operativo:
parte del inventario sufre una desaceleración en su tasa de rotación habitual, comprometiendo
temporalmente la liquidez en almacén mientras el mercado termina de absorber las colecciones a
gran escala.""",
    },
]

TONO_TIPO = {
    "Pesimista": "alerta",
    "Tendencial / Base": "neutro",
    "Apuesta / Meta OWFIT": "ok",
    "Optimista con trade-offs": "ok",
}

# Etiqueta y formato de cada parámetro de escenario, para armar el texto del
# hallazgo de supuestos sin repetir el mapeo en cada escenario.
_ETIQUETAS_PARAM = {
    "margen_objetivo_pct": ("Margen objetivo", lambda v: pct(v, 0)),
    "publicidad_pct": ("Publicidad", lambda v: pct(v, 0)),
    "pasarela_pct": ("Pasarela", lambda v: pct(v, 0)),
    "otros_variables_pct": ("Comisión de marketplace", lambda v: pct(v, 0)),
    "material_envio_mxn": ("Empaque/material de envío", money),
    "envio_mxn": ("Envío", money),
    "percentil_objetivo": ("Percentil objetivo de mercado", lambda v: f"P{v:.0f}"),
}


def _resumen_parametros(overrides: dict) -> str:
    partes = []
    for campo, valor in overrides.items():
        etiqueta, fmt = _ETIQUETAS_PARAM.get(campo, (campo, str))
        partes.append(f"{etiqueta}: <b>{fmt(valor)}</b>")
    return "; ".join(partes)


@st.cache_data(show_spinner=False)
def _mejor_modelo(serie: pd.Series):
    tabla, _ = trends.backtesting(
        serie, settings.MODELOS_SERIES, settings.BACKTEST_HOLDOUT_MESES
    )
    if tabla.empty:
        return None, tabla
    eleccion = trends.seleccionar_modelo(tabla)
    return eleccion["modelo"], tabla


def render(ctx):
    ui.kicker("Escenarios")
    st.title("Escenarios")
    st.caption(
        "Cuatro escenarios cualitativos de planeación para OWFIT (B2C) y Grupo Garmac (B2B), del "
        "más adverso al más favorable. No son un pronóstico estadístico: son supuestos de negocio "
        "para estresar pricing, márgenes e inventario."
    )
    ui.hallazgo(
        "<b>Cómo leerlos.</b> Cada escenario describe una combinación distinta de abasto, "
        "competencia, canal comercial y ejecución. Úselos para revisar si el pricing y los "
        "supuestos de costo del Simulador siguen siendo razonables si el contexto cambia.",
        "neutro",
    )

    tabs = st.tabs([f"{e['numero']}. {e['tono']}" for e in ESCENARIOS])
    for tab, esc in zip(tabs, ESCENARIOS):
        with tab:
            st.markdown(
                f"### Escenario {esc['numero']}: “{esc['nombre']}” ({esc['tono']})"
            )
            c1, c2 = st.columns([1, 1])
            with c1:
                st.caption(f"Canal: **{esc['canal']}**")
            with c2:
                st.caption(f"Tono: **{esc['tono']}**")

            ui.fila_kpis(esc["kpis"])
            st.markdown("")
            for parrafo in esc["texto"].split("\n\n"):
                st.markdown(parrafo)
            ui.hallazgo(
                f"<b>Multiplicador cualitativo aplicado a la proyección:</b> ×{esc['multiplicador']:.2f} "
                "sobre el pronóstico base de interés de búsqueda (ver abajo).",
                TONO_TIPO.get(esc["tono"], "neutro"),
            )
            ui.hallazgo(
                "<b>Supuestos de costo/margen de este escenario</b> (interpretados de la "
                "narrativa de arriba, no declarados por el usuario ni estimados de los datos): "
                f"{_resumen_parametros(esc['parametros'])}. El resto de los parámetros del "
                "Simulador (barra lateral) se mantiene igual. Alimentan el precio recomendado "
                "por prenda de este escenario, en «Plan promocional por temporada» más abajo.",
                "neutro",
            )

    st.markdown("---")
    st.markdown("### Proyección ajustada por escenario")
    st.caption(
        "El pronóstico base usa SARIMA (con descarte de "
        "pronósticos planos, mismo método que la página Estacionalidad). El ajuste por escenario es "
        "un multiplicador cualitativo, no una re-estimación del modelo: ilustra la dirección del "
        "efecto, no su magnitud real."
    )

    df = ctx.trends
    if df is None or df.empty:
        ui.sin_datos(
            "No hay series de Google Trends cargadas para proyectar. Coloque los archivos "
            "exportados en data/google_trends/ y recargue la página."
        )
        return

    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        termino = st.selectbox("Término", list(df.columns))
    with c2:
        esc_sel = st.selectbox(
            "Escenario",
            ESCENARIOS,
            format_func=lambda e: f"{e['numero']}. {e['tono']}",
        )
    with c3:
        meses = st.slider("Meses a proyectar", 3, 24, 12)

    serie = df[termino].dropna()
    with st.spinner("Eligiendo modelo (SARIMA)"):
        modelo, tabla_modelos = _mejor_modelo(serie)

    if modelo is None:
        ui.sin_datos(
            "La serie no tiene suficientes observaciones para elegir un modelo con backtesting."
        )
        return

    futuro_base = trends.pronostico_final(serie, modelo, meses)
    futuro_ajustado = futuro_base.copy()
    futuro_ajustado["Pronóstico"] = (
        futuro_ajustado["Pronóstico"] * esc_sel["multiplicador"]
    ).clip(lower=0)

    st.plotly_chart(
        charts.pronostico_escenario(
            serie, futuro_base, futuro_ajustado, modelo, esc_sel["tono"]
        ),
        use_container_width=True,
    )
    ui.nota_fuente(
        f"Modelo base: {modelo} (elegido por RMSE entre los que no producen un pronóstico plano, ver "
        "tabla completa en la página Estacionalidad). El multiplicador por escenario es un supuesto "
        "cualitativo del equipo, no un parámetro estimado de la serie."
    )

    _plan_promocional(ctx, serie, futuro_base, termino, modelo)


# ------------------------------------------------------------------ promociones
# Regla de activación de promociones sobre el proxy de demanda (Google Trends
# normalizado 0-1). El umbral 0.70 y el rango 15%-25% son metodología fija del
# proyecto: viven en config/settings.py y no se editan desde la interfaz. Aquí
# solo se aplican, escenario por escenario, con `src/promos.py`.


def _referencia_interna(ctx):
    """Controles del producto de referencia: PVP, COGS y volumen mensual.

    El PVP y el COGS SIEMPRE salen del archivo interno cargado en la barra
    lateral (o del archivo demo mientras no haya uno real): nunca hay precios
    escritos en el código. El volumen mensual es el único supuesto que el
    usuario declara aquí, porque el archivo interno trae una cantidad de piezas
    sin periodicidad asociada.
    """
    d = ctx.internos
    if d is None or d.empty or not ctx.val_internos.ok or "PVP" not in d.columns:
        return None

    etiqueta_portafolio = "Portafolio (promedio ponderado)"
    productos = d["Producto"].dropna().astype(str).tolist()

    c1, c2, c3 = st.columns([1.4, 1, 1.2])
    with c1:
        eleccion = st.selectbox(
            "Producto de referencia para el precio",
            [etiqueta_portafolio] + productos,
            help="PVP y COGS se leen del archivo interno cargado en la barra lateral.",
            key="promo_producto",
        )

    tiene_cantidad = (
        "Cantidad" in d.columns
        and pd.to_numeric(d["Cantidad"], errors="coerce").notna().any()
    )
    if eleccion == etiqueta_portafolio:
        pvp_s = pd.to_numeric(d["PVP"], errors="coerce")
        cogs_s = pd.to_numeric(d["COGS"], errors="coerce")
        if tiene_cantidad:
            w = pd.to_numeric(d["Cantidad"], errors="coerce").fillna(0)
            m = pvp_s.notna() & cogs_s.notna() & (w > 0)
            pvp = (
                float(np.average(pvp_s[m], weights=w[m]))
                if m.any()
                else float(pvp_s.mean())
            )
            cogs = (
                float(np.average(cogs_s[m], weights=w[m]))
                if m.any()
                else float(cogs_s.mean())
            )
            vol_default = float(w.sum())
        else:
            pvp, cogs = float(pvp_s.mean()), float(cogs_s.mean())
            vol_default = float(len(d))
        nombre = etiqueta_portafolio
    else:
        fila = d[d["Producto"].astype(str) == eleccion].iloc[0]
        pvp = float(pd.to_numeric(fila["PVP"], errors="coerce"))
        cogs = float(pd.to_numeric(fila["COGS"], errors="coerce"))
        vol_default = (
            float(pd.to_numeric(fila.get("Cantidad"), errors="coerce"))
            if tiene_cantidad
            else 100.0
        )
        if not np.isfinite(vol_default):
            vol_default = 100.0
        nombre = eleccion

    with c2:
        volumen = st.number_input(
            "Volumen mensual de referencia (unidades)",
            min_value=0.0,
            value=float(round(vol_default, 0)),
            step=10.0,
            help="Unidades del periodo con demanda máxima. Las unidades de cada mes son este "
            "volumen escalado por el proxy de demanda; el descuento no altera el volumen "
            "porque el proyecto no tiene una elasticidad estimada.",
            key=f"promo_volumen_{nombre}",
        )
    with c3:
        metodo = st.selectbox(
            "Normalización del proxy (0-1)",
            settings.METODOS_NORMALIZACION_PROXY,
            help="Google re-escala cada consulta: en un mismo export el término más buscado marca "
            "100 y los demás quedan comprimidos. Mín-máx del histórico evita que un término "
            "de bajo volumen quede permanentemente por debajo del umbral.",
            key="promo_normalizacion",
        )

    margen_txt = pct((pvp - cogs) / pvp * 100) if pvp else "—"
    st.caption(
        f"PVP de referencia: **{money(pvp)}** · COGS: **{money(cogs)}** · "
        f"margen bruto regular: **{margen_txt}**"
    )
    return dict(nombre=nombre, pvp=pvp, cogs=cogs, volumen=volumen, metodo=metodo)


def _kpis_escenario(res: dict, umbral: float):
    ui.fila_kpis(
        [
            dict(
                etiqueta="Temporada alta",
                valor=f"{res['periodos_alta']}",
                nota=f"periodos con proxy ≥ {umbral:.2f}",
                icono="calendario",
            ),
            dict(
                etiqueta="Temporada baja",
                valor=f"{res['periodos_baja']}",
                nota=f"periodos con proxy < {umbral:.2f}",
                icono="alerta",
            ),
            dict(
                etiqueta="Promociones activadas",
                valor=f"{res['promociones']}",
                nota="una por cada periodo de temporada baja",
                icono="meta",
            ),
            dict(
                etiqueta="Descuento promedio",
                valor=pct(res["descuento_prom"]),
                nota="solo sobre periodos con promoción",
                icono="porcentaje",
            ),
        ]
    )
    st.markdown("")
    ui.fila_kpis(
        [
            dict(
                etiqueta="Descuento máximo",
                valor=pct(res["descuento_max"]),
                nota="tramo más profundo aplicado",
                icono="porcentaje",
            ),
            dict(
                etiqueta="PVP promedio",
                valor=money(res["pvp_prom"]),
                nota="precio regular de referencia",
                icono="dinero",
            ),
            dict(
                etiqueta="Precio promocional promedio",
                valor=money(res["precio_promo_prom"]),
                nota="promedio de los meses en promoción",
                icono="dinero",
            ),
            dict(
                etiqueta="Ingresos estimados",
                valor=money(res["ingreso"]),
                nota="suma del horizonte proyectado",
                icono="tendencia",
            ),
            dict(
                etiqueta="Utilidad estimada",
                valor=money(res["utilidad"]),
                nota="después de COGS, variables y envío",
                icono="escala",
                positivo=bool(np.isfinite(res["utilidad"]) and res["utilidad"] > 0),
            ),
        ]
    )


def _alertas_escenario(plan: pd.DataFrame):
    lista = promos.alertas(plan)
    bajas = [a for a in lista if a["tipo"] != "ok"]
    altas = [a for a in lista if a["tipo"] == "ok"]

    def detalles(a):
        f = a["fila"]
        base = [
            ("Proxy de demanda", f"{a['proxy']:.2f}"),
            ("Descuento", pct(a["descuento"])),
        ]
        if np.isfinite(f["PVP"]):
            base.append(("Precio regular", money(f["PVP"])))
            base.append(("Precio promocional", money(f["Precio promocional"])))
        if np.isfinite(f["Margen % promocional"]):
            base.append(("Margen bruto", pct(f["Margen % promocional"])))
        return base

    if bajas:
        st.markdown("**Oportunidades de promoción detectadas**")
        cols = st.columns(2)
        for i, a in enumerate(bajas):
            with cols[i % 2]:
                ui.alerta_promo(
                    a["titulo"], a["periodo"], detalles(a), a["motivo"], a["tipo"]
                )
    else:
        ui.hallazgo(
            "Ningún periodo del horizonte cae por debajo del umbral: en este escenario no se "
            "activa ninguna promoción y el precio se mantiene regular todo el periodo.",
            "ok",
        )

    if altas:
        with st.expander(f"Periodos de temporada alta ({len(altas)})", expanded=False):
            cols = st.columns(2)
            for i, a in enumerate(altas):
                with cols[i % 2]:
                    ui.alerta_promo(
                        a["titulo"], a["periodo"], detalles(a), a["motivo"], "ok"
                    )


def _tabla_acciones(plan: pd.DataFrame):
    cols = [
        "Periodo",
        "Proxy",
        "Estado",
        "Descuento %",
        "PVP",
        "Precio promocional",
        "COGS",
        "Margen % promocional",
        "Unidades estimadas",
        "Ingreso estimado",
        "Utilidad estimada",
        "Acción recomendada",
    ]
    st.dataframe(
        plan[cols],
        use_container_width=True,
        hide_index=True,
        column_config={
            "Proxy": st.column_config.NumberColumn("Proxy Trends", format="%.2f"),
            "Descuento %": st.column_config.NumberColumn(format="%.0f%%"),
            "PVP": st.column_config.NumberColumn(format="$%,.0f"),
            "Precio promocional": st.column_config.NumberColumn(
                "Promo", format="$%,.0f"
            ),
            "COGS": st.column_config.NumberColumn(format="$%,.0f"),
            "Margen % promocional": st.column_config.NumberColumn(
                "Margen %", format="%.1f%%"
            ),
            "Unidades estimadas": st.column_config.NumberColumn(
                "Unidades", format="%,.0f"
            ),
            "Ingreso estimado": st.column_config.NumberColumn(
                "Ingreso", format="$%,.0f"
            ),
            "Utilidad estimada": st.column_config.NumberColumn(
                "Utilidad", format="$%,.0f"
            ),
        },
    )


def _tabla_precios_escenario(ctx, esc: dict) -> pd.DataFrame:
    """Precio recomendado por prenda bajo los supuestos propios de este escenario.

    Reutiliza el mismo motor que Simulador/Resumen (`pricing.calcular_precio_recomendado`),
    con los parámetros de costo/margen del escenario en vez de los globales de la barra
    lateral. `ctx.internos["PVP"]` ya es minorista (ver loaders.cargar_internos); el precio
    de mayoreo se deriva dividiendo entre el mismo recargo, sin releer el archivo.
    """
    if ctx.internos is None or ctx.internos.empty or not ctx.val_internos.ok:
        return pd.DataFrame()

    p_esc = replace(ctx.params, **esc["parametros"])
    t = pricing.calcular_precio_recomendado(ctx.internos, ctx.competencia, p_esc)
    if t.empty:
        return t

    factor = 1 + settings.RECARGO_MINORISTA_PCT / 100
    out = t[["Producto", "Categoría", "PVP actual", "Precio recomendado"]].rename(
        columns={"PVP actual": "Precio normal", "Precio recomendado": "Precio nuevo"}
    )
    out["Precio normal (mayoreo)"] = out["Precio normal"] / factor
    out["Precio nuevo (mayoreo)"] = out["Precio nuevo"] / factor
    return out


def _precios_por_prenda(ctx, esc: dict, descuento_pct: float):
    """Precio normal, nuevo (recomendado del escenario) y con descuento de
    temporada baja, prenda por prenda, en minorista y en mayoreo.

    El descuento reutiliza el 'Descuento promedio' ya calculado para este mismo
    escenario en el plan promocional (misma fila de KPIs de arriba), en vez de
    introducir un segundo supuesto de descuento desconectado del resto de la
    página.
    """
    tabla = _tabla_precios_escenario(ctx, esc)
    if tabla.empty:
        return

    descuento = descuento_pct / 100 if np.isfinite(descuento_pct) else 0.0
    tabla["Con descuento de temporada baja"] = tabla["Precio nuevo"] * (1 - descuento)
    tabla["Con descuento de temporada baja (mayoreo)"] = tabla[
        "Precio nuevo (mayoreo)"
    ] * (1 - descuento)

    st.markdown("**Precio recomendado por prenda en este escenario**")
    st.caption(
        "Normal = precio actual. Nuevo = precio recomendado con los supuestos de costo/margen "
        f"de este escenario (ver arriba). Con descuento = nuevo × (1 − {pct(descuento * 100, 0)}), "
        "el descuento promedio de temporada baja de este escenario. Mayoreo = el mismo precio "
        f"dividido entre {1 + settings.RECARGO_MINORISTA_PCT / 100:.2f} (el recargo minorista "
        "del archivo interno, a la inversa)."
    )

    fmt_money = st.column_config.NumberColumn(format="$%,.0f")
    cols_precio = ["Precio normal", "Precio nuevo", "Con descuento de temporada baja"]
    column_config = {c: fmt_money for c in cols_precio}

    st.markdown("*Minorista*")
    st.dataframe(
        tabla[["Producto", "Categoría"] + cols_precio],
        use_container_width=True,
        hide_index=True,
        column_config=column_config,
    )
    st.markdown("*Mayoreo (lo que factura Grupo Garmac)*")
    st.dataframe(
        tabla[
            ["Producto", "Categoría"] + [f"{c} (mayoreo)" for c in cols_precio]
        ].rename(columns=lambda c: c.replace(" (mayoreo)", "")),
        use_container_width=True,
        hide_index=True,
        column_config=column_config,
    )


def _plan_promocional(ctx, serie, futuro_base, termino, modelo):
    """Aplica la regla de temporada a los CUATRO escenarios existentes.

    Cada escenario usa su propia serie: el mismo pronóstico base multiplicado
    por su multiplicador cualitativo, que es el que ya calcula esta página. No
    se crea un quinto escenario ni se re-estima el modelo.
    """
    umbral = settings.UMBRAL_PROXY_TEMPORADA
    minimo, maximo = settings.RANGO_DESCUENTO_PROMO

    st.markdown("---")
    st.markdown("### Plan promocional por temporada")
    st.caption(
        "Regla de activación aplicada periodo por periodo sobre el proxy de demanda de "
        f"«{termino}»: la serie de Google Trends normalizada de 0 a 1. Se ejecuta de forma "
        "independiente para cada uno de los cuatro escenarios."
    )
    ui.hallazgo(
        f"<b>Regla.</b> Proxy de demanda <b>I ≥ {umbral:.2f}</b> → temporada alta, precio regular, "
        f"0% de descuento. <b>I &lt; {umbral:.2f}</b> → temporada baja, promoción activada con un "
        f"descuento dentro del rango {minimo:.0f}%–{maximo:.0f}%: "
        f"<b>0.55 ≤ I &lt; {umbral:.2f} → 15%</b>, <b>0.40 ≤ I &lt; 0.55 → 20%</b>, "
        f"<b>I &lt; 0.40 → 25%</b>. Los tramos solo operacionalizan ese rango; el único corte que "
        f"separa temporada alta de temporada baja es {umbral:.2f}.",
        "neutro",
    )

    ui.cinta_origen(ctx.es_demo, ctx.nombre_archivo)
    ref = _referencia_interna(ctx)
    if ref is None:
        ui.sin_datos(
            "El plan promocional necesita PVP y COGS del archivo interno para calcular precio "
            "promocional y margen. Cargue el archivo en la barra lateral (o descargue la "
            "plantilla de demostración) para ver esta sección."
        )
        return

    planes, resumenes = {}, {}
    for esc in ESCENARIOS:
        futuro = futuro_base.copy()
        futuro["Pronóstico"] = (futuro["Pronóstico"] * esc["multiplicador"]).clip(
            lower=0
        )
        planes[esc["id"]] = promos.plan_promocional(
            futuro,
            serie,
            ref["pvp"],
            ref["cogs"],
            ctx.params,
            volumen_base=ref["volumen"],
            metodo_normalizacion=ref["metodo"],
        )
        resumenes[esc["id"]] = promos.resumen_plan(planes[esc["id"]])

    proxy_hist = pd.Series(
        promos.normalizar_proxy(serie.to_numpy(dtype=float), serie, ref["metodo"]),
        index=serie.index,
    )

    comparativo = pd.DataFrame(
        [
            {
                "Escenario": f"{esc['numero']}. {esc['tono']}",
                "Multiplicador": esc["multiplicador"],
                "Temporada alta": resumenes[esc["id"]].get("periodos_alta"),
                "Temporada baja": resumenes[esc["id"]].get("periodos_baja"),
                "Descuento promedio": resumenes[esc["id"]].get("descuento_prom"),
                "Descuento máximo": resumenes[esc["id"]].get("descuento_max"),
                "Ingreso estimado": resumenes[esc["id"]].get("ingreso"),
                "Utilidad estimada": resumenes[esc["id"]].get("utilidad"),
            }
            for esc in ESCENARIOS
        ]
    )
    st.markdown("**Comparativo de los cuatro escenarios**")
    st.dataframe(
        comparativo,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Multiplicador": st.column_config.NumberColumn(format="×%.2f"),
            "Temporada alta": st.column_config.NumberColumn(
                "Periodos alta", format="%d"
            ),
            "Temporada baja": st.column_config.NumberColumn(
                "Periodos baja", format="%d"
            ),
            "Descuento promedio": st.column_config.NumberColumn(format="%.1f%%"),
            "Descuento máximo": st.column_config.NumberColumn(format="%.0f%%"),
            "Ingreso estimado": st.column_config.NumberColumn(format="$%,.0f"),
            "Utilidad estimada": st.column_config.NumberColumn(format="$%,.0f"),
        },
    )

    tabs = st.tabs([f"{e['numero']}. {e['tono']}" for e in ESCENARIOS])
    for tab, esc in zip(tabs, ESCENARIOS):
        with tab:
            plan = planes[esc["id"]]
            if plan.empty:
                ui.sin_datos("No hay pronóstico disponible para este escenario.")
                continue
            res = resumenes[esc["id"]]

            st.markdown(f"#### Escenario {esc['numero']}: “{esc['nombre']}”")
            st.caption(
                f"Serie del escenario: pronóstico base ({modelo}) × {esc['multiplicador']:.2f}, "
                f"normalizado a 0-1 con «{ref['metodo']}». Producto de referencia: {ref['nombre']}."
            )
            _kpis_escenario(res, umbral)
            st.markdown("")

            _precios_por_prenda(ctx, esc, res.get("descuento_prom"))
            st.markdown("---")

            st.plotly_chart(
                charts.promociones_escenario(plan, proxy_hist, esc["tono"], umbral),
                use_container_width=True,
            )

            ventanas = promos.ventanas_promocionales(plan)
            if ventanas:
                detalle = "; ".join(
                    (v["inicio"] if v["meses"] == 1 else f"{v['inicio']} a {v['fin']}")
                    + f" ({v['meses']} mes{'es' if v['meses'] > 1 else ''}, hasta "
                    f"{v['descuento_max']:.0f}%)"
                    for v in ventanas
                )
                ui.hallazgo(
                    f"<b>Ventanas promocionales del escenario:</b> {detalle}. El resto del "
                    "horizonte se mantiene a precio regular.",
                    "advertencia",
                )

            _alertas_escenario(plan)

            st.markdown("**Tabla de acciones**")
            _tabla_acciones(plan)

            cedido = (
                res["ingreso_regular"] - res["ingreso"]
                if np.isfinite(res["ingreso_regular"]) and np.isfinite(res["ingreso"])
                else np.nan
            )
            if np.isfinite(cedido) and cedido > 0:
                ui.nota_fuente(
                    f"Costo de la promoción en este escenario: {money(cedido)} de ingreso cedido "
                    f"({money(res['utilidad_regular'] - res['utilidad'])} de utilidad) frente a "
                    "vender el mismo volumen a precio regular. La comparación NO supone que el "
                    "descuento aumente las unidades vendidas: el proyecto no tiene una elasticidad "
                    "precio-demanda estimada, así que ese efecto se deja fuera antes que inventarlo."
                )

    ui.nota_fuente(
        f"Proxy de demanda = índice de Google Trends de «{termino}» normalizado a 0-1 con "
        f"«{ref['metodo']}», anclado en el mínimo y el máximo históricos observados. El umbral "
        f"{umbral:.2f} y el rango de descuento {minimo:.0f}%–{maximo:.0f}% son metodología fija "
        "del proyecto, no parámetros ajustados a estos datos. Unidades, ingreso y utilidad son "
        "ilustrativos: dependen del volumen mensual de referencia declarado arriba y usan la "
        "misma economía unitaria (COGS, costos variables y envío) que el resto del dashboard."
    )

"""Activación de promociones por temporada a partir del proxy de demanda.

Implementa la regla de la metodología del proyecto, sin variantes:

    proxy I = serie de Google Trends normalizada a 0-1
    I >= 0.70  ->  TEMPORADA ALTA  ->  precio regular, 0% de descuento
    I <  0.70  ->  TEMPORADA BAJA  ->  promoción activada, descuento 15%-25%

El tramo de descuento (15 / 20 / 25%) solo operacionaliza el rango que ya fija
la metodología; el umbral 0.70 es el único corte que separa temporada alta de
baja y vive en `config.settings.UMBRAL_PROXY_TEMPORADA`.

Este módulo NO estima demanda ni elasticidad. Las unidades de cada periodo son
el volumen mensual de referencia declarado por el usuario escalado por el
proxy; el descuento cambia precio y margen, nunca el volumen. Cualquier lectura
del tipo "la promoción vendería más" no está soportada por estos datos: haría
falta una elasticidad estimada que este proyecto no tiene.

El impacto financiero se calcula con `pricing.economia_unitaria`, la misma
función que usa el resto del dashboard: aquí no se duplica ningún cálculo de
costos, margen ni utilidad.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from config import settings
from src import pricing

MESES_ABREV = [
    "Ene",
    "Feb",
    "Mar",
    "Abr",
    "May",
    "Jun",
    "Jul",
    "Ago",
    "Sep",
    "Oct",
    "Nov",
    "Dic",
]

ESTADO_ALTA = "Temporada alta"
ESTADO_BAJA = "Temporada baja"


# ------------------------------------------------------------------ proxy 0-1
def normalizar_proxy(valores, referencia=None, metodo: str | None = None) -> np.ndarray:
    """Lleva el índice de Google Trends (0-100) al proxy de demanda 0-1.

    `referencia` es la serie histórica observada que ancla la escala mín-máx:
    se usa el mismo mínimo y máximo para histórico y pronóstico, de modo que un
    escenario optimista que empuja la serie por encima del máximo observado
    satura en 1.0 en vez de re-escalar la referencia bajo sus propios pies.

    Si la referencia es inservible (vacía o constante) se cae a la escala cruda
    /100 en lugar de devolver NaN.
    """
    metodo = metodo or settings.METODO_NORMALIZACION_MINMAX
    v = np.asarray(valores, dtype=float)

    if metodo == settings.METODO_NORMALIZACION_CRUDO:
        return np.clip(v / 100.0, 0.0, 1.0)

    ref = pd.Series(
        referencia if referencia is not None else [], dtype="float64"
    ).dropna()
    if ref.empty:
        return np.clip(v / 100.0, 0.0, 1.0)
    lo, hi = float(ref.min()), float(ref.max())
    if not np.isfinite(lo) or not np.isfinite(hi) or hi <= lo:
        return np.clip(v / 100.0, 0.0, 1.0)
    return np.clip((v - lo) / (hi - lo), 0.0, 1.0)


def estado_por_proxy(i: float) -> str:
    """Temporada alta / baja según el único umbral de la metodología."""
    if not np.isfinite(i):
        return ESTADO_ALTA
    return ESTADO_ALTA if i >= settings.UMBRAL_PROXY_TEMPORADA else ESTADO_BAJA


def descuento_por_proxy(i: float) -> tuple[float, str]:
    """Descuento (%) y acción recomendada para un valor del proxy.

    Devuelve (0.0, "Mantener precio regular") en temporada alta. En temporada
    baja recorre la escala de `settings.ESCALA_DESCUENTO_PROMO`, cuyos tramos
    están todos dentro del rango 15%-25%.
    """
    if estado_por_proxy(i) == ESTADO_ALTA:
        return 0.0, settings.ACCION_TEMPORADA_ALTA
    for tramo in settings.ESCALA_DESCUENTO_PROMO:
        if tramo["min"] <= i < tramo["max"]:
            return float(tramo["descuento_pct"]), tramo["accion"]
    # Por debajo del tramo más bajo definido: aplica el descuento máximo.
    ultimo = settings.ESCALA_DESCUENTO_PROMO[-1]
    return float(ultimo["descuento_pct"]), ultimo["accion"]


def etiqueta_periodo(fecha) -> str:
    f = pd.Timestamp(fecha)
    return f"{MESES_ABREV[f.month - 1]} {f.year}"


# ------------------------------------------------------------------ plan
def plan_promocional(
    futuro: pd.DataFrame,
    historico: pd.Series,
    pvp: float,
    cogs: float,
    params: pricing.Parametros,
    volumen_base: float | None = None,
    metodo_normalizacion: str | None = None,
) -> pd.DataFrame:
    """Aplica la regla de temporada periodo por periodo sobre un pronóstico.

    `futuro` es la salida de `trends.pronostico_final` (columnas Fecha y
    Pronóstico) ya ajustada por el multiplicador del escenario. `historico` es
    la serie observada del mismo término, usada solo como referencia de
    normalización.

    Devuelve una fila por periodo con estado, descuento, precios, márgenes e
    impacto estimado. Sin PVP/COGS válidos, las columnas de dinero quedan en
    NaN antes que inventar un precio.
    """
    if futuro is None or futuro.empty:
        return pd.DataFrame()

    proxy = normalizar_proxy(futuro["Pronóstico"], historico, metodo_normalizacion)
    pvp = float(pvp) if pvp is not None and np.isfinite(pvp) else np.nan
    cogs = float(cogs) if cogs is not None and np.isfinite(cogs) else np.nan
    vol = (
        float(volumen_base)
        if volumen_base is not None and np.isfinite(volumen_base)
        else np.nan
    )

    eco_reg = pricing.economia_unitaria(pvp, cogs, params)

    filas = []
    for fecha, indice, proj in zip(futuro["Fecha"], proxy, futuro["Pronóstico"]):
        estado = estado_por_proxy(indice)
        desc_pct, accion = descuento_por_proxy(indice)
        precio = pvp * (1 - desc_pct / 100.0) if np.isfinite(pvp) else np.nan
        eco_promo = pricing.economia_unitaria(precio, cogs, params)

        unidades = vol * indice if np.isfinite(vol) else np.nan
        ingreso = (
            precio * unidades
            if np.isfinite(precio) and np.isfinite(unidades)
            else np.nan
        )
        utilidad = (
            eco_promo["utilidad_unidad"] * unidades
            if np.isfinite(eco_promo["utilidad_unidad"]) and np.isfinite(unidades)
            else np.nan
        )
        ingreso_reg = (
            pvp * unidades if np.isfinite(pvp) and np.isfinite(unidades) else np.nan
        )
        utilidad_reg = (
            eco_reg["utilidad_unidad"] * unidades
            if np.isfinite(eco_reg["utilidad_unidad"]) and np.isfinite(unidades)
            else np.nan
        )

        filas.append(
            {
                "Fecha": pd.Timestamp(fecha),
                "Periodo": etiqueta_periodo(fecha),
                "Índice Trends": float(proj),
                "Proxy": float(indice),
                "Estado": estado,
                "Descuento %": desc_pct,
                "PVP": pvp,
                "Precio promocional": precio,
                "COGS": cogs,
                "Margen unitario regular": (
                    (pvp - cogs) if np.isfinite(pvp) and np.isfinite(cogs) else np.nan
                ),
                "Margen unitario promocional": (
                    (precio - cogs)
                    if np.isfinite(precio) and np.isfinite(cogs)
                    else np.nan
                ),
                "Margen % regular": eco_reg["margen_bruto"] * 100,
                "Margen % promocional": eco_promo["margen_bruto"] * 100,
                "Margen contribución %": eco_promo["margen_contribucion"] * 100,
                "Utilidad unitaria": eco_promo["utilidad_unidad"],
                "Unidades estimadas": unidades,
                "Ingreso estimado": ingreso,
                "Utilidad estimada": utilidad,
                "Ingreso a precio regular": ingreso_reg,
                "Utilidad a precio regular": utilidad_reg,
                "Acción recomendada": accion,
            }
        )
    return pd.DataFrame(filas)


def resumen_plan(plan: pd.DataFrame) -> dict:
    """Indicadores de cabecera de un escenario.

    Los promedios de descuento y de precio promocional se calculan SOLO sobre
    los periodos con promoción: un promedio que incluya los meses a precio
    regular diluye la cifra y hace ver el descuento más suave de lo que
    realmente se ejecutaría en tienda.
    """
    if plan is None or plan.empty:
        return {}

    promos = plan[plan["Estado"] == ESTADO_BAJA]
    altas = plan[plan["Estado"] == ESTADO_ALTA]

    def suma(col):
        s = pd.to_numeric(plan[col], errors="coerce")
        return float(s.sum()) if s.notna().any() else np.nan

    pvp_prom = float(pd.to_numeric(plan["PVP"], errors="coerce").mean())
    return {
        "periodos": int(len(plan)),
        "periodos_alta": int(len(altas)),
        "periodos_baja": int(len(promos)),
        "promociones": int(len(promos)),
        "descuento_prom": (
            float(promos["Descuento %"].mean()) if not promos.empty else 0.0
        ),
        "descuento_max": (
            float(promos["Descuento %"].max()) if not promos.empty else 0.0
        ),
        "proxy_prom": float(plan["Proxy"].mean()),
        "proxy_min": float(plan["Proxy"].min()),
        "pvp_prom": pvp_prom,
        "precio_promo_prom": (
            float(promos["Precio promocional"].mean()) if not promos.empty else pvp_prom
        ),
        "precio_efectivo_prom": float(
            pd.to_numeric(plan["Precio promocional"], errors="coerce").mean()
        ),
        "margen_pct_prom": float(
            pd.to_numeric(plan["Margen % promocional"], errors="coerce").mean()
        ),
        "unidades": suma("Unidades estimadas"),
        "ingreso": suma("Ingreso estimado"),
        "utilidad": suma("Utilidad estimada"),
        "ingreso_regular": suma("Ingreso a precio regular"),
        "utilidad_regular": suma("Utilidad a precio regular"),
    }


def alertas(plan: pd.DataFrame) -> list[dict]:
    """Traduce cada periodo a una alerta comercial accionable.

    `tipo` reutiliza los tonos de `ui.hallazgo`: alerta (rojo) para el tramo
    más profundo, advertencia (ocre) para el resto de la temporada baja y ok
    (verde) para la temporada alta.
    """
    if plan is None or plan.empty:
        return []

    umbral = settings.UMBRAL_PROXY_TEMPORADA
    salida = []
    for _, r in plan.iterrows():
        if r["Estado"] == ESTADO_ALTA:
            salida.append(
                {
                    "tipo": "ok",
                    "titulo": "Temporada alta",
                    "periodo": r["Periodo"],
                    "proxy": float(r["Proxy"]),
                    "descuento": 0.0,
                    "motivo": f"Proxy de demanda {r['Proxy']:.2f} &ge; {umbral:.2f}",
                    "fila": r,
                }
            )
        else:
            profundo = float(r["Descuento %"]) >= settings.RANGO_DESCUENTO_PROMO[1]
            salida.append(
                {
                    "tipo": "alerta" if profundo else "advertencia",
                    "titulo": (
                        "Baja demanda detectada"
                        if profundo
                        else "Oportunidad de promoción"
                    ),
                    "periodo": r["Periodo"],
                    "proxy": float(r["Proxy"]),
                    "descuento": float(r["Descuento %"]),
                    "motivo": f"Proxy de demanda {r['Proxy']:.2f} &lt; {umbral:.2f}",
                    "fila": r,
                }
            )
    return salida


def ventanas_promocionales(plan: pd.DataFrame) -> list[dict]:
    """Agrupa periodos promocionales consecutivos en ventanas continuas, para
    poder hablar de "una promoción de tres meses" en vez de tres promociones
    sueltas."""
    if plan is None or plan.empty:
        return []

    ventanas, actual = [], None
    for _, r in plan.iterrows():
        if r["Estado"] == ESTADO_BAJA:
            if actual is None:
                actual = {
                    "inicio": r["Periodo"],
                    "fin": r["Periodo"],
                    "meses": 1,
                    "descuento_max": float(r["Descuento %"]),
                    "proxy_min": float(r["Proxy"]),
                }
            else:
                actual["fin"] = r["Periodo"]
                actual["meses"] += 1
                actual["descuento_max"] = max(
                    actual["descuento_max"], float(r["Descuento %"])
                )
                actual["proxy_min"] = min(actual["proxy_min"], float(r["Proxy"]))
        elif actual is not None:
            ventanas.append(actual)
            actual = None
    if actual is not None:
        ventanas.append(actual)
    return ventanas

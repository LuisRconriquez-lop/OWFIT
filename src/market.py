"""EDA de mercado y construcción de benchmarks competitivos por categoría."""

from __future__ import annotations

import numpy as np
import pandas as pd

from config import settings
from src.utils import describe_numerica


def resumen_precio_por(
    df: pd.DataFrame, dimension: str, minimo: int = 1
) -> pd.DataFrame:
    """Descriptivos de precio agrupados por una dimensión (marca, categoría, segmento)."""
    filas = []
    for valor, grupo in df.groupby(dimension, dropna=False, observed=True):
        d = describe_numerica(grupo["Precio_MXN"])
        if not d or d["n"] < minimo:
            continue
        d[dimension] = valor
        filas.append(d)
    if not filas:
        return pd.DataFrame()
    out = pd.DataFrame(filas)
    cols = [
        dimension,
        "n",
        "media",
        "mediana",
        "desv_est",
        "min",
        "P25",
        "P50",
        "P75",
        "P90",
        "max",
        "coef_variacion",
    ]
    return out[[c for c in cols if c in out.columns]].sort_values(
        "mediana", ascending=False
    )


def pesos_por_marca(df: pd.DataFrame) -> pd.Series:
    """Peso 1/n_marca para cada producto.

    Sin esto, una marca con miles de referencias en catálogo (Alo Yoga tiene
    ~40 veces más productos que Kleos) define ella sola los percentiles del
    mercado. Con el peso balanceado, cada marca aporta lo mismo a la
    distribución y el percentil describe el mercado, no el tamaño del catálogo.
    """
    n = df.groupby("Marca")["Precio_MXN"].transform("size")
    return 1.0 / n


def cuantil_ponderado(valores, pesos, q: float) -> float:
    v = pd.to_numeric(pd.Series(valores).reset_index(drop=True), errors="coerce")
    w = pd.Series(pesos).reset_index(drop=True).astype(float)
    ok = v.notna() & w.notna() & (w > 0)
    v, w = v[ok].to_numpy(), w[ok].to_numpy()
    if v.size == 0:
        return np.nan
    orden = np.argsort(v)
    v, w = v[orden], w[orden]
    acum = (np.cumsum(w) - 0.5 * w) / w.sum()
    return float(np.interp(q, acum, v))


def referencia_precios(
    df_competencia: pd.DataFrame, categoria: str, balanceado: bool = True
):
    """Devuelve (precios, pesos) de la categoría dentro del conjunto competitivo."""
    d = df_competencia[df_competencia["Categoria_norm"] == categoria]
    precios = d["Precio_MXN"].dropna()
    if precios.empty:
        return precios, pd.Series(dtype=float)
    pesos = (
        pesos_por_marca(d).loc[precios.index]
        if balanceado
        else pd.Series(1.0, index=precios.index)
    )
    return precios, pesos


def percentiles_categoria(
    df_competencia: pd.DataFrame,
    percentiles=(10, 25, 50, 60, 65, 70, 75, 90),
    balanceado: bool = True,
) -> pd.DataFrame:
    """Percentiles de precio por categoría, calculados solo con competidores."""
    filas = []
    for cat, g in df_competencia.groupby("Categoria_norm", observed=True):
        precios = g["Precio_MXN"].dropna()
        if precios.empty:
            continue
        pesos = (
            pesos_por_marca(g).loc[precios.index]
            if balanceado
            else pd.Series(1.0, index=precios.index)
        )
        fila = {
            "Categoria_norm": cat,
            "n_competidores": int(precios.size),
            "n_marcas": int(g["Marca"].nunique()),
        }
        for p in percentiles:
            fila[f"P{p}"] = cuantil_ponderado(precios, pesos, p / 100)
        filas.append(fila)
    return (
        pd.DataFrame(filas).sort_values("Categoria_norm") if filas else pd.DataFrame()
    )


def posicion_percentil(
    precio: float, referencia: pd.Series, pesos: pd.Series | None = None
) -> float:
    """En qué percentil de la distribución de referencia cae un precio."""
    ref = pd.to_numeric(referencia, errors="coerce").dropna()
    if ref.empty or precio is None or not np.isfinite(precio):
        return np.nan
    if pesos is None:
        return float((ref <= precio).mean() * 100)
    w = pd.Series(pesos).reindex(ref.index).astype(float)
    ok = w.notna() & (w > 0)
    if not ok.any():
        return float((ref <= precio).mean() * 100)
    return float(100 * w[ok][ref[ok] <= precio].sum() / w[ok].sum())


def etiqueta_posicion(percentil: float) -> str:
    if percentil is None or np.isnan(percentil):
        return "Sin referencia"
    if percentil < 25:
        return "Value / entrada"
    if percentil < 45:
        return "Debajo de la mediana"
    if percentil <= 60:
        return "En la mediana"
    if percentil <= 80:
        return "Arriba de la mediana"
    return "Premium"


def owfit_vs_mercado(
    df_productos: pd.DataFrame, balanceado: bool = True
) -> pd.DataFrame:
    """Compara la mediana de OWFIT contra la del resto del mercado, por categoría."""
    owfit = df_productos[df_productos["Marca"] == settings.MARCA_OWFIT]
    resto = df_productos[df_productos["Marca"] != settings.MARCA_OWFIT]

    filas = []
    for cat in sorted(set(owfit["Categoria_norm"]) | set(resto["Categoria_norm"])):
        po = owfit.loc[owfit["Categoria_norm"] == cat, "Precio_MXN"].dropna()
        pr, wr = referencia_precios(resto, cat, balanceado)
        if po.empty and pr.empty:
            continue
        med_o = float(po.median()) if not po.empty else np.nan
        med_r = cuantil_ponderado(pr, wr, 0.5) if not pr.empty else np.nan
        pct = (
            posicion_percentil(med_o, pr, wr)
            if not pr.empty and np.isfinite(med_o)
            else np.nan
        )
        filas.append(
            {
                "Categoría": cat,
                "n OWFIT": int(po.size),
                "n competencia": int(pr.size),
                "Mediana OWFIT": med_o,
                "Mediana mercado": med_r,
                "Diferencia $": (
                    med_o - med_r
                    if not (np.isnan(med_o) or np.isnan(med_r))
                    else np.nan
                ),
                "Diferencia %": (
                    (med_o / med_r - 1) * 100
                    if med_r and not np.isnan(med_o)
                    else np.nan
                ),
                "Percentil de OWFIT": pct,
                "Posición": etiqueta_posicion(pct),
            }
        )
    return pd.DataFrame(filas)


def matriz_marca_categoria(df_productos: pd.DataFrame) -> pd.DataFrame:
    """Mediana de precio por marca y categoría (solo prendas con precio válido)."""
    return df_productos.pivot_table(
        index="Marca", columns="Categoria_norm", values="Precio_MXN", aggfunc="median"
    ).round(0)


def diagnostico_columnas_ausentes(df_variantes: pd.DataFrame) -> list[dict]:
    """Lista de análisis solicitados que no se pueden ejecutar con esta base."""
    checks = [
        (
            ["Precio_original", "Precio_lista", "Descuento"],
            "Descuentos",
            "promedio, mediana, distribución, % de productos con descuento y descuento por marca/segmento",
        ),
        (
            [
                "Cotton_pct",
                "Nylon_pct",
                "Polyester_pct",
                "Rayon_pct",
                "Elastane_pct",
                "Modal_pct",
            ],
            "Composición de materiales",
            "relación entre materiales y precio",
        ),
        (
            ["Rating"],
            "Rating",
            "calificación promedio por marca y su relación con el precio",
        ),
        (["Reviews"], "Reviews", "volumen de reseñas como proxy de tracción"),
    ]
    faltantes = []
    for columnas, nombre, detalle in checks:
        if not any(c in df_variantes.columns for c in columnas):
            faltantes.append(
                {"analisis": nombre, "columnas": columnas, "detalle": detalle}
            )
    return faltantes

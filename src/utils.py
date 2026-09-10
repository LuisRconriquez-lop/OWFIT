"""Helpers de formato, normalización y reporte de faltantes."""

from __future__ import annotations

import unicodedata

import numpy as np
import pandas as pd

from config import settings


# ------------------------------------------------------------------ formato
def money(x, decimales: int = 0) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    return f"${x:,.{decimales}f}"


def pct(x, decimales: int = 1) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    return f"{x:,.{decimales}f}%"


def num(x, decimales: int = 0) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    return f"{x:,.{decimales}f}"


def delta_str(x, sufijo: str = "%") -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    signo = "+" if x > 0 else ""
    return f"{signo}{x:,.1f}{sufijo}"


# ------------------------------------------------------------------ texto
def slug(texto: str) -> str:
    """minúsculas, sin acentos, sin espacios extra."""
    if texto is None:
        return ""
    t = str(texto).strip().lower()
    t = unicodedata.normalize("NFKD", t)
    t = "".join(c for c in t if not unicodedata.combining(c))
    return " ".join(t.split())


def normalizar_categoria(valor) -> str:
    """Mapea cualquier etiqueta de categoría a la lista canónica del proyecto.

    Si no hay coincidencia, devuelve el valor original con la primera letra en
    mayúscula: nunca se inventa ni se fuerza una categoría existente.
    """
    if valor is None or (isinstance(valor, float) and np.isnan(valor)):
        return "Sin categorizar"
    clave = slug(valor)
    if clave in settings.MAPA_CATEGORIAS:
        return settings.MAPA_CATEGORIAS[clave]
    # Coincidencia parcial: "Legging Belive Moka" -> Leggings
    for k, v in settings.MAPA_CATEGORIAS.items():
        if k and (
            clave.startswith(k + " ")
            or clave.endswith(" " + k)
            or f" {k} " in f" {clave} "
        ):
            return v
    return str(valor).strip()


def segmento_de_marca(marca: str, mapa: dict | None = None) -> str:
    mapa = mapa or settings.SEGMENTO_MARCAS
    return mapa.get(marca, settings.SEGMENTO_DESCONOCIDO)


# ------------------------------------------------------------------ NA
def reporte_faltantes(df: pd.DataFrame) -> pd.DataFrame:
    """Tabla de valores faltantes por columna. No modifica nada."""
    n = len(df)
    filas = []
    for c in df.columns:
        faltan = int(df[c].isna().sum())
        filas.append(
            {
                "Columna": c,
                "Tipo": str(df[c].dtype),
                "Faltantes": faltan,
                "% faltantes": round(100 * faltan / n, 2) if n else np.nan,
                "Valores únicos": int(df[c].nunique(dropna=True)),
            }
        )
    return pd.DataFrame(filas)


def describe_numerica(
    serie: pd.Series, percentiles=(5, 10, 25, 50, 75, 90, 95)
) -> dict:
    """Descriptivos ignorando NA sin eliminarlos del dataframe original."""
    s = pd.to_numeric(serie, errors="coerce").dropna()
    if s.empty:
        return {}
    out = {
        "n": int(s.size),
        "media": float(s.mean()),
        "mediana": float(s.median()),
        "desv_est": float(s.std(ddof=1)) if s.size > 1 else np.nan,
        "min": float(s.min()),
        "max": float(s.max()),
        "rango_intercuartil": float(s.quantile(0.75) - s.quantile(0.25)),
        "coef_variacion": (
            float(s.std(ddof=1) / s.mean()) if s.size > 1 and s.mean() else np.nan
        ),
    }
    for p in percentiles:
        out[f"P{p}"] = float(s.quantile(p / 100))
    return out


def redondeo_comercial(precio: float, modo: str = "Terminación en 9") -> float:
    """Redondeo psicológico de precio. 'Sin redondeo' devuelve el valor tal cual."""
    if precio is None or (isinstance(precio, float) and np.isnan(precio)):
        return np.nan
    if modo == "Sin redondeo":
        return round(float(precio), 2)
    if modo == "Terminación en 9":
        base = int(np.floor(precio / 10.0)) * 10
        return float(base + 9)
    if modo == "Múltiplos de 10":
        return float(int(round(precio / 10.0)) * 10)
    if modo == "Múltiplos de 50":
        return float(int(round(precio / 50.0)) * 50)
    return round(float(precio), 2)

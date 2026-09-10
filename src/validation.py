"""Validación de columnas y contratos de datos.

Cada validador devuelve un ResultadoValidacion con mensajes legibles para
mostrarlos en la interfaz. Ningún validador elimina filas ni rellena NA.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from config import settings
from src.utils import slug


@dataclass
class ResultadoValidacion:
    ok: bool = True
    errores: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)
    notas: list[str] = field(default_factory=list)

    def error(self, msg: str):
        self.errores.append(msg)
        self.ok = False

    def aviso(self, msg: str):
        self.avisos.append(msg)

    def nota(self, msg: str):
        self.notas.append(msg)

    def __add__(self, otro: "ResultadoValidacion") -> "ResultadoValidacion":
        return ResultadoValidacion(
            ok=self.ok and otro.ok,
            errores=self.errores + otro.errores,
            avisos=self.avisos + otro.avisos,
            notas=self.notas + otro.notas,
        )


def renombrar_por_alias(df: pd.DataFrame, alias: dict[str, str]) -> pd.DataFrame:
    """Renombra columnas usando un diccionario de alias tolerante a acentos."""
    nuevo = {}
    for c in df.columns:
        destino = alias.get(slug(c))
        nuevo[c] = destino if destino else c
    return df.rename(columns=nuevo)


def validar_internos(df: pd.DataFrame) -> ResultadoValidacion:
    """Valida el archivo interno de OWFIT (PVP, COGS, cantidad...)."""
    r = ResultadoValidacion()

    faltantes = [
        c for c in settings.COLUMNAS_INTERNAS_REQUERIDAS if c not in df.columns
    ]
    if faltantes:
        r.error(
            "Faltan columnas obligatorias en el archivo interno: "
            + ", ".join(faltantes)
            + ". El archivo debe incluir al menos Producto, PVP y COGS. "
            "Se aceptan nombres equivalentes (por ejemplo 'Precio' en lugar de 'PVP')."
        )
        return r

    for c in settings.COLUMNAS_INTERNAS_OPCIONALES:
        if c not in df.columns:
            if c == "Categoría":
                r.aviso(
                    "No se encontró la columna 'Categoría'. Se intentará inferir a partir "
                    "del nombre del producto; revise el resultado antes de decidir precios."
                )
            elif c == "Cantidad":
                r.aviso(
                    "No se encontró la columna 'Cantidad'. Los promedios se calcularán sin "
                    "ponderar por volumen."
                )

    for c in ["PVP", "COGS", "Cantidad"]:
        if c in df.columns:
            convertidos = pd.to_numeric(df[c], errors="coerce")
            no_numericos = int(convertidos.isna().sum() - df[c].isna().sum())
            if no_numericos > 0:
                r.aviso(
                    f"La columna '{c}' tiene {no_numericos} valor(es) no numérico(s). "
                    "Se marcaron como faltantes y quedan excluidos de los cálculos, "
                    "pero no se eliminaron del archivo."
                )

    if "PVP" in df.columns and "COGS" in df.columns:
        pvp = pd.to_numeric(df["PVP"], errors="coerce")
        cogs = pd.to_numeric(df["COGS"], errors="coerce")
        invertidos = int((cogs > pvp).sum())
        if invertidos:
            r.aviso(
                f"{invertidos} producto(s) tienen COGS mayor que PVP. Se conservan y se "
                "marcan con margen bruto negativo."
            )
        ceros = int((pvp <= 0).sum())
        if ceros:
            r.aviso(
                f"{ceros} producto(s) tienen PVP menor o igual a cero; no se calculan márgenes."
            )

    faltan_pvp = int(pd.to_numeric(df.get("PVP"), errors="coerce").isna().sum())
    if faltan_pvp:
        r.aviso(
            f"{faltan_pvp} producto(s) sin PVP. Se conservan como NA en todas las tablas."
        )

    extras = [
        c
        for c in df.columns
        if c
        not in settings.COLUMNAS_INTERNAS_REQUERIDAS
        + settings.COLUMNAS_INTERNAS_OPCIONALES
        + ["SKU"]
    ]
    if extras:
        r.nota(
            "Columnas adicionales detectadas y conservadas: "
            + ", ".join(map(str, extras))
        )

    return r


def validar_mercado(df: pd.DataFrame) -> ResultadoValidacion:
    r = ResultadoValidacion()
    requeridas = ["Producto", "Categoría", "Precio", "Marca"]
    faltantes = [c for c in requeridas if c not in df.columns]
    if faltantes:
        r.error("Faltan columnas en la base de mercado: " + ", ".join(faltantes))
        return r

    for col, mensaje in [
        ("Descuento", "descuentos"),
        ("Precio_original", "precio de lista"),
        ("Rating", "calificaciones"),
        ("Reviews", "número de reseñas"),
        ("Cotton_pct", "composición de materiales"),
    ]:
        if col not in df.columns:
            r.nota(
                f"La base no incluye '{col}': el análisis de {mensaje} no está disponible."
            )
    return r


def validar_trends(df: pd.DataFrame) -> ResultadoValidacion:
    r = ResultadoValidacion()
    if df is None or df.empty:
        r.error("No se cargó ninguna serie de Google Trends.")
        return r
    if not isinstance(df.index, pd.DatetimeIndex):
        r.error(
            "La columna de tiempo de Google Trends no pudo interpretarse como fecha."
        )
        return r
    if len(df) < 24:
        r.aviso(
            f"Solo hay {len(df)} observaciones mensuales. Con menos de 24 meses no es posible "
            "estimar estacionalidad anual de forma confiable."
        )
    return r


def validar_encuesta(df: pd.DataFrame) -> ResultadoValidacion:
    r = ResultadoValidacion()
    if df is None or df.empty:
        r.error("La encuesta está vacía.")
        return r

    faltan_vw = [c for c in settings.COLS_VAN_WESTENDORP if c not in df.columns]
    if faltan_vw:
        r.nota(
            "No están las cuatro preguntas de Van Westendorp ("
            + ", ".join(faltan_vw)
            + "): no se calcula el rango de precios aceptable."
        )
    faltan_rk = [c for c in settings.COLS_RANKING if c not in df.columns]
    if faltan_rk:
        r.nota("Faltan variables de ranking de atributos: " + ", ".join(faltan_rk))

    cols_int = [f"Purchase_Intention_{p}" for p in settings.PRECIOS_INTENCION]
    faltan_int = [c for c in cols_int if c not in df.columns]
    if faltan_int:
        r.nota("Faltan preguntas de intención de compra: " + ", ".join(faltan_int))

    if len(df) < 100:
        r.aviso(
            f"La muestra es de {len(df)} respuestas. Es suficiente para lectura descriptiva y "
            "direccional, no para inferencia poblacional ni segmentación estadística."
        )
    return r

"""Modelo de rentabilidad y motor de precio recomendado.

Supuesto central sobre el COGS
------------------------------
El COGS que carga OWFIT ya incluye todo lo necesario para tener la prenda en
almacén, embolsada y lista para entregar: fabricación, importación, transporte,
aranceles y bodega. Este módulo NO vuelve a sumar ninguno de esos conceptos.

Solo se agregan costos variables posteriores a la venta:
comisión de pasarela, publicidad, envío, material y mano de obra de envío, y
cualquier otro costo variable que el usuario declare.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict

import numpy as np
import pandas as pd

from config import settings
from src.market import (
    posicion_percentil,
    etiqueta_posicion,
    referencia_precios,
    cuantil_ponderado,
)
from src.utils import redondeo_comercial


# ------------------------------------------------------------------ parámetros
@dataclass
class Parametros:
    pasarela_pct: float = settings.COSTOS_DEFAULT["pasarela_pct"]
    publicidad_pct: float = settings.COSTOS_DEFAULT["publicidad_pct"]
    otros_variables_pct: float = settings.COSTOS_DEFAULT["otros_variables_pct"]
    envio_mxn: float = settings.COSTOS_DEFAULT["envio_mxn"]
    material_envio_mxn: float = settings.COSTOS_DEFAULT["material_envio_mxn"]
    pct_envio_absorbido: float = settings.COSTOS_DEFAULT["pct_envio_absorbido"]
    margen_objetivo_pct: float = settings.MARGEN_OBJETIVO_DEFAULT
    percentil_objetivo: int = settings.PERCENTIL_DEFAULT
    redondeo: str = settings.REDONDEO_PSICOLOGICO_DEFAULT
    min_comparables: int = settings.MIN_COMPARABLES
    aplicar_techo_wtp: bool = False
    techo_wtp: float | None = None
    categoria_techo_wtp: str = settings.CATEGORIA_REFERENCIA_ENCUESTA
    balancear_marcas: bool = True
    modo: str = "El mayor de mercado y margen"

    @property
    def pct_variables(self) -> float:
        """Suma de costos variables expresados como % del PVP (en tanto por uno)."""
        return (
            self.pasarela_pct + self.publicidad_pct + self.otros_variables_pct
        ) / 100.0

    @property
    def costo_fijo_unitario(self) -> float:
        """Costos por unidad que no dependen del precio."""
        factor = self.pct_envio_absorbido / 100.0
        return (self.envio_mxn + self.material_envio_mxn) * factor

    def como_dict(self) -> dict:
        return asdict(self)


# ------------------------------------------------------------------ economía
def economia_unitaria(pvp, cogs, p: Parametros) -> dict:
    """Métricas financieras de una unidad.

    margen_bruto        = (PVP - COGS) / PVP
    utilidad_unidad     = PVP - COGS - %variables x PVP - costos de envío
    margen_contribucion = utilidad_unidad / PVP   (margen de CONTRIBUCIÓN estimado,
                          no margen neto: no incluye costos fijos ni operación)
    """
    pvp = np.nan if pvp is None else float(pvp)
    cogs = np.nan if cogs is None else float(cogs)

    if not np.isfinite(pvp) or pvp <= 0 or not np.isfinite(cogs):
        return {
            "pvp": pvp,
            "cogs": cogs,
            "margen_bruto": np.nan,
            "costo_variable_pct": np.nan,
            "costo_envio": np.nan,
            "utilidad_unidad": np.nan,
            "margen_contribucion": np.nan,
        }

    costo_var = pvp * p.pct_variables
    costo_envio = p.costo_fijo_unitario
    utilidad = pvp - cogs - costo_var - costo_envio
    return {
        "pvp": pvp,
        "cogs": cogs,
        "margen_bruto": (pvp - cogs) / pvp,
        "costo_variable_pct": costo_var,
        "costo_envio": costo_envio,
        "utilidad_unidad": utilidad,
        "margen_contribucion": utilidad / pvp,
    }


def precio_piso_por_margen(
    cogs: float, p: Parametros, margen_objetivo_pct: float | None = None
) -> float:
    """Precio mínimo que alcanza el margen de contribución objetivo.

    Se despeja de:  margen = (P - COGS - v·P - F) / P
      =>  P = (COGS + F) / (1 - v - margen)
    donde v = % de costos variables y F = costos de envío por unidad.
    """
    m = (
        margen_objetivo_pct
        if margen_objetivo_pct is not None
        else p.margen_objetivo_pct
    ) / 100.0
    denominador = 1 - p.pct_variables - m
    if denominador <= 0 or not np.isfinite(cogs):
        return np.nan
    return (cogs + p.costo_fijo_unitario) / denominador


def calcular_precio_recomendado(
    df_internos: pd.DataFrame,
    competencia: pd.DataFrame,
    p: Parametros,
) -> pd.DataFrame:
    """Precio recomendado producto por producto.

    Lógica, en este orden:
      1. Referencia competitiva: percentil objetivo de los precios de la MISMA
         categoría dentro del conjunto competitivo elegido, con las marcas
         balanceadas para que el tamaño del catálogo no distorsione. Si hay
         menos de `min_comparables` productos, no se usa y se registra el motivo.
      2. Piso de rentabilidad: precio que alcanza el margen de contribución
         objetivo dado el COGS y los costos variables.
      3. Se combinan según `modo`: por defecto se toma el mayor de ambos, para
         no recomendar un precio alineado al mercado que destruya el margen.
      4. Techo de disposición a pagar (opcional): solo se aplica a la categoría
         que la encuesta realmente preguntó.
      5. Redondeo comercial.
    Cada producto conserva la bandera de qué criterio terminó mandando.
    """
    filas = []
    for _, row in df_internos.iterrows():
        cat = row.get("Categoria_norm")
        cogs = row.get("COGS", np.nan)
        pvp_actual = row.get("PVP", np.nan)

        ref, pesos = referencia_precios(competencia, cat, p.balancear_marcas)
        n_comp = int(ref.size)
        n_marcas = int(
            competencia.loc[competencia["Categoria_norm"] == cat, "Marca"].nunique()
        )

        # La cobertura de comparables sigue decidiendo si hay referencia de
        # mercado (misma regla de siempre), pero ya no genera texto: el número
        # de comparables y de marcas queda como metadato en las columnas
        # "Competidores comparables" / "Marcas comparables", sin narrativa.
        if n_comp >= p.min_comparables:
            precio_competitivo = cuantil_ponderado(
                ref, pesos, p.percentil_objetivo / 100
            )
        else:
            precio_competitivo = np.nan

        piso = precio_piso_por_margen(cogs, p)

        candidatos = {"Competitivo": precio_competitivo, "Piso de margen": piso}
        validos = {k: v for k, v in candidatos.items() if np.isfinite(v)}

        if not validos:
            precio_base, criterio = np.nan, "Sin base suficiente"
        elif p.modo == "Priorizar mercado" and np.isfinite(precio_competitivo):
            precio_base, criterio = precio_competitivo, "Competitivo"
        elif p.modo == "Priorizar margen" and np.isfinite(piso):
            precio_base, criterio = piso, "Piso de margen"
        else:
            criterio = max(validos, key=validos.get)
            precio_base = validos[criterio]

        conflicto = ""
        if (
            np.isfinite(precio_competitivo)
            and np.isfinite(piso)
            and piso > precio_competitivo
        ):
            conflicto = (
                f"El percentil P{p.percentil_objetivo} de la categoría (${precio_competitivo:,.0f}) "
                f"no alcanza el margen objetivo; el piso de rentabilidad es ${piso:,.0f}."
            )

        techo_aplicado = False
        if (
            p.aplicar_techo_wtp
            and p.techo_wtp
            and np.isfinite(precio_base)
            and cat == p.categoria_techo_wtp
            and precio_base > p.techo_wtp
        ):
            precio_base = float(p.techo_wtp)
            criterio = "Techo de disposición a pagar"
            techo_aplicado = True

        precio_rec = (
            redondeo_comercial(precio_base, p.redondeo)
            if np.isfinite(precio_base)
            else np.nan
        )

        eco_actual = economia_unitaria(pvp_actual, cogs, p)
        eco_rec = economia_unitaria(precio_rec, cogs, p)

        pct_actual = posicion_percentil(pvp_actual, ref, pesos) if n_comp else np.nan
        pct_rec = posicion_percentil(precio_rec, ref, pesos) if n_comp else np.nan

        filas.append(
            {
                "Producto": row.get("Producto"),
                "Categoría": cat,
                "PVP actual": pvp_actual,
                "COGS": cogs,
                "Cantidad": row.get("Cantidad", np.nan),
                "Precio recomendado": precio_rec,
                "Cambio $": (
                    precio_rec - pvp_actual
                    if np.isfinite(precio_rec) and np.isfinite(pvp_actual)
                    else np.nan
                ),
                "Cambio %": (
                    (precio_rec / pvp_actual - 1) * 100
                    if np.isfinite(precio_rec)
                    and np.isfinite(pvp_actual)
                    and pvp_actual
                    else np.nan
                ),
                "Utilidad actual": eco_actual["utilidad_unidad"],
                "Utilidad recomendada": eco_rec["utilidad_unidad"],
                "Margen bruto actual %": (
                    eco_actual["margen_bruto"] * 100
                    if np.isfinite(eco_actual["margen_bruto"])
                    else np.nan
                ),
                "Margen bruto recomendado %": (
                    eco_rec["margen_bruto"] * 100
                    if np.isfinite(eco_rec["margen_bruto"])
                    else np.nan
                ),
                "Margen contribución actual %": (
                    eco_actual["margen_contribucion"] * 100
                    if np.isfinite(eco_actual["margen_contribucion"])
                    else np.nan
                ),
                "Margen contribución recomendado %": (
                    eco_rec["margen_contribucion"] * 100
                    if np.isfinite(eco_rec["margen_contribucion"])
                    else np.nan
                ),
                "Competidores comparables": n_comp,
                "Marcas comparables": n_marcas,
                f"Mercado P{p.percentil_objetivo}": precio_competitivo,
                "Piso por margen": piso,
                "Percentil actual": pct_actual,
                "Percentil recomendado": pct_rec,
                "Posición actual": etiqueta_posicion(pct_actual),
                "Criterio": criterio,
                "Techo WTP aplicado": techo_aplicado,
                "Conflicto": conflicto,
            }
        )

    return pd.DataFrame(filas)


# ------------------------------------------------------------------ agregados
def kpis_portafolio(tabla: pd.DataFrame, p: Parametros) -> dict:
    """KPIs de portafolio. Si hay 'Cantidad', se pondera por volumen."""
    t = tabla.copy()
    tiene_cantidad = "Cantidad" in t.columns and t["Cantidad"].notna().any()
    w = t["Cantidad"].fillna(0) if tiene_cantidad else pd.Series(1.0, index=t.index)

    def prom(col):
        s = pd.to_numeric(t[col], errors="coerce")
        m = s.notna() & (w > 0) if tiene_cantidad else s.notna()
        if not m.any():
            return np.nan
        return (
            float(np.average(s[m], weights=w[m]))
            if tiene_cantidad
            else float(s[m].mean())
        )

    con_rec = t["Precio recomendado"].notna() & t["PVP actual"].notna()
    return {
        "productos": int(len(t)),
        "con_recomendacion": int(con_rec.sum()),
        "ponderado_por_volumen": bool(tiene_cantidad),
        "precio_actual_prom": prom("PVP actual"),
        "precio_rec_prom": prom("Precio recomendado"),
        "cambio_pct_prom": prom("Cambio %"),
        "margen_bruto_prom": prom("Margen bruto actual %"),
        "margen_contrib_prom": prom("Margen contribución actual %"),
        "margen_contrib_rec_prom": prom("Margen contribución recomendado %"),
        "utilidad_prom": prom("Utilidad actual"),
        "utilidad_rec_prom": prom("Utilidad recomendada"),
        "percentil_prom": prom("Percentil actual"),
        # Inventario declarado en el archivo interno: PVP x piezas en existencia.
        # No es venta ni ingreso: es el valor a precio de lista de lo que hay.
        # Sin columna 'Cantidad' no hay piezas que valorar y queda en NaN.
        "valor_inventario_pvp": (
            float(
                (pd.to_numeric(t["PVP actual"], errors="coerce") * w).sum(skipna=True)
            )
            if tiene_cantidad
            else np.nan
        ),
        "piezas_totales": float(w.sum()) if tiene_cantidad else np.nan,
        "utilidad_total_actual": float(
            (t["Utilidad actual"] * (t["Cantidad"] if tiene_cantidad else 1)).sum(
                skipna=True
            )
        ),
        "utilidad_total_rec": float(
            (t["Utilidad recomendada"] * (t["Cantidad"] if tiene_cantidad else 1)).sum(
                skipna=True
            )
        ),
        "productos_bajo_costo": int((t["Utilidad actual"] < 0).sum()),
    }


def resumen_por_categoria(tabla: pd.DataFrame) -> pd.DataFrame:
    """Comparación por categoría entre situación actual y recomendada."""
    if tabla.empty:
        return pd.DataFrame()
    g = tabla.groupby("Categoría", dropna=False)
    out = g.agg(
        Productos=("Producto", "count"),
        **{
            "Precio actual": ("PVP actual", "mean"),
            "Precio recomendado": ("Precio recomendado", "mean"),
            "Margen contribución actual %": ("Margen contribución actual %", "mean"),
            "Margen contribución recomendado %": (
                "Margen contribución recomendado %",
                "mean",
            ),
            "Utilidad actual": ("Utilidad actual", "mean"),
            "Utilidad recomendada": ("Utilidad recomendada", "mean"),
            "Comparables": ("Competidores comparables", "max"),
        },
    ).reset_index()
    out["Cambio %"] = (out["Precio recomendado"] / out["Precio actual"] - 1) * 100
    if "Cantidad" in tabla.columns and tabla["Cantidad"].notna().any():
        vol = (
            tabla.assign(
                _delta=(tabla["Utilidad recomendada"] - tabla["Utilidad actual"])
                * tabla["Cantidad"]
            )
            .groupby("Categoría")["_delta"]
            .sum()
        )
        out["Impacto en utilidad ($)"] = out["Categoría"].map(vol)
    return out.sort_values("Cambio %", ascending=False)


# ------------------------------------------------------------------ packaging
def escenario_packaging(
    tabla: pd.DataFrame,
    p: Parametros,
    costo_packaging: float,
    incremento_pct: float,
    categoria: str = "Sets/Conjuntos",
    usar_precio_recomendado: bool = False,
) -> pd.DataFrame:
    """Compara el escenario actual contra uno con packaging premium en sets.

    El costo del packaging se suma al COGS porque es un costo adicional de tener
    la prenda lista para entregar; el incremento de precio es la hipótesis a
    evaluar, no un resultado.
    """
    base_col = "Precio recomendado" if usar_precio_recomendado else "PVP actual"
    sets = tabla[tabla["Categoría"] == categoria].copy()
    if sets.empty:
        return pd.DataFrame()

    filas = []
    for _, r in sets.iterrows():
        precio_base = r[base_col]
        cogs = r["COGS"]
        actual = economia_unitaria(precio_base, cogs, p)
        nuevo_precio = (
            precio_base * (1 + incremento_pct / 100)
            if np.isfinite(precio_base)
            else np.nan
        )
        nuevo_precio = (
            redondeo_comercial(nuevo_precio, p.redondeo)
            if np.isfinite(nuevo_precio)
            else np.nan
        )
        con_pack = economia_unitaria(nuevo_precio, cogs + costo_packaging, p)

        filas.append(
            {
                "Producto": r["Producto"],
                "Cantidad": r.get("Cantidad", np.nan),
                "Precio actual": precio_base,
                "Precio con packaging": nuevo_precio,
                "COGS actual": cogs,
                "COGS con packaging": cogs + costo_packaging,
                "Utilidad actual": actual["utilidad_unidad"],
                "Utilidad con packaging": con_pack["utilidad_unidad"],
                "Δ Utilidad": con_pack["utilidad_unidad"] - actual["utilidad_unidad"],
                "Margen contribución actual %": actual["margen_contribucion"] * 100,
                "Margen contribución con packaging %": con_pack["margen_contribucion"]
                * 100,
                "Δ Margen (pp)": (
                    con_pack["margen_contribucion"] - actual["margen_contribucion"]
                )
                * 100,
            }
        )
    return pd.DataFrame(filas)


def precio_minimo_packaging(
    precio_actual: float, cogs: float, costo_packaging: float, p: Parametros
) -> float:
    """Aumento de precio necesario para que el packaging no reduzca el margen %."""
    eco = economia_unitaria(precio_actual, cogs, p)
    if not np.isfinite(eco["margen_contribucion"]):
        return np.nan
    return precio_piso_por_margen(
        cogs + costo_packaging, p, eco["margen_contribucion"] * 100
    )

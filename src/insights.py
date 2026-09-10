"""Hallazgos automáticos.

Cada hallazgo se construye a partir de una cifra calculada en esta sesión y la
cita en el texto. Si la condición no se cumple, el hallazgo no aparece: no hay
frases de relleno ni conclusiones que no se sostengan en los datos cargados.

Cada hallazgo declara además una PRIORIDAD (0-100) que ordena la lectura por
impacto en dinero o en decisión, no por el orden en que se calculó. La página
de Resumen muestra solo los más altos y manda el resto a un expander; ver
`dividir_por_prioridad`.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from config import settings
from src.utils import money, pct

# Prioridades declaradas en un solo lugar para poder compararlas de un vistazo.
# Arriba, lo que cuesta o gana dinero de forma directa; abajo, lo descriptivo.
PRIORIDAD = {
    "perdida": 100,  # productos que venden por debajo de su costo variable
    "margen_objetivo": 90,  # brecha de margen contra la meta, en todo el portafolio
    "brecha_mercado": 85,  # categoría más barata que el mercado, con impacto en $
    "sobreprecio": 70,  # categoría más cara que el mercado
    "hueco_catalogo": 65,  # categorías donde la competencia vende y OWFIT no
    "wtp": 60,  # precio contra el techo declarado e intención de compra
    "oportunidad_cat": 50,  # ajuste sugerido por categoría
    "conflicto": 45,  # mercado y margen apuntan a precios distintos
    "posicion": 40,  # percentil agregado del portafolio
    "rango_wtp": 35,  # rango aceptable declarado
}


def dividir_por_prioridad(lista: list[tuple], maximo: int = 5) -> tuple[list, list]:
    """Parte los hallazgos en (visibles, resto) ordenando por prioridad.

    No descarta nada: lo que no cabe en los `maximo` visibles se devuelve aparte
    para mostrarlo en un expander cerrado.
    """
    ordenada = sorted(lista, key=lambda h: h[2] if len(h) > 2 else 0, reverse=True)
    return ordenada[:maximo], ordenada[maximo:]


def hallazgos_portafolio(
    tabla: pd.DataFrame, kpis: dict, params
) -> list[tuple[str, str, int]]:
    """Devuelve lista de (texto, tipo, prioridad) con tipo en {'ok','alerta','neutro'}."""
    out: list[tuple[str, str, int]] = []
    if tabla.empty:
        return out

    # 1. Productos que pierden dinero
    perdida = tabla[tabla["Utilidad actual"] < 0]
    if len(perdida):
        nombres = ", ".join(perdida["Producto"].head(3).astype(str))
        out.append(
            (
                f"<b>{len(perdida)} producto(s) no cubren sus costos variables</b> al precio actual "
                f"({nombres}{'…' if len(perdida) > 3 else ''}). Con envío de "
                f"{money(params.envio_mxn)} y {pct(params.pasarela_pct + params.publicidad_pct)} "
                "de costos sobre el precio, cada venta resta utilidad.",
                "alerta",
                PRIORIDAD["perdida"],
            )
        )

    # 2. Brecha de margen contra el objetivo
    bajo = tabla[tabla["Margen contribución actual %"] < params.margen_objetivo_pct]
    if len(bajo):
        faltante = (
            params.margen_objetivo_pct - bajo["Margen contribución actual %"].mean()
        )
        out.append(
            (
                f"<b>{len(bajo)} de {len(tabla)} productos quedan por debajo del margen objetivo</b> "
                f"de {pct(params.margen_objetivo_pct, 0)}. En promedio les faltan "
                f"{faltante:.1f} puntos porcentuales de margen de contribución.",
                "alerta" if len(bajo) > len(tabla) / 2 else "neutro",
                PRIORIDAD["margen_objetivo"],
            )
        )

    # 3. Categoría con mayor oportunidad
    # El número de comparables ya no se narra aquí: es metadato de la tabla de
    # productos y del tooltip, no una advertencia que compita con la decisión.
    cat = oportunidad_por_categoria(tabla)
    if not cat.empty:
        top = cat.iloc[0]
        if np.isfinite(top["Cambio %"]) and top["Cambio %"] > 2:
            texto = (
                f"<b>{top['Categoría']} concentra la mayor oportunidad de precio</b>: "
                f"{pct(top['Cambio %'])} de ajuste sugerido sobre {int(top['Productos'])} producto(s)."
            )
            if "Impacto en utilidad ($)" in cat.columns and np.isfinite(
                top.get("Impacto en utilidad ($)", np.nan)
            ):
                texto += f" Impacto estimado sobre el inventario declarado: {money(top['Impacto en utilidad ($)'])}."
            out.append((texto, "ok", PRIORIDAD["oportunidad_cat"]))

    # 4. Posición competitiva agregada
    p = kpis.get("percentil_prom")
    if p is not None and np.isfinite(p):
        if p < 35:
            out.append(
                (
                    f"<b>El portafolio se ubica en el percentil {p:.0f} de sus categorías.</b> "
                    "Es una posición de entrada: hay espacio de precio antes de tocar la mediana "
                    "del mercado, pero conviene revisar si esa posición es una decisión de marca "
                    "o el resultado de no haber ajustado precios.",
                    "neutro",
                    PRIORIDAD["posicion"],
                )
            )
        elif p > 70:
            out.append(
                (
                    f"<b>El portafolio se ubica en el percentil {p:.0f}</b>: precios por arriba de la "
                    "mayoría de los comparables. Sostener esa posición exige una diferencia visible "
                    "en producto, servicio o marca.",
                    "neutro",
                    PRIORIDAD["posicion"],
                )
            )
        else:
            out.append(
                (
                    f"<b>El portafolio se ubica en el percentil {p:.0f}</b>, cerca de la mediana de sus "
                    "categorías. La posición es coherente con un producto mid-market.",
                    "ok",
                    PRIORIDAD["posicion"],
                )
            )

    # 5. Conflictos entre mercado y margen
    conflictos = tabla[tabla["Conflicto"].astype(str).str.len() > 0]
    if len(conflictos):
        out.append(
            (
                f"<b>En {len(conflictos)} producto(s) el precio de mercado no alcanza para el margen "
                f"objetivo.</b> Alinear el precio a P{params.percentil_objetivo} dejaría el margen por "
                "debajo de la meta; las salidas son bajar COGS, revisar el costo de envío o aceptar "
                "un margen menor en esas referencias.",
                "alerta",
                PRIORIDAD["conflicto"],
            )
        )

    return out


def oportunidad_por_categoria(tabla: pd.DataFrame) -> pd.DataFrame:
    from src.pricing import resumen_por_categoria

    r = resumen_por_categoria(tabla)
    if r.empty:
        return r
    columna = (
        "Impacto en utilidad ($)"
        if "Impacto en utilidad ($)" in r.columns
        else "Cambio %"
    )
    return r.sort_values(columna, ascending=False)


def hallazgos_encuesta(
    df: pd.DataFrame, vw: dict, gg: pd.DataFrame, precio_referencia: float | None = None
) -> list[tuple[str, str, int]]:
    """Lectura de la encuesta: disposición a pagar e intención de compra.

    No incluye composición ni segmentación de la muestra (edad, gasto habitual):
    describía a quién contestó, no qué hacer con el precio. El alcance de la
    muestra vive una sola vez, en el pie de página global (`ui.pie_muestra`).
    """
    out: list[tuple[str, str, int]] = []

    if vw.get("disponible"):
        p = vw["puntos"]
        out.append(
            (
                f"<b>El rango de precio aceptable declarado va de {money(p['PMC'])} a {money(p['PME'])}</b>, "
                f"con punto óptimo en {money(p['OPP'])} (Van Westendorp, {vw['n_valido']} respuestas "
                "consistentes). Se refiere a la prenda genérica que se preguntó, no a todo el catálogo.",
                "ok",
                PRIORIDAD["rango_wtp"],
            )
        )

    sobre_techo = (
        vw.get("disponible")
        and precio_referencia
        and np.isfinite(precio_referencia)
        and precio_referencia > vw["puntos"]["PME"]
    )
    caida = (
        gg["% top-2-box"].iloc[0] - gg["% top-2-box"].iloc[-1]
        if not gg.empty
        else np.nan
    )

    # Techo declarado y caída de intención son la misma decisión —hasta dónde
    # aguanta el precio—, así que van en una sola oración cuando ambos existen.
    if sobre_techo and np.isfinite(caida):
        out.append(
            (
                f"<b>El precio de referencia ({money(precio_referencia)}) está por encima del techo "
                f"declarado ({money(vw['puntos']['PME'])})</b> y la intención de compra alta cae "
                f"{caida:.0f} puntos entre {money(gg['Precio'].iloc[0])} y {money(gg['Precio'].iloc[-1])}.",
                "alerta",
                PRIORIDAD["wtp"],
            )
        )
    elif sobre_techo:
        out.append(
            (
                f"<b>El precio de referencia ({money(precio_referencia)}) está por encima del techo "
                f"declarado ({money(vw['puntos']['PME'])}).</b> Antes de mover precios conviene "
                "contrastarlo con conversión y devoluciones reales.",
                "alerta",
                PRIORIDAD["wtp"],
            )
        )

    if not gg.empty:
        mejor = gg.loc[gg["Ingreso relativo"].idxmax()]
        out.append(
            (
                f"<b>El ingreso esperado se maximiza en {money(mejor['Precio'])}</b> dentro de los "
                f"{len(gg)} puntos de precio que se preguntaron.",
                "ok",
                PRIORIDAD["rango_wtp"],
            )
        )

    return out


def hallazgos_mercado(
    productos: pd.DataFrame, comparacion: pd.DataFrame, impactos: dict | None = None
) -> list[tuple[str, str, int]]:
    """`impactos` mapea categoría -> impacto en utilidad ($) ya calculado en
    `oportunidad_por_categoria`. Se cita en la brecha más amplia para que el
    hallazgo lleve la cifra de dinero, no solo el porcentaje."""
    out: list[tuple[str, str, int]] = []
    if comparacion.empty:
        return out

    con_dato = comparacion.dropna(subset=["Diferencia %"])
    if con_dato.empty:
        return out

    impactos = impactos or {}
    arriba = con_dato[con_dato["Diferencia %"] > 10]
    abajo = con_dato[con_dato["Diferencia %"] < -10]

    if len(abajo):
        peor = abajo.sort_values("Diferencia %").iloc[0]
        texto = (
            f"<b>{peor['Categoría']} está {pct(abs(peor['Diferencia %']))} por debajo de la mediana del "
            f"mercado</b> ({money(peor['Mediana OWFIT'])} contra {money(peor['Mediana mercado'])}): es la "
            "brecha más amplia del catálogo"
        )
        impacto = impactos.get(peor["Categoría"], np.nan)
        if impacto is not None and np.isfinite(impacto):
            texto += f", con impacto estimado de {money(impacto)} sobre el inventario declarado."
        else:
            texto += "."
        out.append((texto, "ok", PRIORIDAD["brecha_mercado"]))

    if len(arriba):
        alto = arriba.sort_values("Diferencia %", ascending=False).iloc[0]
        out.append(
            (
                f"<b>{alto['Categoría']} cobra {pct(alto['Diferencia %'])} más que la mediana</b> "
                f"({money(alto['Mediana OWFIT'])} contra {money(alto['Mediana mercado'])}).",
                "neutro",
                PRIORIDAD["sobreprecio"],
            )
        )

    sin_presencia = comparacion[
        (comparacion["n OWFIT"] == 0) & (comparacion["n competencia"] >= 20)
    ]
    if len(sin_presencia):
        cats = ", ".join(sin_presencia["Categoría"].astype(str))
        out.append(
            (
                f"<b>No hay productos en {cats}</b>, donde la competencia sí tiene surtido: es hueco de "
                "catálogo, no problema de precio.",
                "neutro",
                PRIORIDAD["hueco_catalogo"],
            )
        )
    return out

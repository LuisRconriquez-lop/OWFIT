"""Metodología, supuestos, limitaciones y enlaces a recursos externos."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from config import settings
from src import ui
from src.utils import pct


def render(ctx):
    ui.kicker("Metodología")
    st.title("Metodología")
    st.caption(
        "Qué se calculó, con qué datos, bajo qué supuestos y qué no se puede concluir."
    )

    tabs = st.tabs(["Fuentes", "Cálculos", "Confidencialidad", "Recursos"])

    # ------------------------------------------------------------- fuentes
    with tabs[0]:
        st.markdown("### Las cuatro fuentes del proyecto")
        fuentes = pd.DataFrame(
            [
                {
                    "Fuente": "Base de mercado",
                    "Naturaleza": "Pública (catálogos en línea)",
                    "Contenido": f"{len(ctx.mercado_variantes):,} variantes, "
                    f"{ctx.mercado_productos['Marca'].nunique()} marcas",
                    "Uso": "Percentiles de precio por categoría, posición competitiva",
                },
                {
                    "Fuente": "Encuesta de consumidor",
                    "Naturaleza": "Investigación propia",
                    "Contenido": f"{len(ctx.encuesta)} respuestas",
                    "Uso": "Importancia de atributos, disposición a pagar, intención de compra",
                },
                {
                    "Fuente": "Google Trends",
                    "Naturaleza": "Pública",
                    "Contenido": f"{ctx.trends.shape[1] if not ctx.trends.empty else 0} términos, "
                    f"{len(ctx.trends)} meses",
                    "Uso": "Estacionalidad y pronóstico de interés de búsqueda",
                },
                {
                    "Fuente": "Datos internos de OWFIT",
                    "Naturaleza": "Confidencial, carga externa",
                    "Contenido": f"{len(ctx.internos)} productos"
                    + (
                        " (demostración ficticia)"
                        if ctx.es_demo
                        else " (archivo del usuario)"
                    ),
                    "Uso": "PVP, COGS y piezas para el modelo de rentabilidad",
                },
            ]
        )
        st.dataframe(fuentes, use_container_width=True, hide_index=True)

        st.markdown("### Preparación de la base de mercado")
        st.markdown("""
- Cada hoja del archivo corresponde a una marca; se unen en una sola tabla con la columna `Marca`.
- Los catálogos en dólares se convierten a pesos con el tipo de cambio de la barra lateral.
- Las categorías se normalizan a una lista única para que la comparación sea entre equivalentes.
  Un producto capturado como «Legging» y otro como «Leggings» terminan en la misma categoría.
- Las tallas y colores se agrupan a nivel producto. Sin esta agrupación, una marca con veinte
  variantes por modelo pesaría veinte veces más que otra con una sola.
- Accesorios, productos sin categorizar y registros con precio cero se **marcan y se excluyen**
  de las comparaciones por categoría. No se eliminan de la base: su conteo está en el EDA.
- Los faltantes se conservan como faltantes. Nunca se sustituyen por cero.
            """)

    # ------------------------------------------------------------- cálculos
    with tabs[1]:
        p = ctx.params
        st.markdown("### Métricas financieras")
        st.latex(r"\text{Margen bruto} = \frac{PVP - COGS}{PVP}")
        st.latex(
            r"\text{Utilidad por unidad} = PVP - COGS - PVP\cdot(c_{pasarela} + c_{publicidad} + c_{otros})"
            r" - \text{envío} - \text{material de envío}"
        )
        st.latex(
            r"\text{Margen de contribución} = \frac{\text{Utilidad por unidad}}{PVP}"
        )
        ui.hallazgo(
            "Se llama <b>margen de contribución estimado</b>, no margen neto. No incluye renta, "
            "nómina, software, devoluciones ni impuestos sobre la utilidad. Con la información "
            "disponible no es posible calcular un margen neto verdadero.",
            "neutro",
        )
        ui.hallazgo(
            "El <b>COGS</b> se toma como el costo de tener la prenda en almacén, embolsada y lista "
            "para entregar. Fabricación, importación, transporte, aranceles y bodega ya están "
            "dentro. El modelo no los vuelve a sumar.",
            "neutro",
        )

        st.markdown("### Precio recomendado")
        st.markdown(f"""
El precio no sale de una regla fija. Se construye en cinco pasos:

1. **Referencia competitiva.** Percentil objetivo (hoy **P{p.percentil_objetivo}**) de los precios
   de la misma categoría dentro del conjunto competitivo elegido. Las marcas se balancean para
   que el tamaño del catálogo no defina la distribución.
2. **Piso de rentabilidad.** Precio que alcanza el margen de contribución objetivo
   (hoy **{pct(p.margen_objetivo_pct, 0)}**) dado el COGS del producto:
""")
        st.latex(
            r"P_{\min} = \frac{COGS + \text{costos fijos por unidad}}{1 - c_{variables} - m_{objetivo}}"
        )
        st.markdown(f"""
3. **Combinación.** Criterio activo: *{p.modo.lower()}*. Por defecto se toma el mayor de los dos,
   para no recomendar un precio alineado al mercado que deje el margen por debajo de la meta.
   Cuando ambos apuntan a precios distintos, el producto queda marcado como conflicto.
4. **Techo de disposición a pagar.** Opcional y solo aplicable a la categoría que la encuesta
   preguntó realmente ({settings.CATEGORIA_REFERENCIA_ENCUESTA}). No se extrapola a categorías
   que nunca se preguntaron.
5. **Redondeo comercial** ({p.redondeo.lower()}).

Si una categoría tiene menos de **{p.min_comparables}** comparables, la referencia de mercado
no se usa y el producto se marca. Con pocos comparables un percentil es ruido, no información.
            """)

        st.markdown("### Selección del modelo de estacionalidad")
        st.markdown(f"""
Se comparan tres modelos: **Seasonal Naive** (y(t) = y(t-12), baseline obligatorio), **ETS /
Holt-Winters** (rejilla de tendencia, amortiguamiento y estacionalidad elegida por AICc) y
**SARIMA** (periodo estacional 12; los órdenes de diferenciación se fijan con pruebas ADF sobre
la serie en nivel y diferenciada, y p/q/P/Q se eligen por AICc en una rejilla acotada).

No hay un ARIMA sin componente estacional en la comparación: sin ese componente, el pronóstico
converge a la media en 1-2 pasos y no puede reproducir un patrón anual — es matemáticamente
incapaz de decir en qué mes conviene concentrar marketing.

La validación es un holdout estrictamente temporal de los últimos {settings.BACKTEST_HOLDOUT_MESES}
meses (nunca aleatorio): se entrena con todo lo anterior y se compara el pronóstico contra esos
meses reales.

**El error de pronóstico (MAE/RMSE) no decide solo.** Un modelo que siempre predice la media
nunca se equivoca de forma escandalosa, así que en series ruidosas puede ganarle en RMSE a un
modelo que sí seguía el ciclo anual, con correlación 0.00 contra la forma real. Por eso primero
se descarta cualquier modelo cuyo pronóstico sea esencialmente plano (rango menor al 5% de la
media de la serie, o correlación con la forma real menor a 0.10) y solo entre los que sobreviven
gana el menor RMSE — con empate a favor del modelo más simple si la diferencia es menor a 2%. Si
todos quedan descartados, la serie se marca como sin señal de forecast utilizable.
            """)

        st.markdown("### Segmentación de consumidores")
        st.markdown(f"""
El clustering se somete a cuatro pruebas antes de usarse: tamaño muestral de al menos
{settings.CLUSTER_MIN_N} respuestas, variables no ipsativas, silueta de al menos
{settings.CLUSTER_MIN_SILHOUETTE} y grupos de tamaño accionable. Mientras esas pruebas no se
cumplan, el dashboard no presenta segmentos de consumidor: la lectura de la encuesta se limita
a disposición a pagar e intención de compra.
            """)

    # ------------------------------------------------------------- privacidad
    with tabs[2]:
        st.markdown("### Separación de datos")
        st.markdown("""
**Datos del proyecto** (viven en el repositorio, en `data/`):
mercado, encuesta y Google Trends. Son públicos o de investigación propia.

**Datos confidenciales de OWFIT** (nunca en el repositorio):
PVP interno, COGS, cantidad de piezas y cualquier otra variable interna.
            """)
        ui.hallazgo(
            "Los datos internos se cargan desde un archivo externo y se procesan <b>solo en memoria "
            "durante la sesión</b>. No se escriben en el proyecto, no están dentro del código y no "
            "aparecen en ejemplos ni en documentación.",
            "ok",
        )
        st.markdown(
            f"""
El archivo de demostración incluido (`{settings.PATH_DEMO_INTERNO.name}`) contiene
**{len(ctx.internos) if ctx.es_demo else 20} productos completamente inventados**. Su único
propósito es permitir que el dashboard funcione sin datos reales.

**Estructura esperada del archivo interno**

| Columna | Obligatoria | Descripción |
|---|---|---|
| Producto | Sí | Nombre o identificador |
| PVP | Sí | Precio de **mayoreo** en MXN (ver conversión abajo) |
| COGS | Sí | Costo de la prenda lista para entregar |
| Categoría | Recomendada | Si falta, se infiere del nombre del producto |
| Cantidad | Recomendada | Piezas; permite ponderar promedios por volumen |

Se aceptan nombres equivalentes (Precio, Costo, Piezas, Unidades) y columnas adicionales,
que se conservan sin modificar.

**Conversión de mayoreo a minorista.** La columna PVP del archivo interno es el precio de
mayoreo que maneja Grupo Garmac, no lo que paga la clienta final. Al cargar el archivo, el
dashboard suma un recargo fijo de """
            + f"{settings.RECARGO_MINORISTA_PCT:.0f}%"
            + """ para
obtener el precio al público, y **desde ahí en adelante toda cifra de "PVP" o "precio actual"
en el dashboard (Simulador, Rentabilidad, Competencia, Escenarios, Packaging, Resumen) es ya
precio minorista.** Esto es necesario porque la base de mercado con la que se compara reporta
precios minoristas: comparar el precio de mayoreo directo contra esos precios hundiría
artificialmente la posición competitiva y el precio recomendado. El precio de mayoreo original
no se descarta: se conserva aparte y se muestra explícitamente en la página Escenarios.
            """
        )

    # ------------------------------------------------------------- recursos
    with tabs[3]:
        st.markdown("### Recursos y documentación")
        st.caption(
            "Edite la lista en `config/settings.py` → `ENLACES_RECURSOS` para agregar los enlaces "
            "del proyecto."
        )
        for r in settings.ENLACES_RECURSOS:
            if r.get("url"):
                st.markdown(
                    f"- [{r['nombre']}]({r['url']})"
                    + (f" — {r['nota']}" if r.get("nota") else "")
                )
            else:
                st.markdown(
                    f"- {r['nombre']} — *pendiente de enlace*"
                    + (f" · {r['nota']}" if r.get("nota") else "")
                )

        st.markdown("### Estado de validación de esta sesión")
        for titulo, res in [
            ("Base de mercado", ctx.val_mercado),
            ("Encuesta", ctx.val_encuesta),
            ("Google Trends", ctx.val_trends),
            ("Archivo interno", ctx.val_internos),
        ]:
            with st.expander(
                f"{titulo} · {'sin errores' if res.ok else 'con errores'}"
            ):
                if not (res.errores or res.avisos or res.notas):
                    st.caption("Sin observaciones.")
                for e in res.errores:
                    st.error(e)
                for a in res.avisos:
                    st.warning(a)
                for n in res.notas:
                    st.caption(n)

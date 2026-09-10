"""
Dashboard de pricing OWFIT México.

Ejecutar:  streamlit run app.py

Separación de datos:
  * Datos del proyecto (mercado, encuesta, Google Trends) viven en data/ y son
    públicos o de investigación propia.
  * Datos internos de OWFIT (PVP, COGS, cantidades) NUNCA están en el código:
    se cargan desde un archivo externo y se procesan solo en memoria.
"""

from __future__ import annotations

import base64
import warnings

import streamlit as st

warnings.filterwarnings("ignore")

from config import settings  # noqa: E402
from src import loaders, market, pricing, survey, trends, ui  # noqa: E402

st.set_page_config(
    page_title="OWFIT · Pricing México",
    page_icon="◧",
    layout="wide",
    initial_sidebar_state="expanded",
)
ui.aplicar_tema()


# ------------------------------------------------------------------ carga
@st.cache_data(show_spinner="Cargando base de mercado…")
def _mercado(tipo_cambio: dict):
    variantes, res = loaders.cargar_mercado(tipo_cambio=tipo_cambio)
    productos = loaders.agregar_a_producto(variantes)
    return variantes, productos, res


@st.cache_data(show_spinner="Cargando encuesta…")
def _encuesta():
    return loaders.cargar_encuesta()


@st.cache_data(show_spinner="Cargando Google Trends…")
def _trends():
    return loaders.cargar_trends()


@st.cache_data(show_spinner="Cargando interés por estado…")
def _region():
    return loaders.cargar_region()


@st.cache_data(show_spinner=False)
def _geojson_estados():
    return loaders.cargar_geojson_estados()


@st.cache_data(show_spinner="Leyendo archivo interno…")
def _internos_demo():
    return loaders.cargar_internos(es_demo=True)


def _internos_usuario(archivo):
    return loaders.cargar_internos(archivo, es_demo=False)


# ------------------------------------------------------------------ sidebar
def barra_lateral():
    with st.sidebar:
        logo = settings.ROOT / "assets" / "images" / "brand" / "logo_owfit_sinFondo.png"
        if logo.exists():
            # El logo es un trazo oscuro sobre fondo transparente: sobre el sidebar oscuro
            # necesita una tarjeta clara detrás para tener contraste suficiente.
            logo_b64 = base64.b64encode(logo.read_bytes()).decode()
            st.markdown(
                f'<div style="background:#F2EDE9; border-radius:10px; padding:0.6rem 0.9rem; '
                f'display:inline-block; margin-bottom:0.7rem;">'
                f'<img src="data:image/png;base64,{logo_b64}" alt="OWFIT" '
                f'style="width:130px; display:block;" />'
                f"</div>",
                unsafe_allow_html=True,
            )
        st.markdown(
            '<div class="marca-titulo">OWFIT</div>'
            '<div class="marca-sub">Pricing Intelligence · México 2026</div>',
            unsafe_allow_html=True,
        )
        st.markdown("---")

        paginas_nav = [
            "Resumen",
            "Pricing",
            "Simulador",
            "Competencia",
            "Rentabilidad",
            "Encuesta",
            "EDA de mercado",
            "Estacionalidad",
            "Escenarios",
            "Packaging",
            "Metodología",
        ]
        pagina = st.radio(
            "Navegación",
            paginas_nav,
            format_func=ui.etiqueta_nav,
            label_visibility="collapsed",
        )

        st.session_state.setdefault("uploader_key", 0)
        st.session_state.setdefault("ultimo_archivo_nombre", None)

        st.markdown("---")
        st.markdown("**Datos internos de OWFIT**")
        archivo = st.file_uploader(
            "Archivo Excel o CSV con Producto, PVP, COGS y Cantidad",
            type=["xlsx", "xls", "csv"],
            help="Se procesa en memoria durante la sesión. No se guarda en el proyecto.",
            key=f"archivo_interno_{st.session_state.uploader_key}",
        )
        if archivo is None:
            st.caption("Sin archivo: se usan datos de demostración ficticios.")
            try:
                with open(settings.PATH_DEMO_INTERNO, "rb") as f:
                    st.download_button(
                        "Descargar plantilla de demostración",
                        f.read(),
                        file_name="OWFIT_DEMO_datos_internos.xlsx",
                        use_container_width=True,
                    )
            except FileNotFoundError:
                st.caption("Genere la plantilla con `python scripts/generar_demo.py`.")
        else:
            # La flor solo crece una vez que hay un archivo real cargado, no
            # antes (con datos de demostración no hay nada que "analizar").
            if archivo.name != st.session_state.ultimo_archivo_nombre:
                st.session_state.ultimo_archivo_nombre = archivo.name
                st.session_state["_flor_petalos"] = [True] * 5

            recien_pelada, restantes = ui.flor_interactiva(key="flor")
            if recien_pelada:
                # Easter egg: deshojada por completo (clic directo en cada
                # pétalo), se suelta el archivo cargado. La próxima vez que
                # el uploader se vuelva a dibujar, con la key incrementada,
                # aparece vacío.
                st.session_state.uploader_key += 1
                st.session_state.ultimo_archivo_nombre = None
            if restantes == 0:
                st.caption(
                    "🥀 Se deshojó por completo: se quitó el archivo cargado. Sube uno nuevo cuando quieras."
                )

        # Los parámetros de pricing, costos variables y conjunto competitivo se
        # ajustan por producto en el Simulador; aquí solo se fijan sus valores
        # por defecto para el resto de las páginas.
        percentil = settings.PERCENTIL_DEFAULT
        margen = settings.MARGEN_OBJETIVO_DEFAULT
        modo = "El mayor de mercado y margen"
        redondeo = "Terminación en 9"

        pasarela = settings.COSTOS_DEFAULT["pasarela_pct"]
        publicidad = settings.COSTOS_DEFAULT["publicidad_pct"]
        otros = settings.COSTOS_DEFAULT["otros_variables_pct"]
        envio = settings.COSTOS_DEFAULT["envio_mxn"]
        material = settings.COSTOS_DEFAULT["material_envio_mxn"]
        absorbido = settings.COSTOS_DEFAULT["pct_envio_absorbido"]

        segmentos = sorted(
            {s for s in settings.SEGMENTO_MARCAS.values() if s != "OWFIT"}
        )
        elegidos = segmentos
        balancear = True
        min_comp = settings.MIN_COMPARABLES
        fx = settings.TIPO_CAMBIO_DEFAULT["USD"]

    tipo_cambio = dict(settings.TIPO_CAMBIO_DEFAULT)
    tipo_cambio["USD"] = fx

    if (pasarela + publicidad + otros) / 100.0 + margen / 100.0 >= 1:
        st.sidebar.error(
            f"Un margen objetivo de {margen}% es inalcanzable con "
            f"{pasarela + publicidad + otros:.0f}% de costos proporcionales al precio: "
            "sumados superan el 100% del PVP. Baje el margen objetivo o los costos para que "
            "el piso de rentabilidad pueda calcularse."
        )

    params = pricing.Parametros(
        pasarela_pct=pasarela,
        publicidad_pct=publicidad,
        otros_variables_pct=otros,
        envio_mxn=envio,
        material_envio_mxn=material,
        pct_envio_absorbido=absorbido,
        margen_objetivo_pct=margen,
        percentil_objetivo=percentil,
        redondeo=redondeo,
        min_comparables=int(min_comp),
        balancear_marcas=balancear,
        modo=modo,
    )
    return pagina, archivo, params, elegidos, tipo_cambio


# ------------------------------------------------------------------ contexto
class Contexto:
    """Todo lo que las páginas necesitan, cargado una sola vez."""

    def __init__(self, archivo, params, segmentos, tipo_cambio):
        self.params = params
        self.segmentos = segmentos

        self.mercado_variantes, self.mercado_productos, self.val_mercado = _mercado(
            tipo_cambio
        )
        self.encuesta, self.glosario, self.val_encuesta = _encuesta()
        self.trends, self.val_trends = _trends()
        self.region, self.val_region = _region()
        self.geojson_estados = _geojson_estados()

        if archivo is not None:
            self.internos, self.val_internos = _internos_usuario(archivo)
            self.es_demo = False
            self.nombre_archivo = archivo.name
        else:
            self.internos, self.val_internos = _internos_demo()
            self.es_demo = True
            self.nombre_archivo = None

        self.comparables = loaders.universo_comparable(self.mercado_productos)
        self.competencia = self.comparables[
            (self.comparables["Marca"] != settings.MARCA_OWFIT)
            & (self.comparables["Segmento"].isin(segmentos))
        ]
        self.owfit_publico = self.comparables[
            self.comparables["Marca"] == settings.MARCA_OWFIT
        ]

        # Encuesta: se calcula una vez y se reutiliza
        self.vw = survey.van_westendorp(self.encuesta)
        self.gg = survey.gabor_granger(self.encuesta)

        if self.val_internos.ok and not self.internos.empty:
            self.tabla = pricing.calcular_precio_recomendado(
                self.internos, self.competencia, params
            )
            self.kpis = pricing.kpis_portafolio(self.tabla, params)
        else:
            import pandas as pd

            self.tabla = pd.DataFrame()
            self.kpis = {}


# ------------------------------------------------------------------ main
def main():
    pagina, archivo, params, segmentos, tipo_cambio = barra_lateral()
    ctx = Contexto(archivo, params, segmentos, tipo_cambio)

    from views import (
        competencia,
        eda,
        encuesta,
        escenarios,
        estacionalidad,
        metodologia,
        packaging,
        precios,
        rentabilidad,
        resumen,
        simulador,
    )

    paginas = {
        "Resumen": resumen.render,
        "Pricing": precios.render,
        "Simulador": simulador.render,
        "Competencia": competencia.render,
        "Rentabilidad": rentabilidad.render,
        "Encuesta": encuesta.render,
        "EDA de mercado": eda.render,
        "Estacionalidad": estacionalidad.render,
        "Escenarios": escenarios.render,
        "Packaging": packaging.render,
        "Metodología": metodologia.render,
    }
    paginas[pagina](ctx)

    # Disclaimer de la muestra: vive UNA sola vez en todo el dashboard, como
    # pie de página, en lugar de repetirse como bullet en cada sección.
    ui.pie_muestra(len(ctx.encuesta) if ctx.encuesta is not None else 0)


if __name__ == "__main__":
    main()

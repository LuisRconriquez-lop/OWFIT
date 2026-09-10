"""
Configuración central del dashboard de pricing OWFIT México.

Todo lo que aquí aparece es un VALOR POR DEFECTO editable.
Ningún dato confidencial de OWFIT (PVP real, COGS, cantidades) vive en este archivo.
"""

from pathlib import Path

# ---------------------------------------------------------------- Rutas
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"

PATH_MERCADO = DATA_DIR / "mercado" / "OWFIT_MERCADO_LIMPIO.xlsx"
PATH_ENCUESTA = DATA_DIR / "encuesta" / "Encuestas.xlsx"
DIR_TRENDS = DATA_DIR / "google_trends"
PATH_DEMO_INTERNO = DATA_DIR / "demo" / "OWFIT_DEMO_datos_internos.xlsx"

# Export de Google Trends "Interés por subregión" (una fila por estado).
# Se busca con un patrón tolerante a acentos y sufijos en lugar de fijar el
# nombre exacto del archivo. El mismo patrón se usa para EXCLUIRLO de la carga
# de series de tiempo: no es una serie mensual y no debe entrar ahí.
PATRON_REGION = "*owfit*regi*n*"
PATH_GEOJSON_ESTADOS = DATA_DIR / "geo" / "mexico_estados.geojson"

# Umbral de lectura del índice regional (0-100): por debajo de esto se
# considera interés bajo en los KPIs del mapa.
UMBRAL_INTERES_BAJO = 20

# ---------------------------------------------------------------- Moneda
MONEDA_BASE = "MXN"
TIPO_CAMBIO_DEFAULT = {"USD": 17.00, "MXN": 1.0, "EUR": 19.80}

# ---------------------------------------------------------------- Categorías
# Categoría canónica -> variantes que pueden aparecer en cualquier archivo.
# El diccionario se usa en ambos sentidos: normaliza el mercado y los datos internos
# para que leggings se comparen contra leggings.
CATEGORIAS_CANONICAS = [
    "Leggings",
    "Tops",
    "Sports Bra",
    "Shorts",
    "Sets/Conjuntos",
    "Pants/Joggers",
    "Chamarras/Sudaderas",
    "Vestidos",
    "Faldas",
    "Accesorios/Otros",
    "Sin categorizar",
]

MAPA_CATEGORIAS = {
    "leggings": "Leggings",
    "legging": "Leggings",
    "mallas": "Leggings",
    "tops": "Tops",
    "top": "Tops",
    "blusa": "Tops",
    "blusas": "Tops",
    "playera": "Tops",
    "tank top": "Tops",
    "crop top": "Tops",
    "sports bra": "Sports Bra",
    "sport bra": "Sports Bra",
    "bra": "Sports Bra",
    "brasier deportivo": "Sports Bra",
    "shorts": "Shorts",
    "short": "Shorts",
    "biker": "Shorts",
    "sets/conjuntos": "Sets/Conjuntos",
    "sets": "Sets/Conjuntos",
    "set": "Sets/Conjuntos",
    "conjunto": "Sets/Conjuntos",
    "conjuntos": "Sets/Conjuntos",
    "pants/joggers": "Pants/Joggers",
    "pants": "Pants/Joggers",
    "pantalon": "Pants/Joggers",
    "pantalón": "Pants/Joggers",
    "joggers": "Pants/Joggers",
    "jogger": "Pants/Joggers",
    "chamarras/sudaderas": "Chamarras/Sudaderas",
    "chamarra": "Chamarras/Sudaderas",
    "chamarras": "Chamarras/Sudaderas",
    "sudadera": "Chamarras/Sudaderas",
    "sudaderas": "Chamarras/Sudaderas",
    "hoodie": "Chamarras/Sudaderas",
    "vestidos": "Vestidos",
    "vestido": "Vestidos",
    "faldas": "Faldas",
    "falda": "Faldas",
    "skort": "Faldas",
    "accesorios/otros": "Accesorios/Otros",
    "accesorios": "Accesorios/Otros",
    "otros": "Accesorios/Otros",
    "sin categorizar": "Sin categorizar",
}

# Categorías que NO son prenda y por lo tanto no entran en las comparaciones de
# precio por categoría (se reportan aparte, nunca se borran en silencio).
CATEGORIAS_NO_PRENDA = ["Accesorios/Otros", "Sin categorizar"]

# ---------------------------------------------------------------- Marcas
MARCA_OWFIT = "OWFIT"

# Segmento por defecto de cada marca. Es un supuesto editable desde la interfaz
# y desde aquí; se documenta como tal en la página de Metodología.
SEGMENTO_MARCAS = {
    "OWFIT": "OWFIT",
    "Alo Yoga": "Premium internacional",
    "Adanola": "Premium internacional",
    "Adriana Olimpo": "Mid-market MX",
    "Kleos": "Emergente MX",
    "Vyve Active Wear": "Emergente MX",
}
SEGMENTO_DESCONOCIDO = "Sin clasificar"

ORDEN_SEGMENTOS = [
    "OWFIT",
    "Premium internacional",
    "Mid-market MX",
    "Emergente MX",
    SEGMENTO_DESCONOCIDO,
]

# ---------------------------------------------------------------- Costos variables
# Valores iniciales de referencia, todos editables desde el dashboard.
COSTOS_DEFAULT = {
    "pasarela_pct": 5.0,  # % sobre PVP
    "publicidad_pct": 10.0,  # % sobre PVP
    "otros_variables_pct": 0.0,  # % sobre PVP
    "envio_mxn": 129.0,  # $ por unidad
    "material_envio_mxn": 27.0,  # $ por unidad
    "pct_envio_absorbido": 100.0,  # % de órdenes donde OWFIT paga el envío
}

# ---------------------------------------------------------------- Pricing
PERCENTILES_OBJETIVO = [50, 60, 65, 70, 75]
PERCENTIL_DEFAULT = 65
MARGEN_OBJETIVO_DEFAULT = 35.0  # % de margen de contribución objetivo
MIN_COMPARABLES = 5  # mínimo de productos competidores por categoría
REDONDEO_PSICOLOGICO_DEFAULT = "Terminación en 9"

# ---------------------------------------------------------------- Encuesta
# Columnas de Van Westendorp y de intención de compra esperadas en la encuesta.
COLS_VAN_WESTENDORP = ["Too_Cheap", "Good_Value", "Expensive", "Too_Expensive"]
PRECIOS_INTENCION = [699, 799, 899, 999, 1099]
COLS_RANKING = [
    "Ranking_Price",
    "Ranking_Quality",
    "Ranking_Comfort",
    "Ranking_Durability",
    "Ranking_Design",
]
ETIQUETAS_RANKING = {
    "Ranking_Price": "Precio",
    "Ranking_Quality": "Calidad",
    "Ranking_Comfort": "Comodidad",
    "Ranking_Durability": "Durabilidad",
    "Ranking_Design": "Diseño",
}
# La encuesta preguntó por una prenda de referencia en el rango $699–$1,099.
# Se declara explícitamente para no extrapolar la disposición a pagar a categorías
# que nunca se preguntaron (chamarras, sets, vestidos).
CATEGORIA_REFERENCIA_ENCUESTA = "Leggings"

# Umbrales del diagnóstico de clustering
CLUSTER_MIN_N = 100  # tamaño muestral mínimo razonable
CLUSTER_MIN_SILHOUETTE = 0.35  # estructura mínima aceptable

# ---------------------------------------------------------------- Estacionalidad
# Seasonal Naive es el baseline obligatorio; ETS y SARIMA deben ganarle para
# justificar su complejidad. No hay ARIMA no estacional: sin componente
# estacional converge a la media y no puede reproducir un patrón anual
# (ver comentario en src/trends.py).
MODELOS_SERIES = ["Seasonal Naive", "ETS", "SARIMA"]
BACKTEST_HOLDOUT_MESES = (
    12  # holdout estricto: últimos 12 meses reales, nunca aleatorio
)

# ---------------------------------------------------------------- Packaging
PACKAGING_DEFAULT = {
    "costo_packaging_mxn": 45.0,
    "incremento_precio_pct": 8.0,
}

# ---------------------------------------------------------------- Esquema de columnas
# Contrato de columnas del archivo interno de OWFIT.
COLUMNAS_INTERNAS_REQUERIDAS = ["Producto", "PVP", "COGS"]
COLUMNAS_INTERNAS_OPCIONALES = ["Categoría", "Cantidad"]

# ---------------------------------------------------------------- Mayoreo -> minorista
# La columna "PVP" del archivo interno de OWFIT es el precio de MAYOREO (el que
# maneja Grupo Garmac): NO es lo que paga la clienta final. El precio al
# público (minorista) es ese precio de mayoreo con este recargo.
#
# La conversión se aplica UNA sola vez, al cargar el archivo (ver
# src/loaders.py::cargar_internos): de ahí en adelante, toda columna "PVP" /
# "PVP actual" del dashboard (Simulador, Rentabilidad, Competencia, Escenarios,
# Packaging, Resumen) ya es precio minorista. Esto importa porque el precio se
# compara contra el mercado (data/mercado/), que reporta precios minoristas: si
# se comparara el precio de mayoreo directo contra esos precios, la posición
# competitiva y el precio recomendado saldrían sistemáticamente bajos.
# El valor de mayoreo original NO se descarta: se conserva en la columna
# "PVP mayorista" para las vistas que lo necesiten explícitamente (Escenarios).
RECARGO_MINORISTA_PCT = 5.0

# Alias aceptados al leer el archivo interno (tolerancia a acentos y mayúsculas).
ALIAS_COLUMNAS_INTERNAS = {
    "producto": "Producto",
    "nombre": "Producto",
    "sku": "SKU",
    "categoria": "Categoría",
    "categoría": "Categoría",
    "pvp": "PVP",
    "precio": "PVP",
    "precio de venta": "PVP",
    "cogs": "COGS",
    "costo": "COGS",
    "cantidad": "Cantidad",
    "cantidad de piezas": "Cantidad",
    "piezas": "Cantidad",
    "unidades": "Cantidad",
    "inventario": "Cantidad",
}

# ---------------------------------------------------------------- Enlaces
# Editar libremente: se muestran en la página de Metodología y recursos.
ENLACES_RECURSOS = [
    {
        "nombre": "Manual",
        "url": "https://docs.google.com/document/d/1vSYK-bge28vmIbvMQB6ZH2xmQe-rhxqr/edit?usp=sharing&ouid=109868154320364835657&rtpof=true&sd=true",
        "nota": "Cómo funciona el dashboard y cómo cambiarlo",
    },
    {
        "nombre": "Cuestionario de la encuesta",
        "url": "https://encuestaowfit.netlify.app/",
        "nota": "",
    },
    {
        "nombre": "Resultados de la encuesta",
        "url": "https://docs.google.com/spreadsheets/d/1JrLCU71Zzxpn2zWa4gk7h7Nvjolu_UT1K8ObUeKd2Ac/edit?usp=sharing",
        "nota": "",
    },
    {
        "nombre": "Propuesta de packaging",
        "url": "https://docs.google.com/document/d/17MU5QO_XMeuaPQVduyuu8PElch8j-OCfC-A8bg4bs-w/edit?usp=sharing",
        "nota": "",
    },
    {
        "nombre": "Documentación del proyecto",
        "url": "https://drive.google.com/drive/folders/1WRZQQODG028BAc6OOlMkYzka_gLcNkGU?usp=sharing",
        "nota": "",
    },
]

AVISO_DEMO = (
    "DATOS DE DEMOSTRACIÓN — NO SON DATOS REALES DE OWFIT. "
    "Cargue su archivo interno para trabajar con cifras reales."
)

# ---------------------------------------------------------------- Promociones por temporada
# Regla de activación de promociones sobre el PROXY DE DEMANDA: la serie de
# Google Trends normalizada a 0-1. El umbral separa temporada alta de temporada
# baja y NO es editable desde la interfaz: es el parámetro fijo de la
# metodología del proyecto.
#
#   I >= 0.70  ->  TEMPORADA ALTA  ->  precio regular, 0% de descuento
#   I <  0.70  ->  TEMPORADA BAJA  ->  promoción activada, descuento 15%-25%
#
# El caso de frontera exacto (I = 0.70) cuenta como temporada alta, por
# consistencia con el primer tramo de la escala de descuento.
UMBRAL_PROXY_TEMPORADA = 0.70

# Rango de descuento admitido por la metodología (%). Ningún tramo puede caer
# fuera de este rango.
RANGO_DESCUENTO_PROMO = (15.0, 25.0)

# Operacionalización del rango 15%-25%: tramos del proxy -> descuento. El corte
# superior del primer tramo ES el umbral de temporada, no un valor aparte.
ESCALA_DESCUENTO_PROMO = [
    {
        "min": 0.55,
        "max": UMBRAL_PROXY_TEMPORADA,
        "descuento_pct": 15.0,
        "accion": "Activar promoción",
    },
    {"min": 0.40, "max": 0.55, "descuento_pct": 20.0, "accion": "Activar promoción"},
    {"min": 0.00, "max": 0.40, "descuento_pct": 25.0, "accion": "Promoción agresiva"},
]

ACCION_TEMPORADA_ALTA = "Mantener precio regular"

# Cómo se lleva el índice de Google Trends (0-100) al proxy 0-1.
#
# "Mín–máx del histórico" es el default porque Google re-escala cada consulta:
# en un mismo export, el término más buscado marca 100 y los demás quedan
# comprimidos abajo (en los datos de OWFIT, "leggings" llega a 100 mientras
# "Yoga pants" nunca pasa de 11). Dividir entre 100 dejaría a esos términos
# permanentemente por debajo de 0.70 y la regla de temporada perdería sentido.
# La opción cruda se conserva para quien quiera leer la escala de Google tal
# cual, y la elección se declara en pantalla.
METODO_NORMALIZACION_MINMAX = "Mín–máx del histórico"
METODO_NORMALIZACION_CRUDO = "Índice Google / 100"
METODOS_NORMALIZACION_PROXY = [METODO_NORMALIZACION_MINMAX, METODO_NORMALIZACION_CRUDO]

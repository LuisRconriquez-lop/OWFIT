"""Carga de las cuatro fuentes del proyecto.

Reglas que se respetan en todo el módulo:
  * No se eliminan filas con NA.
  * NA nunca se convierte en cero.
  * Las exclusiones (accesorios, precios no válidos) se marcan con banderas
    booleanas para poder contarlas y explicarlas, nunca se borran.
  * Ningún dato interno de OWFIT se escribe en el código.
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import numpy as np
import pandas as pd

from config import settings
from src import validation
from src.utils import normalizar_categoria, segmento_de_marca, slug


# =================================================================== MERCADO
def cargar_mercado(
    ruta: str | Path | io.BytesIO = None,
    tipo_cambio: dict | None = None,
) -> tuple[pd.DataFrame, validation.ResultadoValidacion]:
    """Lee el Excel de mercado. Cada hoja es una marca.

    Devuelve el detalle a nivel VARIANTE con columnas añadidas:
      Marca, Segmento, Categoria_norm, Precio_MXN, es_prenda, precio_valido
    """
    ruta = ruta or settings.PATH_MERCADO
    tipo_cambio = tipo_cambio or settings.TIPO_CAMBIO_DEFAULT

    xl = pd.ExcelFile(ruta)
    marcos = []
    for hoja in xl.sheet_names:
        d = xl.parse(hoja)
        d["Marca"] = hoja
        marcos.append(d)
    df = pd.concat(marcos, ignore_index=True)

    if "Moneda" not in df.columns:
        df["Moneda"] = settings.MONEDA_BASE
    df["Moneda"] = df["Moneda"].fillna(settings.MONEDA_BASE)

    res = validation.validar_mercado(df)
    if not res.ok:
        return df, res

    df["Precio"] = pd.to_numeric(df["Precio"], errors="coerce")
    df["Categoria_norm"] = df["Categoría"].map(normalizar_categoria)
    df["Segmento"] = df["Marca"].map(segmento_de_marca)

    fx = df["Moneda"].map(lambda m: tipo_cambio.get(str(m).upper(), np.nan))
    sin_fx = fx.isna() & df["Moneda"].notna()
    if sin_fx.any():
        monedas = sorted(df.loc[sin_fx, "Moneda"].unique())
        res.aviso(
            "Sin tipo de cambio para: "
            + ", ".join(map(str, monedas))
            + ". Esos precios quedan como faltantes."
        )
    df["Precio_MXN"] = df["Precio"] * fx

    df["es_prenda"] = ~df["Categoria_norm"].isin(settings.CATEGORIAS_NO_PRENDA)
    df["precio_valido"] = df["Precio_MXN"].notna() & (df["Precio_MXN"] > 0)

    if "Disponible" in df.columns:
        df["Agotado"] = df["Disponible"].map(
            lambda v: (
                True
                if slug(v) in {"agotado", "no", "sin stock"}
                else (False if pd.notna(v) else np.nan)
            )
        )
    else:
        df["Agotado"] = np.nan
        res.nota("La base no incluye 'Disponible': no se analiza disponibilidad.")

    n_no_prenda = int((~df["es_prenda"]).sum())
    n_precio_cero = int((df["Precio_MXN"].fillna(-1) <= 0).sum())
    res.nota(
        f"{len(df):,} filas de variante leídas. {n_no_prenda:,} pertenecen a accesorios o a "
        "productos sin categorizar y se marcan (no se borran) para excluirlos de las "
        f"comparaciones por categoría. {n_precio_cero:,} registros tienen precio 0 o faltante "
        "(regalos, promociones o campos vacíos) y se marcan como precio no válido."
    )
    return df, res


def agregar_a_producto(df_variantes: pd.DataFrame) -> pd.DataFrame:
    """Colapsa variantes a producto para que las marcas con muchas tallas no
    dominen la distribución de precios.

    n_variantes = número de SKU/tallas/colores de ese producto.
    """
    g = df_variantes.groupby(
        ["Marca", "Segmento", "Producto", "Categoria_norm"], dropna=False, observed=True
    )
    out = g.agg(
        Precio_MXN=("Precio_MXN", "median"),
        Precio_min=("Precio_MXN", "min"),
        Precio_max=("Precio_MXN", "max"),
        n_variantes=("Precio_MXN", "size"),
        n_agotadas=("Agotado", "sum"),
        variantes_con_dato_stock=("Agotado", "count"),
        Moneda=("Moneda", "first"),
    ).reset_index()

    out["pct_agotado"] = np.where(
        out["variantes_con_dato_stock"] > 0,
        100 * out["n_agotadas"] / out["variantes_con_dato_stock"],
        np.nan,
    )
    out["es_prenda"] = ~out["Categoria_norm"].isin(settings.CATEGORIAS_NO_PRENDA)
    out["precio_valido"] = out["Precio_MXN"].notna() & (out["Precio_MXN"] > 0)
    return out


def universo_comparable(
    df_productos: pd.DataFrame, incluir_no_prenda: bool = False
) -> pd.DataFrame:
    """Subconjunto usable para comparar precios: prenda + precio válido."""
    m = df_productos["precio_valido"]
    if not incluir_no_prenda:
        m = m & df_productos["es_prenda"]
    return df_productos[m].copy()


# =================================================================== ENCUESTA
def cargar_encuesta(
    ruta: str | Path | io.BytesIO = None,
) -> tuple[pd.DataFrame, pd.DataFrame, validation.ResultadoValidacion]:
    """Devuelve (respuestas, glosario, validación)."""
    ruta = ruta or settings.PATH_ENCUESTA
    xl = pd.ExcelFile(ruta)

    hoja_resp = next(
        (h for h in xl.sheet_names if slug(h).startswith("respuesta")),
        xl.sheet_names[-1],
    )
    df = xl.parse(hoja_resp)
    df = df.loc[:, [c for c in df.columns if not str(c).startswith("Unnamed")]]
    df = df.dropna(axis=0, how="all")

    glosario = pd.DataFrame()
    hoja_glo = next((h for h in xl.sheet_names if slug(h).startswith("glosario")), None)
    if hoja_glo:
        glosario = xl.parse(hoja_glo)
        # Las columnas de ejemplo mezclan texto y números; se uniforman a texto
        # para que la tabla pueda mostrarse sin conversiones automáticas.
        for c in glosario.columns:
            if glosario[c].dtype == object:
                glosario[c] = glosario[c].astype(str).replace({"nan": ""})

    for c in settings.COLS_VAN_WESTENDORP + settings.COLS_RANKING:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    for p in settings.PRECIOS_INTENCION:
        c = f"Purchase_Intention_{p}"
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    if "Packaging_Importance" in df.columns:
        df["Packaging_Importance"] = pd.to_numeric(
            df["Packaging_Importance"], errors="coerce"
        )

    res = validation.validar_encuesta(df)
    return df, glosario, res


# =============================================================== GOOGLE TRENDS
def _leer_trends_archivo(origen, nombre: str) -> pd.DataFrame:
    """Lee un archivo de Google Trends (CSV o Excel) en formato ancho.

    Tolera el encabezado de exportación de Google ('Categoría: Todas...'),
    columnas vacías y valores '<1'.
    """
    if hasattr(origen, "read"):
        contenido = origen.read()
        buffer = io.BytesIO(contenido)
    else:
        buffer = None

    if str(nombre).lower().endswith((".xlsx", ".xls")):
        df = pd.read_excel(buffer or origen)
    else:
        crudo = (buffer or open(origen, "rb")).read()
        texto = (
            crudo.decode("utf-8-sig", errors="replace")
            if isinstance(crudo, bytes)
            else crudo
        )
        lineas = texto.splitlines()
        salto = 0
        for i, linea in enumerate(lineas[:5]):
            if linea.count(",") >= 1 and not slug(linea).startswith("categoria"):
                salto = i
                break
        df = pd.read_csv(io.StringIO("\n".join(lineas[salto:])))

    df = df.loc[:, [c for c in df.columns if not str(c).startswith("Unnamed")]]
    df = df.dropna(axis=1, how="all")

    col_tiempo = df.columns[0]
    fechas = pd.to_datetime(df[col_tiempo], format="%d/%m/%Y", errors="coerce")
    if fechas.isna().mean() > 0.5:
        fechas = pd.to_datetime(df[col_tiempo], errors="coerce", format="mixed")
    df = df.assign(_fecha=fechas).dropna(subset=["_fecha"]).set_index("_fecha")
    df = df.drop(columns=[col_tiempo])

    for c in df.columns:
        df[c] = pd.to_numeric(
            df[c]
            .astype(str)
            .str.replace("<1", "0.5", regex=False)
            .str.replace("%", "", regex=False),
            errors="coerce",
        )
    df.index.name = "Fecha"
    df.columns = [str(c).strip() for c in df.columns]
    return df


def cargar_trends(
    rutas: list | None = None,
) -> tuple[pd.DataFrame, validation.ResultadoValidacion]:
    """Combina 1..N archivos de Google Trends en una sola base mensual.

    Los términos con el mismo nombre en dos archivos se promedian y se avisa,
    porque el índice de Google se re-escala por consulta y no es directamente
    comparable entre exportaciones distintas.
    """
    res = validation.ResultadoValidacion()

    if rutas is None:
        # El export por subregión vive en la misma carpeta pero NO es una serie
        # mensual: su primera columna son estados, no fechas. Si entra aquí, sus
        # columnas se leen como términos repetidos y disparan un aviso falso de
        # "términos repetidos entre archivos". Se excluye por patrón.
        region = {p.name for p in settings.DIR_TRENDS.glob(settings.PATRON_REGION)}
        rutas = sorted(
            [
                p
                for p in settings.DIR_TRENDS.glob("*")
                if p.suffix.lower() in {".csv", ".xlsx", ".xls"}
                and p.name not in region
            ]
        )
    if not rutas:
        res.error(
            "No se encontró ningún archivo de Google Trends en data/google_trends/."
        )
        return pd.DataFrame(), res

    marcos, origenes = [], []
    for r in rutas:
        nombre = getattr(r, "name", str(r))
        try:
            d = _leer_trends_archivo(r, nombre)
            marcos.append(d)
            origenes.append(Path(nombre).name)
        except Exception as e:  # noqa: BLE001
            res.aviso(f"No se pudo leer '{nombre}': {e}")

    if not marcos:
        res.error("Ningún archivo de Google Trends pudo interpretarse.")
        return pd.DataFrame(), res

    combinado = pd.concat(marcos, axis=1)
    duplicados = combinado.columns[combinado.columns.duplicated()].unique().tolist()
    if duplicados:
        combinado = combinado.T.groupby(level=0).mean().T
        res.aviso(
            "Términos repetidos entre archivos, se promediaron: "
            + ", ".join(duplicados)
            + ". Recuerde que el índice de Google se re-escala en cada consulta."
        )

    combinado = combinado.sort_index()
    try:
        combinado = combinado.asfreq("MS")
    except ValueError:
        res.aviso(
            "Las fechas no son mensuales exactas; se usa el índice tal cual se leyó."
        )

    res.nota(
        f"{len(origenes)} archivo(s) combinado(s): {', '.join(origenes)}. "
        f"{combinado.shape[1]} término(s), {len(combinado)} meses "
        f"({combinado.index.min():%b %Y} a {combinado.index.max():%b %Y})."
    )
    res = res + validation.validar_trends(combinado)
    return combinado, res


# ========================================================= REGIÓN (subregión)
# Estados que NO empatan solo con normalizar (minúsculas, sin acentos ni
# puntuación). Google Trends exporta los nombres en inglés; los archivos
# oficiales usan los nombres largos. El valor es el nombre tal como aparece en
# el GeoJSON, que es la llave del join.
ALIAS_ESTADOS = {
    "mexico city": "Ciudad de México",
    "ciudad de mexico": "Ciudad de México",
    "distrito federal": "Ciudad de México",
    "cdmx": "Ciudad de México",
    "df": "Ciudad de México",
    "state of mexico": "México",
    "estado de mexico": "México",
    "edomex": "México",
    "michoacan de ocampo": "Michoacán",
    "veracruz de ignacio de la llave": "Veracruz",
    "coahuila de zaragoza": "Coahuila",
    "queretaro de arteaga": "Querétaro",
}


def cargar_geojson_estados(ruta: str | Path | None = None) -> dict:
    """GeoJSON de los 32 estados. Se lee del disco: no depende de la red."""
    ruta = Path(ruta or settings.PATH_GEOJSON_ESTADOS)
    if not ruta.exists():
        return {}
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def _saltar_preambulo(lineas: list[str]) -> int:
    """Índice de la fila de encabezado real de un export de Google Trends.

    Los exports traen 1-3 filas de preámbulo ('Categoría: Todas...', líneas en
    blanco) antes del encabezado. El encabezado es la primera línea que ya tiene
    tantas comas como las filas de datos, que son la mayoría del archivo.
    """
    con_datos = [l for l in lineas if l.strip()]
    if not con_datos:
        return 0
    referencia = pd.Series([l.count(",") for l in con_datos[-10:]]).mode()
    esperado = int(referencia.iloc[0]) if not referencia.empty else 0
    for i, linea in enumerate(lineas):
        if linea.strip() and linea.count(",") == esperado:
            return i
    return 0


def cargar_region(
    ruta: str | Path | None = None,
) -> tuple[pd.DataFrame, validation.ResultadoValidacion]:
    """Lee el export 'Interés por subregión' y lo empata contra el GeoJSON.

    Devuelve un DataFrame con la columna 'Estado' (nombre canónico del GeoJSON)
    y una columna numérica 0-100 por término de búsqueda. Los valores vacíos y
    '<1' se leen como 0, tal como los reporta Google.
    """
    res = validation.ResultadoValidacion()

    if ruta is None:
        candidatos = sorted(settings.DATA_DIR.rglob(settings.PATRON_REGION + ".csv"))
        if not candidatos:
            candidatos = sorted(
                settings.DATA_DIR.rglob(settings.PATRON_REGION + ".xlsx")
            )
        if not candidatos:
            res.nota(
                "No se encontró el export por subregión de Google Trends "
                f"(patrón '{settings.PATRON_REGION}') en data/."
            )
            return pd.DataFrame(), res
        ruta = candidatos[0]

    ruta = Path(ruta)
    if ruta.suffix.lower() in {".xlsx", ".xls"}:
        df = pd.read_excel(ruta)
    else:
        texto = ruta.read_bytes().decode("utf-8-sig", errors="replace")
        lineas = texto.splitlines()
        df = pd.read_csv(io.StringIO("\n".join(lineas[_saltar_preambulo(lineas) :])))

    df = df.loc[:, [c for c in df.columns if not str(c).startswith("Unnamed")]]
    df = df.dropna(axis=1, how="all").dropna(axis=0, how="all")
    if df.shape[1] < 2:
        res.error(f"El archivo de región '{ruta.name}' no tiene columnas de término.")
        return pd.DataFrame(), res

    col_estado = df.columns[0]
    # Google agrega el ámbito al nombre del término ("leggings: (México)").
    df.columns = [str(c).split(":")[0].strip() for c in df.columns]
    col_estado = str(col_estado).split(":")[0].strip()

    for c in df.columns:
        if c == col_estado:
            continue
        df[c] = pd.to_numeric(
            df[c]
            .astype(str)
            .str.replace("<1", "0", regex=False)
            .str.replace("%", "", regex=False)
            .str.strip()
            .replace({"": "0", "nan": "0"}),
            errors="coerce",
        ).fillna(0)

    geo = cargar_geojson_estados()
    if not geo:
        res.error(
            f"Falta el GeoJSON de estados en {settings.PATH_GEOJSON_ESTADOS}. "
            "El mapa no se puede dibujar."
        )
        return pd.DataFrame(), res

    indice_geo = {
        slug(f["properties"]["name"]): f["properties"]["name"] for f in geo["features"]
    }

    def _canonico(nombre) -> str | None:
        clave = slug(nombre)
        if clave in ALIAS_ESTADOS:
            return ALIAS_ESTADOS[clave]
        return indice_geo.get(clave)

    df = df.rename(columns={col_estado: "Estado"})
    df["Estado"] = df["Estado"].map(_canonico).fillna(df["Estado"])

    sin_match = sorted(set(df["Estado"]) - set(indice_geo.values()))
    if sin_match:
        # Consola: el usuario debe poder ver qué estado se quedó sin geometría
        # antes de que el mapa lo pinte en gris.
        print(
            "[región] Estados sin match contra el GeoJSON:",
            ", ".join(map(str, sin_match)),
        )
        res.aviso(
            "Estados sin correspondencia en el GeoJSON (quedarían sin color): "
            + ", ".join(map(str, sin_match))
        )

    faltan_geo = sorted(set(indice_geo.values()) - set(df["Estado"]))
    if faltan_geo:
        res.nota(
            f"{len(faltan_geo)} estado(s) del GeoJSON sin dato en el export: "
            + ", ".join(faltan_geo)
        )

    res.nota(
        f"Interés por subregión leído de '{ruta.name}': {len(df)} estados, "
        f"{df.shape[1] - 1} término(s)."
    )
    return df.reset_index(drop=True), res


# ============================================================ DATOS INTERNOS
def cargar_internos(
    origen=None,
    es_demo: bool = True,
) -> tuple[pd.DataFrame, validation.ResultadoValidacion]:
    """Lee el archivo interno de OWFIT (o el archivo demo ficticio).

    `origen` puede ser un UploadedFile de Streamlit o una ruta.
    """
    origen = origen or settings.PATH_DEMO_INTERNO
    nombre = getattr(origen, "name", str(origen))

    if str(nombre).lower().endswith(".csv"):
        df = pd.read_csv(origen)
    else:
        xl = pd.ExcelFile(origen)
        hoja = next(
            (
                h
                for h in xl.sheet_names
                if not slug(h).startswith(("leeme", "readme", "aviso"))
            ),
            xl.sheet_names[0],
        )
        df = xl.parse(hoja)

    df = df.loc[:, [c for c in df.columns if not str(c).startswith("Unnamed")]]
    df = df.dropna(axis=0, how="all")
    df = validation.renombrar_por_alias(df, settings.ALIAS_COLUMNAS_INTERNAS)

    res = validation.validar_internos(df)
    if not res.ok:
        return df, res

    for c in ["PVP", "COGS", "Cantidad"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    if "PVP" in df.columns:
        # El archivo trae precio de MAYOREO, no el precio al público. Se
        # conserva el original tal cual (columna aparte) y "PVP" pasa a ser el
        # minorista de aquí en adelante, para que ninguna vista aguas abajo
        # tenga que acordarse de convertirlo. Ver settings.RECARGO_MINORISTA_PCT.
        df["PVP mayorista"] = df["PVP"]
        df["PVP"] = df["PVP"] * (1 + settings.RECARGO_MINORISTA_PCT / 100)

    if "Categoría" in df.columns:
        df["Categoria_norm"] = df["Categoría"].map(normalizar_categoria)
    else:
        df["Categoria_norm"] = df["Producto"].map(normalizar_categoria)

    df["es_demo"] = bool(es_demo)
    return df, res

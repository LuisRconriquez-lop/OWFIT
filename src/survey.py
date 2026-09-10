"""Análisis de la encuesta de consumidor.

Incluye:
  * Descriptivos de importancia de atributos (rankings ipsativos).
  * Van Westendorp: rango de precios aceptable y punto óptimo.
  * Gabor-Granger: curva de intención de compra e ingreso esperado relativo.
  * Diagnóstico de segmentación: decide si el clustering está justificado
    ANTES de mostrar cualquier segmento.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from config import settings


# ------------------------------------------------------------------ atributos
def importancia_atributos(df: pd.DataFrame) -> pd.DataFrame:
    """Rankings 1 = más importante. Se reporta el promedio y el % de primeros lugares."""
    cols = [c for c in settings.COLS_RANKING if c in df.columns]
    if not cols:
        return pd.DataFrame()
    filas = []
    for c in cols:
        s = df[c].dropna()
        if s.empty:
            continue
        filas.append(
            {
                "Atributo": settings.ETIQUETAS_RANKING.get(c, c),
                "Posición promedio": float(s.mean()),
                "Mediana": float(s.median()),
                "% en 1er lugar": float((s == 1).mean() * 100),
                "% en top 2": float((s <= 2).mean() * 100),
                "% en último lugar": float((s == s.max()).mean() * 100),
                "n": int(s.size),
            }
        )
    return pd.DataFrame(filas).sort_values("Posición promedio")


def distribucion_categorica(
    df: pd.DataFrame, columna: str, separador: str | None = None
) -> pd.DataFrame:
    """Frecuencias de una variable categórica. `separador` para respuestas múltiples."""
    if columna not in df.columns:
        return pd.DataFrame()
    s = df[columna].dropna().astype(str)
    if separador:
        s = s.str.split(separador).explode().str.strip()
        s = s[s != ""]
    conteo = s.value_counts()
    base = len(df) if separador else int(s.size)
    return pd.DataFrame(
        {
            "Respuesta": conteo.index,
            "n": conteo.values,
            "%": (conteo.values / base * 100).round(1),
        }
    )


# ------------------------------------------------------------ Van Westendorp
def van_westendorp(df: pd.DataFrame, paso: int = 10) -> dict:
    """Curvas acumuladas y puntos de corte de Van Westendorp.

    Devuelve dict con la malla de precios, las cuatro curvas y los puntos
    PMC, PME, IPP y OPP. Solo usa respuestas internamente consistentes
    (too cheap <= good value <= expensive <= too expensive) y reporta cuántas
    se descartaron por inconsistencia.
    """
    cols = settings.COLS_VAN_WESTENDORP
    if any(c not in df.columns for c in cols):
        return {
            "disponible": False,
            "motivo": "Faltan una o más preguntas de Van Westendorp.",
        }

    v = df[cols].dropna()
    n_total = int(len(v))
    if n_total == 0:
        return {
            "disponible": False,
            "motivo": "No hay respuestas completas de Van Westendorp.",
        }

    consistente = (
        (v["Too_Cheap"] <= v["Good_Value"])
        & (v["Good_Value"] <= v["Expensive"])
        & (v["Expensive"] <= v["Too_Expensive"])
    )
    v = v[consistente]
    n_valido = int(len(v))
    if n_valido < 10:
        return {
            "disponible": False,
            "motivo": f"Solo {n_valido} respuestas consistentes; insuficientes para trazar curvas.",
            "n_total": n_total,
            "n_valido": n_valido,
        }

    tope = float(np.nanpercentile(v["Too_Expensive"], 97))
    malla = np.arange(0, max(tope, 100) + paso, paso)

    muy_barato = np.array([(v["Too_Cheap"] >= p).mean() for p in malla])  # decreciente
    barato = np.array([(v["Good_Value"] >= p).mean() for p in malla])  # decreciente
    caro = np.array([(v["Expensive"] <= p).mean() for p in malla])  # creciente
    muy_caro = np.array([(v["Too_Expensive"] <= p).mean() for p in malla])  # creciente

    def cruce(a, b):
        i = int(np.argmin(np.abs(a - b)))
        return float(malla[i])

    puntos = {
        "PMC": cruce(muy_barato, 1 - barato),  # marginal cheapness
        "PME": cruce(muy_caro, 1 - caro),  # marginal expensiveness
        "IPP": cruce(barato, caro),  # indiferencia
        "OPP": cruce(muy_barato, muy_caro),  # óptimo
    }

    return {
        "disponible": True,
        "malla": malla,
        "curvas": {
            "Demasiado barato": muy_barato * 100,
            "Barato / buena relación": barato * 100,
            "Caro": caro * 100,
            "Demasiado caro": muy_caro * 100,
        },
        "puntos": puntos,
        "n_total": n_total,
        "n_valido": n_valido,
        "descartadas": n_total - n_valido,
        "mediana_good_value": float(v["Good_Value"].median()),
        "mediana_expensive": float(v["Expensive"].median()),
    }


# -------------------------------------------------------------- Gabor-Granger
def gabor_granger(df: pd.DataFrame, umbral_top: int = 4) -> pd.DataFrame:
    """Intención de compra por punto de precio.

    top_box = % que responde >= umbral_top en la escala Likert 1-5.
    ingreso_relativo = precio x top_box, útil para ver dónde se maximiza el
    ingreso esperado dentro del rango preguntado (NO es un pronóstico de ventas).
    """
    filas = []
    for p in settings.PRECIOS_INTENCION:
        c = f"Purchase_Intention_{p}"
        if c not in df.columns:
            continue
        s = df[c].dropna()
        if s.empty:
            continue
        top = float((s >= umbral_top).mean())
        filas.append(
            {
                "Precio": p,
                "Intención promedio (1-5)": float(s.mean()),
                "% top-2-box": top * 100,
                "% que respondería 3 o más": float((s >= 3).mean() * 100),
                "Ingreso relativo": p * top,
                "n": int(s.size),
            }
        )
    if not filas:
        return pd.DataFrame()
    out = pd.DataFrame(filas)
    if out["Ingreso relativo"].max() > 0:
        out["Ingreso relativo (índice)"] = (
            100 * out["Ingreso relativo"] / out["Ingreso relativo"].max()
        )
    return out


def elasticidad_aparente(gg: pd.DataFrame) -> float | None:
    """Elasticidad log-log de la intención top-box respecto al precio.

    Es una elasticidad declarada, no de comportamiento real de compra.
    """
    if gg.empty or "% top-2-box" not in gg.columns:
        return None
    d = gg[(gg["% top-2-box"] > 0)]
    if len(d) < 3:
        return None
    x = np.log(d["Precio"].to_numpy(dtype=float))
    y = np.log(d["% top-2-box"].to_numpy(dtype=float))
    pendiente = float(np.polyfit(x, y, 1)[0])
    return pendiente


# ------------------------------------------------------- diagnóstico clustering
def diagnostico_clustering(df: pd.DataFrame, k_max: int = 4) -> dict:
    """Evalúa si segmentar a los consumidores es metodológicamente defendible.

    Criterios, todos verificables y reportados:
      1. Tamaño muestral suficiente (n >= CLUSTER_MIN_N).
      2. Variables no ipsativas: si los rankings suman una constante, la matriz
         está restringida y las distancias euclidianas son artificiales.
      3. Estructura real: silueta máxima >= CLUSTER_MIN_SILHOUETTE.
      4. Tamaño mínimo de grupo >= 10% de la muestra.

    Se ejecuta el k-means solo para MEDIR, no para presentar segmentos:
    los perfiles se devuelven únicamente si los cuatro criterios se cumplen.
    """
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score
    from sklearn.preprocessing import StandardScaler

    cols_rank = [c for c in settings.COLS_RANKING if c in df.columns]
    extra = [
        c
        for c in ["Packaging_Importance", "Good_Value", "Too_Expensive"]
        if c in df.columns
    ]
    variables = cols_rank + extra

    resultado = {
        "n": int(len(df)),
        "variables_usadas": variables,
        "criterios": [],
        "justificado": False,
        "scores": pd.DataFrame(),
        "perfiles": pd.DataFrame(),
    }

    if len(variables) < 3:
        resultado["criterios"].append(
            {
                "criterio": "Variables suficientes",
                "cumple": False,
                "detalle": f"Solo {len(variables)} variable(s) numérica(s) utilizable(s).",
            }
        )
        resultado["motivo"] = "No hay suficientes variables numéricas para segmentar."
        return resultado

    X = df[variables].dropna()
    resultado["n_completo"] = int(len(X))

    # Criterio 1: tamaño muestral
    ok_n = len(X) >= settings.CLUSTER_MIN_N
    resultado["criterios"].append(
        {
            "criterio": "Tamaño muestral",
            "cumple": ok_n,
            "detalle": f"n = {len(X)} respuestas completas; el mínimo razonable para "
            f"segmentar es {settings.CLUSTER_MIN_N}. Con muestras pequeñas cada "
            "grupo queda con muy pocos casos y el resultado no es estable.",
        }
    )

    # Criterio 2: rankings ipsativos
    ipsativo = False
    if len(cols_rank) >= 3:
        sumas = df[cols_rank].sum(axis=1).dropna().unique()
        ipsativo = len(sumas) == 1
    resultado["criterios"].append(
        {
            "criterio": "Variables no ipsativas",
            "cumple": not ipsativo,
            "detalle": (
                "Los rankings de atributos suman siempre la misma constante (dato ipsativo): "
                "subir un atributo obliga a bajar otro, así que las distancias euclidianas "
                "reflejan la restricción del formato, no diferencias reales entre personas."
                if ipsativo
                else "Las variables no están sujetas a una restricción de suma constante."
            ),
        }
    )

    # Criterio 3 y 4: estructura
    Z = StandardScaler().fit_transform(X)
    filas, mejor_sil, mejor_k, etiquetas_mejor = [], -1.0, None, None
    for k in range(2, min(k_max, max(2, len(X) - 1)) + 1):
        km = KMeans(n_clusters=k, n_init=25, random_state=42)
        lab = km.fit_predict(Z)
        if len(set(lab)) < 2:
            continue
        sil = float(silhouette_score(Z, lab))
        tam = np.bincount(lab)
        filas.append(
            {
                "k": k,
                "Silueta": sil,
                "Inercia": float(km.inertia_),
                "Grupo más pequeño": int(tam.min()),
                "% del grupo más pequeño": float(100 * tam.min() / len(X)),
            }
        )
        if sil > mejor_sil:
            mejor_sil, mejor_k, etiquetas_mejor = sil, k, lab

    resultado["scores"] = pd.DataFrame(filas)
    resultado["mejor_k"] = mejor_k
    resultado["mejor_silueta"] = mejor_sil

    ok_sil = mejor_sil >= settings.CLUSTER_MIN_SILHOUETTE
    resultado["criterios"].append(
        {
            "criterio": "Estructura de grupos",
            "cumple": ok_sil,
            "detalle": f"Silueta máxima = {mejor_sil:.3f} (k = {mejor_k}). Se pide al menos "
            f"{settings.CLUSTER_MIN_SILHOUETTE}. Por debajo de ese valor los grupos "
            "se traslapan y la partición es un corte arbitrario de una nube continua.",
        }
    )

    ok_tam = False
    if etiquetas_mejor is not None:
        tam = np.bincount(etiquetas_mejor)
        ok_tam = (tam.min() / len(X)) >= 0.10
        resultado["criterios"].append(
            {
                "criterio": "Grupos con tamaño accionable",
                "cumple": ok_tam,
                "detalle": f"El grupo más pequeño tiene {int(tam.min())} personas "
                f"({100 * tam.min() / len(X):.0f}% de la muestra).",
            }
        )

    resultado["justificado"] = bool(ok_n and (not ipsativo) and ok_sil and ok_tam)

    if resultado["justificado"] and etiquetas_mejor is not None:
        perfil = X.copy()
        perfil["Segmento"] = [f"Segmento {i + 1}" for i in etiquetas_mejor]
        resultado["perfiles"] = (
            perfil.groupby("Segmento").agg(["mean", "size"]).round(2)
        )
    else:
        fallidos = [c["criterio"] for c in resultado["criterios"] if not c["cumple"]]
        resultado["motivo"] = (
            "No se presenta segmentación porque no se cumplen estos criterios: "
            + ", ".join(fallidos)
            + ". Forzar clusters aquí produciría perfiles que cambian con la semilla "
            "aleatoria y que no describen grupos reales de clientes."
        )
    return resultado


# ---------------------------------------------------------------- techo de WTP
def techo_disposicion_pagar(
    vw: dict, gg: pd.DataFrame, criterio: str = "PME"
) -> float | None:
    """Precio de referencia máximo sugerido por la encuesta.

    criterio:
      'PME'         -> punto de marginal expensiveness de Van Westendorp
      'OPP'         -> punto óptimo de Van Westendorp
      'Ingreso máx' -> precio con mayor ingreso relativo en Gabor-Granger
    """
    if criterio in {"PME", "OPP"} and vw.get("disponible"):
        return float(vw["puntos"][criterio])
    if criterio == "Ingreso máx" and not gg.empty:
        return float(gg.loc[gg["Ingreso relativo"].idxmax(), "Precio"])
    return None

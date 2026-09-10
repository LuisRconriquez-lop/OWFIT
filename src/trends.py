"""Estacionalidad del interés de búsqueda (Google Trends).

Las series son ÍNDICE DE INTERÉS DE BÚSQUEDA (0-100, re-escalado por Google
en cada consulta). No son ventas, ni unidades, ni participación de mercado.
Los ceros son valores reales (volumen bajo el umbral de reporte de Google),
nunca se imputan ni se tratan como faltantes.

La selección de modelo se valida con un holdout estrictamente temporal: se
entrena con todo menos los últimos `holdout_meses` y se evalúa contra esos
meses reales. Nunca aleatorio, nunca con folds que exceden los datos
disponibles (ver `backtesting`).
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")


# ------------------------------------------------------------------ descriptivo
def perfil_mensual(serie: pd.Series) -> pd.DataFrame:
    """Índice estacional por mes: promedio del mes / promedio general x 100."""
    s = serie.dropna()
    if s.empty:
        return pd.DataFrame()
    d = pd.DataFrame({"valor": s.values}, index=s.index)
    d["mes"] = d.index.month
    base = d["valor"].mean()
    out = (
        d.groupby("mes")["valor"].agg(["mean", "median", "std", "count"]).reset_index()
    )
    out["Índice estacional"] = 100 * out["mean"] / base if base else np.nan
    nombres = [
        "Ene",
        "Feb",
        "Mar",
        "Abr",
        "May",
        "Jun",
        "Jul",
        "Ago",
        "Sep",
        "Oct",
        "Nov",
        "Dic",
    ]
    out["Mes"] = out["mes"].map(lambda m: nombres[m - 1])
    return out[["Mes", "mes", "mean", "median", "std", "count", "Índice estacional"]]


def descomposicion(serie: pd.Series, modelo: str = "additive"):
    from statsmodels.tsa.seasonal import seasonal_decompose

    s = serie.dropna()
    if len(s) < 24:
        return None
    return seasonal_decompose(s, model=modelo, period=12, extrapolate_trend="freq")


def tendencia_anual(serie: pd.Series) -> pd.DataFrame:
    s = serie.dropna()
    if s.empty:
        return pd.DataFrame()
    d = pd.DataFrame({"valor": s.values}, index=s.index)
    d["año"] = d.index.year
    out = d.groupby("año")["valor"].agg(["mean", "min", "max", "count"]).reset_index()
    out["Cambio % vs año previo"] = out["mean"].pct_change() * 100
    return out


def fuerza_estacional(serie: pd.Series) -> float | None:
    """Fuerza de la estacionalidad: 1 - Var(residuo)/Var(residuo+estacional).

    Valores cercanos a 1 indican estacionalidad marcada; cercanos a 0, ausente.
    """
    desc = descomposicion(serie)
    if desc is None:
        return None
    resid = pd.Series(desc.resid).dropna()
    seas = pd.Series(desc.seasonal).reindex(resid.index)
    denom = float(np.var(resid + seas))
    if denom == 0:
        return None
    return float(max(0.0, 1 - np.var(resid) / denom))


# ------------------------------------------------------------------ modelos
#
# Por qué NO hay un ARIMA no estacional en el comparador
# -------------------------------------------------------
# Sin componente estacional, los términos AR/MA de un ARIMA solo "recuerdan"
# 1-2 meses hacia atrás; pasados esos pasos el pronóstico converge a la media
# de la serie y se queda plano. Verificado en la serie de leggings: un
# ARIMA(1,1,1) varía apenas 0.3 puntos de índice en un horizonte de 12 meses,
# mientras que un SARIMA con componente estacional varía 16.4 puntos. Un
# pronóstico plano no sirve para responder la pregunta del proyecto (en qué
# mes conviene concentrar marketing), así que el ARIMA no estacional se
# elimina del comparador y se sustituye por Seasonal Naive como baseline
# obligatorio (ver `_seasonal_naive`).
#
# Por qué el error (MAE/RMSE/MAPE) por sí solo no basta para elegir ganador
# --------------------------------------------------------------------------
# Esas métricas premian no equivocarse de MAGNITUD, no premian acertar la
# FORMA del año. Un modelo que siempre pronostica la media nunca se arriesga,
# y en series ruidosas eso le basta para ganarle en RMSE a un modelo bien
# ajustado que sí sigue el ciclo anual, incluso con correlación 0.00 contra la
# forma real (visto en la práctica al comparar contra ETS). Por eso
# `seleccionar_modelo` primero descarta cualquier modelo cuyo pronóstico sea
# esencialmente plano (poco rango, poca correlación con la forma real) y solo
# entre los que sobreviven decide por RMSE — ver la regla completa en el
# docstring de esa función.

SIMPLICIDAD = {"Seasonal Naive": 0, "ETS": 1, "SARIMA": 2}


def _seasonal_naive(train: pd.Series, h: int) -> np.ndarray:
    """y(t) = y(t-12). Baseline obligatorio: cualquier modelo debe ganarle."""
    if len(train) < 12:
        return np.repeat(float(train.iloc[-1]), h)
    ultimo_ciclo = train.iloc[-12:].to_numpy(dtype=float)
    return np.array([ultimo_ciclo[i % 12] for i in range(h)])


def _mejor_ets(train: pd.Series, h: int) -> tuple[np.ndarray, tuple]:
    """Busca trend x damped x seasonal por AICc (no por error de pronóstico)."""
    from statsmodels.tools.sm_exceptions import ConvergenceWarning
    from statsmodels.tsa.holtwinters import ExponentialSmoothing

    positivo = bool((train > 0).all())
    mejor = None
    for trend in (None, "add"):
        for damped in ((False,) if trend is None else (False, True)):
            for seasonal in ("add", "mul"):
                if seasonal == "mul" and not positivo:
                    continue  # estacional multiplicativo exige serie > 0; Trends trae ceros reales
                try:
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore", category=ConvergenceWarning)
                        m = ExponentialSmoothing(
                            train,
                            trend=trend,
                            damped_trend=damped,
                            seasonal=seasonal,
                            seasonal_periods=12,
                            initialization_method="estimated",
                        ).fit(optimized=True)
                except Exception:  # noqa: BLE001
                    continue
                aicc = getattr(m, "aicc", np.inf)
                if not np.isfinite(aicc):
                    continue
                if mejor is None or aicc < mejor[0]:
                    mejor = (aicc, m, (trend, damped, seasonal))
    if mejor is None:
        # último recurso si toda la rejilla falló al ajustar: nivel + estacional aditivo
        m = ExponentialSmoothing(
            train,
            trend=None,
            seasonal="add",
            seasonal_periods=12,
            initialization_method="estimated",
        ).fit(optimized=True)
        mejor = (getattr(m, "aicc", np.nan), m, (None, False, "add"))
    _, modelo, spec = mejor
    return np.asarray(modelo.forecast(h), dtype=float), spec


def _decidir_d_D(train: pd.Series) -> tuple[int, int]:
    """Fija (d, D) con pruebas ADF sobre nivel, diferenciación estacional y
    diferenciación regular — no se buscan por fuerza bruta.

    Se prueba en orden de menor a mayor diferenciación y se detiene en la
    primera combinación estacionaria (ADF rechaza raíz unitaria a alfa=0.05),
    para no sobrediferenciar una serie corta de ~5 años de datos mensuales.
    """
    from statsmodels.tsa.stattools import adfuller

    def estacionaria(s: pd.Series) -> bool:
        s = s.dropna()
        if len(s) < 8:
            return False
        try:
            return adfuller(s, autolag="AIC")[1] < 0.05
        except Exception:  # noqa: BLE001
            return False

    if estacionaria(train):
        return 0, 0
    if estacionaria(train.diff(12)):
        return 0, 1
    if estacionaria(train.diff(1)):
        return 1, 0
    return 1, 1


def _mejor_sarima(
    train: pd.Series, h: int
) -> tuple[np.ndarray, tuple, np.ndarray, np.ndarray]:
    """Rejilla acotada p,q en 0..2 y P,Q en 0..1, con d,D fijados por ADF.

    Selección por AICc. Devuelve también el intervalo de confianza al 95%,
    recortado a [0, 100] (dominio válido del índice de Google Trends).
    """
    from statsmodels.tools.sm_exceptions import ConvergenceWarning
    from statsmodels.tsa.statespace.sarimax import SARIMAX

    d, D = _decidir_d_D(train)
    mejor = None
    for p in range(3):
        for q in range(3):
            for P in range(2):
                for Q in range(2):
                    if p == q == P == Q == 0:
                        continue
                    try:
                        with warnings.catch_warnings():
                            warnings.simplefilter("ignore", category=ConvergenceWarning)
                            m = SARIMAX(
                                train,
                                order=(p, d, q),
                                seasonal_order=(P, D, Q, 12),
                                enforce_stationarity=False,
                                enforce_invertibility=False,
                            ).fit(disp=0)
                    except Exception:  # noqa: BLE001
                        continue
                    aicc = getattr(m, "aicc", np.inf)
                    if not np.isfinite(aicc):
                        continue
                    if mejor is None or aicc < mejor[0]:
                        mejor = (aicc, m, (p, d, q, P, D, Q))
    if mejor is None:
        m = SARIMAX(
            train,
            order=(1, d, 1),
            seasonal_order=(0, D, 0, 12),
            enforce_stationarity=False,
            enforce_invertibility=False,
        ).fit(disp=0)
        mejor = (getattr(m, "aicc", np.nan), m, (1, d, 1, 0, D, 0))
    _, modelo, orden = mejor
    pred = modelo.get_forecast(h)
    forecast = np.asarray(pred.predicted_mean, dtype=float)
    ci = pred.conf_int(alpha=0.05)
    ci_inf = np.clip(np.asarray(ci.iloc[:, 0], dtype=float), 0, 100)
    ci_sup = np.clip(np.asarray(ci.iloc[:, 1], dtype=float), 0, 100)
    return forecast, orden, ci_inf, ci_sup


def _pronostico(train: pd.Series, metodo: str, h: int):
    """Devuelve (forecast, ci_inf, ci_sup). El intervalo es None si el modelo
    no produce uno analítico (hoy solo SARIMA lo hace)."""
    if metodo == "Seasonal Naive":
        return _seasonal_naive(train, h), None, None

    if metodo == "ETS":
        forecast, _spec = _mejor_ets(train, h)
        return forecast, None, None

    if metodo == "SARIMA":
        forecast, _orden, ci_inf, ci_sup = _mejor_sarima(train, h)
        return forecast, ci_inf, ci_sup

    raise ValueError(f"Modelo no reconocido: {metodo}")


def _metricas(real: np.ndarray, forecast: np.ndarray, media_serie: float) -> dict:
    """MAE/RMSE siempre; MAPE solo si todos los reales >= 1 (si no, sMAPE);
    corr_forma y rango_forecast para detectar pronósticos planos disfrazados
    de buen error (ver comentario al inicio de esta sección)."""
    e = real - forecast
    mae = float(np.mean(np.abs(e)))
    rmse = float(np.sqrt(np.mean(e**2)))
    mape = float(np.mean(np.abs(e) / real) * 100) if np.all(real >= 1) else np.nan

    denom = np.abs(real) + np.abs(forecast)
    smape_terms = np.where(
        denom == 0, 0.0, 2 * np.abs(e) / np.where(denom == 0, 1, denom)
    )
    smape = float(np.mean(smape_terms) * 100)

    if np.std(real) > 0 and np.std(forecast) > 0:
        corr = float(np.corrcoef(real, forecast)[0, 1])
    else:
        corr = 0.0  # forecast constante: no hay forma que correlacionar, cuenta como "sin forma"

    rango = float(np.max(forecast) - np.min(forecast))
    rango_pct = float(rango / media_serie * 100) if media_serie else np.nan

    return {
        "MAE": mae,
        "RMSE": rmse,
        "MAPE %": mape,
        "sMAPE %": smape,
        "corr_forma": corr,
        "rango_forecast": rango,
        "rango_pct": rango_pct,
    }


def backtesting(
    serie: pd.Series, modelos: list[str], holdout_meses: int = 12
) -> tuple[pd.DataFrame, dict]:
    """Holdout estrictamente temporal (nunca aleatorio): entrena con todo
    menos los últimos `holdout_meses` y evalúa contra esos meses reales.

    Devuelve (tabla de métricas por modelo, forecasts crudos por modelo).
    """
    s = serie.dropna().astype(float)
    n = len(s)
    if n == 0:
        return pd.DataFrame(), {}

    assert holdout_meses < n, (
        f"No se puede reservar un holdout de {holdout_meses} meses con solo {n} observaciones "
        "disponibles: el número de ventanas de validación no puede exceder los datos que existen."
    )

    train = s.iloc[:-holdout_meses]
    test = s.iloc[-holdout_meses:]
    if len(train) < 24:
        return pd.DataFrame(), {}

    media_serie = float(s.mean())
    resultados, forecasts = [], {}

    for metodo in modelos:
        try:
            forecast, ci_inf, ci_sup = _pronostico(train, metodo, holdout_meses)
        except Exception:  # noqa: BLE001
            forecast = np.repeat(float(train.iloc[-1]), holdout_meses)
            ci_inf = ci_sup = None
        forecast = np.asarray(forecast, dtype=float)[:holdout_meses]
        real = test.to_numpy(dtype=float)
        m = _metricas(real, forecast, media_serie)

        motivos = []
        if not np.isfinite(m["rango_pct"]) or m["rango_pct"] < 5:
            motivos.append(
                f"pronóstico plano: rango {m['rango_pct']:.1f}% de la media (< 5%)"
            )
        if m["corr_forma"] < 0.1:
            motivos.append(
                f"no sigue la forma real: corr {m['corr_forma']:.2f} (< 0.10)"
            )

        resultados.append(
            {
                "Modelo": metodo,
                **m,
                "Ventanas": holdout_meses,
                "descartado": len(motivos) > 0,
                "motivo_descarte": "; ".join(motivos),
            }
        )
        forecasts[metodo] = {
            "forecast": forecast,
            "real": real,
            "ci_inf": ci_inf,
            "ci_sup": ci_sup,
        }

    return pd.DataFrame(resultados), forecasts


def seleccionar_modelo(tabla: pd.DataFrame) -> dict:
    """Regla de selección, en orden:

    1. Descarta cualquier modelo cuyo `rango_pct` sea menor a 5% de la media
       de la serie, o cuya `corr_forma` sea menor a 0.1: es una línea plana
       disfrazada y no responde la pregunta del proyecto.
    2. Entre los que sobreviven, gana el menor RMSE.
    3. Si un modelo más simple queda dentro del 2% del mejor RMSE, gana el
       simple (Seasonal Naive < ETS < SARIMA).
    4. Si TODOS quedan descartados, se usa Seasonal Naive y la serie se marca
       como sin señal de forecast utilizable.
    """
    if tabla.empty:
        return {
            "modelo": None,
            "explicacion": "No hubo datos suficientes para comparar modelos.",
            "tabla": tabla,
            "sin_senal": True,
            "fila": None,
        }

    sobreviven = tabla[~tabla["descartado"]]

    if sobreviven.empty:
        fila_sn = tabla[tabla["Modelo"] == "Seasonal Naive"]
        fila = fila_sn.iloc[0] if not fila_sn.empty else tabla.iloc[0]
        explicacion = (
            "Todos los modelos evaluados producen un pronóstico plano o sin relación con la forma "
            f"real del año. Se usa **{fila['Modelo']}** como referencia mínima, pero esta serie "
            "<b>no tiene señal de forecast utilizable</b>: no hay base para recomendar un mes de "
            "mayor interés con confianza."
        )
        return {
            "modelo": str(fila["Modelo"]),
            "explicacion": explicacion,
            "tabla": tabla,
            "sin_senal": True,
            "fila": fila,
        }

    t = sobreviven.sort_values("RMSE").reset_index(drop=True)
    ganador = t.iloc[0]
    umbral = ganador["RMSE"] * 1.02
    candidatos = t[t["RMSE"] <= umbral].copy()
    candidatos["orden_simplicidad"] = candidatos["Modelo"].map(SIMPLICIDAD)
    elegido = candidatos.sort_values("orden_simplicidad").iloc[0]

    partes = [
        f"**{elegido['Modelo']}** obtiene RMSE {elegido['RMSE']:.2f} evaluado en los últimos "
        f"{int(elegido['Ventanas'])} meses reales."
    ]
    if elegido["Modelo"] != ganador["Modelo"]:
        partes.append(
            f"{ganador['Modelo']} tiene el menor RMSE ({ganador['RMSE']:.2f}), pero la diferencia es "
            f"menor a 2%: se prefiere {elegido['Modelo']} por ser el modelo más simple entre los que "
            "sí reflejan la forma real del año."
        )
    else:
        partes.append(
            "Es también el de menor RMSE entre los modelos que no fueron descartados."
        )

    descartados = tabla[tabla["descartado"]]
    if not descartados.empty:
        partes.append(
            "Se descartaron por pronóstico plano o sin forma real: "
            + "; ".join(
                f"{r['Modelo']} ({r['motivo_descarte']})"
                for _, r in descartados.iterrows()
            )
            + "."
        )
    return {
        "modelo": str(elegido["Modelo"]),
        "explicacion": " ".join(partes),
        "tabla": tabla,
        "sin_senal": False,
        "fila": elegido,
    }


def pronostico_final(serie: pd.Series, metodo: str, h: int = 12) -> pd.DataFrame:
    """Reentrena con toda la serie y proyecta h meses.

    El intervalo de confianza se recorta a [0, 100] (dominio válido del
    índice de Google Trends). Hoy solo SARIMA produce un intervalo analítico;
    en Seasonal Naive y ETS las columnas CI_inf/CI_sup quedan en NaN.
    """
    s = serie.dropna().astype(float)
    if s.empty or metodo is None:
        return pd.DataFrame()
    try:
        forecast, ci_inf, ci_sup = _pronostico(s, metodo, h)
    except Exception:  # noqa: BLE001
        forecast = np.repeat(float(s.iloc[-1]), h)
        ci_inf = ci_sup = None

    forecast = np.clip(np.asarray(forecast, dtype=float), 0, 100)
    fechas = pd.date_range(s.index[-1] + pd.offsets.MonthBegin(1), periods=h, freq="MS")
    out = pd.DataFrame({"Fecha": fechas, "Pronóstico": forecast})
    out["CI_inf"] = np.clip(ci_inf, 0, 100) if ci_inf is not None else np.nan
    out["CI_sup"] = np.clip(ci_sup, 0, 100) if ci_sup is not None else np.nan
    return out

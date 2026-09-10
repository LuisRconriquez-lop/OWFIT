# Dashboard de pricing — OWFIT México

Herramienta de análisis de precios para OWFIT en el mercado mexicano de ropa deportiva
femenina. Combina cuatro fuentes —mercado, encuesta de consumidor, Google Trends y datos
internos— para calcular precios recomendados que consideran a la vez la posición competitiva
y la rentabilidad unitaria.

El dashboard **funciona sin datos confidenciales**: arranca con un archivo de demostración
ficticio y OWFIT puede cargar el suyo cuando quiera.

---

## Arranque rápido

```bash
pip install -r requirements.txt
streamlit run app.py
```

Se abre en `http://localhost:8501`. No hace falta configurar nada más: los datos del
proyecto ya están en `data/` y el archivo interno de demostración se carga solo.

Para regenerar el archivo de demostración:

```bash
python scripts/generar_demo.py
```

---

## Confidencialidad

El proyecto separa dos tipos de datos y los trata distinto.

| | Datos del proyecto | Datos internos de OWFIT |
|---|---|---|
| Qué son | Mercado, encuesta, Google Trends | PVP, COGS, piezas |
| Naturaleza | Públicos o de investigación propia | Confidenciales |
| Dónde viven | `data/` dentro del repositorio | Fuera del repositorio |
| Cómo entran | Se leen del disco al arrancar | Se suben desde la barra lateral |
| Persistencia | Versionados | Solo en memoria durante la sesión |

Los valores internos **no están escritos en el código**, no aparecen en ejemplos ni en
documentación, y `.gitignore` bloquea `data/interno/` y cualquier archivo con `_REAL` o
`_CONFIDENCIAL` en el nombre.

El archivo `data/demo/OWFIT_DEMO_datos_internos.xlsx` contiene **20 productos completamente
inventados** y una hoja LEEME que lo advierte. Sirve solo para demostrar que el dashboard
funciona.

### Cómo cargar los datos reales

1. Abra el dashboard y use **Datos internos de OWFIT** en la barra lateral.
2. Suba un Excel o CSV con esta estructura:

| Columna | Obligatoria | Descripción |
|---|---|---|
| `Producto` | Sí | Nombre o identificador |
| `PVP` | Sí | Precio de venta al público, MXN |
| `COGS` | Sí | Costo de la prenda en almacén, embolsada y lista para entregar |
| `Categoría` | Recomendada | Si falta, se infiere del nombre del producto |
| `Cantidad` | Recomendada | Piezas; permite ponderar los promedios por volumen |

Se aceptan nombres equivalentes (`Precio`, `Costo`, `Piezas`, `Unidades`) y columnas
adicionales, que se conservan sin modificar. Si falta una columna obligatoria, el dashboard
lo dice con un mensaje que nombra la columna y no intenta adivinar.

**El COGS ya incluye** fabricación, importación, transporte, aranceles y bodega. El modelo
no los vuelve a sumar. Los costos que sí se agregan encima (pasarela, publicidad, envío,
material de envío) se configuran en la barra lateral.

---

## Las diez páginas

1. **Resumen** — KPIs de portafolio, posición competitiva y hallazgos automáticos, cada uno
   citando la cifra que lo sostiene.
2. **Pricing** — Precio recomendado producto por producto, resumen por categoría, y una
   pestaña dedicada a los conflictos entre mercado y margen.
3. **Simulador** — Controles interactivos, cascada de costos, curva de sensibilidad al precio
   y comparación de los cinco percentiles objetivo.
4. **Competencia** — OWFIT contra el mercado, por categoría comparable y por segmento.
5. **Rentabilidad** — Estructura de costos, márgenes por producto y sensibilidad a cada
   parámetro de costo.
6. **Encuesta** — Perfil, importancia de atributos, Van Westendorp, Gabor-Granger y el
   diagnóstico de segmentación.
7. **EDA de mercado** — Distribuciones, comparaciones, variantes, calidad de datos y la lista
   de análisis que la base no permite ejecutar.
8. **Estacionalidad** — Interés de búsqueda, perfil mensual y selección de modelo por
   backtesting.
9. **Packaging** — Escenario actual contra escenario con empaque premium para conjuntos.
10. **Metodología** — Fuentes, fórmulas, supuestos, límites y recursos.

---

## Cómo se calcula el precio recomendado

No es una regla fija. Se construye en cinco pasos y cada producto guarda cuál mandó.

**1. Referencia competitiva.** Percentil objetivo (P50 a P75) de los precios de la misma
categoría dentro del conjunto competitivo elegido.

Las marcas se **balancean**: cada una aporta el mismo peso a la distribución sin importar
cuántas referencias tenga en catálogo. Sin este ajuste, la marca con el catálogo más grande
define sola los percentiles del mercado; en esta base concreta eso desplazaba el P65 de
leggings de unos $1,170 a $3,390.

**2. Piso de rentabilidad.** El precio que alcanza el margen de contribución objetivo:

```
P_mínimo = (COGS + costos fijos por unidad) / (1 − costos variables % − margen objetivo)
```

**3. Combinación.** Por defecto se toma el mayor de los dos, para no recomendar un precio
alineado al mercado que deje el margen por debajo de la meta. También se puede priorizar
explícitamente uno u otro. Cuando ambos apuntan a precios distintos, el producto queda
marcado como conflicto y aparece en su propia pestaña.

**4. Techo de disposición a pagar.** Opcional, y solo se aplica a la categoría que la encuesta
preguntó de verdad. No se extrapola a categorías que nunca se preguntaron.

**5. Redondeo comercial.** Terminación en 9, múltiplos de 10 o de 50, o sin redondeo.

Si una categoría tiene menos comparables que el mínimo configurado, la referencia de mercado
no se usa y el producto se marca: con pocos comparables, un percentil es ruido.

### Métricas financieras

```
Margen bruto        = (PVP − COGS) / PVP
Utilidad por unidad = PVP − COGS − PVP·(pasarela + publicidad + otros) − envío − material
Margen de contrib.  = Utilidad por unidad / PVP
```

Se llama **margen de contribución estimado**, no margen neto: no incluye renta, nómina,
software, devoluciones ni impuestos sobre la utilidad.

---

## Decisiones metodológicas

**Análisis a nivel producto, no a nivel variante.** Las tallas y colores de un modelo se
agrupan (la mediana de sus precios). Sin esto, una marca con veinte variantes por modelo
pesaría veinte veces más que otra con una.

**Categorías normalizadas.** Un producto capturado como «Legging» y otro como «Leggings»
terminan en la misma categoría, para que leggings se comparen contra leggings. Las etiquetas
que no coinciden con ninguna categoría conocida se conservan tal cual: no se fuerzan.

**Nada se elimina en silencio.** Accesorios, productos sin categorizar y registros con precio
cero se **marcan** y se excluyen de las comparaciones por categoría, pero permanecen en la
base y su conteo aparece en la pestaña de calidad de datos. Los faltantes se conservan como
faltantes; nunca se convierten en cero.

**Conversión de moneda.** Los catálogos en dólares se convierten con un tipo de cambio
editable desde la barra lateral.

### El clustering se somete a prueba antes de usarse

La segmentación de consumidores pasa por cuatro criterios: tamaño muestral suficiente,
variables no ipsativas, silueta por encima del umbral y grupos de tamaño accionable. Si
alguno falla, **no se presentan segmentos** y la página explica cuál falló y por qué.

Con los datos actuales el diagnóstico se ejecuta en vivo y muestra el resultado. La página
ofrece cortes descriptivos por gasto habitual, edad y frecuencia de compra como alternativa
accionable.

### La selección del modelo de pronóstico es empírica

Se comparan tres modelos: Seasonal Naive (baseline obligatorio), ETS/Holt-Winters (rejilla por
AICc) y SARIMA (diferenciación fijada por pruebas ADF, órdenes p/q/P/Q por AICc en una rejilla
acotada). No hay un ARIMA sin componente estacional: sin él, el pronóstico converge a la media
en 1-2 pasos y no puede reproducir un patrón anual.

La validación es un holdout estrictamente temporal de los últimos 12 meses (nunca aleatorio).
El error de pronóstico no decide solo: primero se descarta cualquier modelo cuyo pronóstico sea
esencialmente plano (poco rango, poca correlación con la forma real del año — un modelo que solo
predice el promedio puede ganar en RMSE sin decir nada útil sobre estacionalidad), y solo entre
los que sobreviven gana el menor RMSE, con empate a favor del modelo más simple si la diferencia
es menor a 2%.

---

## Límites del análisis

- **No estima demanda ni ventas.** No hay datos de transacciones ni de conversión. La utilidad
  total supone que se vende el inventario declarado; no lo pronostica.
- **La encuesta no es representativa.** Muestra por conveniencia y pequeña. Describe a quienes
  contestaron, no al mercado mexicano ni a la base de clientes de OWFIT.
- **Google Trends mide interés de búsqueda**, no demanda. Es un índice relativo que Google
  re-escala en cada consulta, así que los niveles no son comparables entre términos.
- **Los precios de la competencia son de lista.** La base no incluye precio original ni
  descuentos, así que ese análisis no se puede ejecutar.
- **Sin datos de materiales, rating ni reseñas** en la base actual. Esos análisis se activan
  solos si la base incorpora las columnas; mientras tanto aparecen listados como no disponibles.
- **La captura es una foto de un momento**, no un promedio del año.

---

## Estructura

```
owfit_pricing/
├── app.py                     Navegación, barra lateral y carga de contexto
├── requirements.txt
├── config/
│   └── settings.py            Parámetros, mapeo de categorías, segmentos, enlaces
├── src/
│   ├── loaders.py             Carga de las cuatro fuentes
│   ├── validation.py          Contratos de columnas y mensajes de error
│   ├── market.py              EDA y percentiles competitivos
│   ├── survey.py              Van Westendorp, Gabor-Granger, diagnóstico de clustering
│   ├── trends.py              Estacionalidad y backtesting de modelos
│   ├── pricing.py             Rentabilidad y motor de precio recomendado
│   ├── insights.py            Hallazgos automáticos
│   ├── charts.py              Gráficas
│   ├── ui.py                  Tema visual y componentes
│   └── utils.py               Formato, normalización y manejo de NA
├── views/                     Una página por módulo del menú
├── scripts/
│   └── generar_demo.py        Genera el archivo interno ficticio
└── data/
    ├── mercado/               Base de catálogos
    ├── encuesta/              Respuestas y glosario
    ├── google_trends/         Uno o varios archivos exportados
    └── demo/                  Archivo interno ficticio
```

---

## Personalización

Casi todo se ajusta desde la barra lateral. Lo que se configura en código vive en
`config/settings.py`:

| Qué | Constante |
|---|---|
| Segmento de cada marca | `SEGMENTO_MARCAS` |
| Equivalencias de categorías | `MAPA_CATEGORIAS` |
| Costos variables por defecto | `COSTOS_DEFAULT` |
| Percentiles disponibles | `PERCENTILES_OBJETIVO` |
| Umbrales del diagnóstico de clustering | `CLUSTER_MIN_N`, `CLUSTER_MIN_SILHOUETTE` |
| Categoría de referencia de la encuesta | `CATEGORIA_REFERENCIA_ENCUESTA` |
| Enlaces de la página de Metodología | `ENLACES_RECURSOS` |

### Agregar más archivos de Google Trends

Coloque los archivos exportados en `data/google_trends/`. El dashboard lee todos los CSV y
Excel de la carpeta y los combina en una sola base mensual. Si un término aparece en dos
archivos, se promedia y se avisa: el índice de Google se re-escala en cada consulta, así que
dos exportaciones no son directamente comparables.

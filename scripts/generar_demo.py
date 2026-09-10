"""Genera el archivo interno de DEMOSTRACIÓN con datos completamente inventados.

Ejecutar desde la raíz del proyecto:
    python scripts/generar_demo.py

El archivo resultante (data/demo/OWFIT_DEMO_datos_internos.xlsx) NO contiene
información real de OWFIT. Sirve para que el dashboard funcione sin necesidad
de cargar datos confidenciales.
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import settings  # noqa: E402

FILAS = [
    # Producto,                     Categoría,  PVP,  COGS, Cantidad
    ("Legging Demo Alta Cintura", "Leggings", 1000, 400, 100),
    ("Legging Demo Textura", "Leggings", 950, 390, 80),
    ("Legging Demo Bolsillos", "Leggings", 1090, 460, 60),
    ("Legging Demo Básico", "Leggings", 870, 355, 95),
    ("Top Demo Cruzado", "Tops", 800, 300, 80),
    ("Top Demo Manga Larga", "Tops", 880, 340, 45),
    ("Top Demo Sin Costuras", "Tops", 760, 285, 70),
    ("Sports Bra Demo Alto Impacto", "Sports Bra", 890, 350, 55),
    ("Sports Bra Demo Ligero", "Sports Bra", 720, 270, 65),
    ("Short Demo Ciclista", "Shorts", 700, 265, 90),
    ("Short Demo Corte Alto", "Shorts", 650, 245, 75),
    ("Set Demo Entrenamiento", "Sets/Conjuntos", 1600, 650, 50),
    ("Set Demo Casual", "Sets/Conjuntos", 1750, 720, 35),
    ("Set Demo Premium", "Sets/Conjuntos", 1980, 830, 20),
    ("Jogger Demo Felpa", "Pants/Joggers", 1250, 520, 40),
    ("Pants Demo Recto", "Pants/Joggers", 1180, 495, 30),
    ("Chamarra Demo Rompevientos", "Chamarras/Sudaderas", 1750, 780, 25),
    ("Sudadera Demo Oversize", "Chamarras/Sudaderas", 1450, 640, 30),
    ("Vestido Demo Deportivo", "Vestidos", 1200, 500, 18),
    ("Falda Demo Short Integrado", "Faldas", 850, 340, 28),
]

LEEME = pd.DataFrame(
    {
        "AVISO": [
            "DATOS DE DEMOSTRACIÓN — NO SON DATOS REALES DE OWFIT.",
            "",
            "Todos los valores de PVP, COGS y Cantidad de esta hoja son inventados.",
            "Su único propósito es permitir que el dashboard funcione sin datos confidenciales.",
            "",
            "Para usar datos reales:",
            "1. Copie la estructura de la hoja 'Datos' en su propio archivo Excel.",
            "2. Columnas obligatorias: Producto, PVP, COGS.",
            "3. Columnas recomendadas: Categoría, Cantidad.",
            "4. Puede agregar columnas adicionales; el dashboard las conserva.",
            "5. Cárguelo desde la barra lateral del dashboard.",
            "",
            "El archivo cargado se procesa en memoria durante la sesión.",
            "No se escribe en el repositorio ni queda dentro del código.",
            "",
            "El COGS debe representar el costo de tener la prenda en almacén,",
            "embolsada y lista para entregar. No sume aquí pasarela, publicidad ni envío:",
            "esos costos se configuran por separado dentro del dashboard.",
        ]
    }
)


def main():
    df = pd.DataFrame(
        FILAS, columns=["Producto", "Categoría", "PVP", "COGS", "Cantidad"]
    )
    destino = settings.PATH_DEMO_INTERNO
    destino.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(destino, engine="openpyxl") as w:
        LEEME.to_excel(w, sheet_name="LEEME", index=False)
        df.to_excel(w, sheet_name="Datos", index=False)
    print(f"Archivo de demostración generado: {destino}")
    print(f"{len(df)} productos ficticios.")


if __name__ == "__main__":
    main()

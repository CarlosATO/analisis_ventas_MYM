"""
tabs/base.py — Pestaña "Base de análisis"
Tabla completa del SKU summary con columnas renombradas y exportación Excel.
"""

import streamlit as st
import pandas as pd

from helpers import dl_excel_btn, theme_palette


def render_base(sku_df: pd.DataFrame, is_dark: bool) -> None:
    """Renderiza la pestaña Base analítica consolidada por SKU."""

    st.subheader("Base analítica consolidada por SKU")

    base_out = sku_df.rename(columns={
        "venta_6m":                    "Venta del período",
        "unidades_6m":                 "Unidades vendidas",
        "margen_6m":                   "Margen estimado",
        "fecha_primera_venta":         "Primera venta",
        "fecha_ultima_venta":          "Última venta",
        "dias_desde_ultima_venta":     "Días sin venta",
        "Cantidad Disponible":         "Stock disponible",
        "unidades_promedio_diaria_30d":"Demanda diaria promedio",
        "dias_cobertura":              "Días de cobertura",
        "valor_stock_disponible":      "Valor del stock",
        "alerta":                      "Alerta",
        "prioridad":                   "Prioridad",
    }).sort_values("Venta del período", ascending=False)

    st.dataframe(base_out, hide_index=True, width="stretch")
    dl_excel_btn(base_out, "base_analitica_sku.xlsx", "Base SKU")

"""
tabs/stock_sin_ventas.py — Pestaña "Stock sin ventas"
Gráfico horizontal Top 15 por valor de stock + tabla completa + Excel.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

from analytics import build_sku_summary, classify_skus
from helpers import fmt_money, fmt_date, suggest_action, dl_excel_btn, plotly_theme, theme_palette


def render_stock_sin_ventas(
    sales_global: pd.DataFrame,
    stock_global: pd.DataFrame,
    is_dark: bool,
    max_sales_date: pd.Timestamp,
    min_sales_date: pd.Timestamp,
) -> None:
    """Renderiza la pestaña Productos con stock sin ventas."""

    p = theme_palette(is_dark)
    TEXT_MAIN = p["TEXT_MAIN"]

    st.subheader("Productos con stock sin ventas")
    st.caption("Productos con inventario disponible que no registran ventas en el período analizado.")

    dead_period = st.selectbox(
        "Período de referencia",
        ["Historial completo", "Últimos 45 días", "Últimos 90 días"],
        key="dead_period",
    )
    inact_days = {"Últimos 45 días": 45, "Últimos 90 días": 90}.get(dead_period, 45)
    if dead_period == "Historial completo":
        d_start = min_sales_date
    elif dead_period == "Últimos 45 días":
        d_start = max_sales_date - pd.Timedelta(days=45)
    else:
        d_start = max_sales_date - pd.Timedelta(days=90)
    d_start = max(d_start, min_sales_date)
    st.info(f"Mostrando ventas desde {d_start.strftime('%d-%m-%Y')} hasta {max_sales_date.strftime('%d-%m-%Y')}")

    sku_d = classify_skus(build_sku_summary(sales_global, stock_global, d_start, max_sales_date))

    # Ampliar clasificación si el período no es historial completo
    if dead_period != "Historial completo":
        cond = (
            (sku_d["Cantidad Disponible"] > 0) &
            (sku_d["dias_desde_ultima_venta"] >= inact_days) &
            (sku_d["venta_6m"] == 0)
        )
        sku_d.loc[cond, "alerta"]    = "Producto muerto con stock"
        sku_d.loc[cond, "prioridad"] = "Alta"

    dead_d = sku_d[sku_d["alerta"] == "Producto muerto con stock"].copy()
    dead_d["Acción sugerida"] = dead_d["dias_desde_ultima_venta"].apply(suggest_action)
    dead_d["Subestado"] = np.where(
        dead_d["tuvo_demanda_historica"],
        "Tuvo demanda, hoy inmovilizado",
        "Sin demanda histórica relevante",
    )
    dead_d = dead_d.sort_values("valor_stock_disponible", ascending=False)

    if dead_d.empty:
        st.info("No se encontraron productos con stock sin ventas en esta selección.")
        return

    # Gráfico horizontal Top 15
    top = dead_d.head(15).sort_values("valor_stock_disponible")
    fig = go.Figure(go.Bar(
        x=top["valor_stock_disponible"],
        y=top["Producto"],
        orientation="h",
        marker_color="#EF4444",
        text=[fmt_money(v) for v in top["valor_stock_disponible"]],
        textposition="inside",
        textfont=dict(size=9, color="#FFFFFF"),
    ))
    fig.update_layout(
        xaxis_title="Valor del stock inmovilizado ($)",
        yaxis_title="",
        **plotly_theme(is_dark),
    )
    st.plotly_chart(fig, width="stretch")

    # Tabla completa
    tbl = dead_d.reset_index(drop=True)
    tbl.insert(0, "Ranking", range(1, len(tbl) + 1))
    out = tbl[["Ranking","SKU","Producto","Subestado","Cantidad Disponible",
               "valor_stock_disponible","fecha_ultima_venta",
               "dias_desde_ultima_venta","Acción sugerida"]].rename(columns={
        "Cantidad Disponible":"Stock disponible",
        "valor_stock_disponible":"Valor estimado del stock",
        "fecha_ultima_venta":"Última venta",
        "dias_desde_ultima_venta":"Días sin venta",
    })
    out["Valor estimado del stock"] = out["Valor estimado del stock"].apply(fmt_money)
    out["Última venta"] = out["Última venta"].apply(fmt_date)
    st.dataframe(out, hide_index=True, width="stretch")
    dl_excel_btn(out, "stock_sin_ventas.xlsx", "Stock sin ventas")

"""
tabs/caidas.py — Pestaña "Caídas y crecimiento"
Dos columnas: productos con mayor caída / mayor crecimiento + tablas + Excel.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

from analytics import build_sku_summary, classify_skus
from helpers import fmt_money, fmt_pct, dl_excel_btn, plotly_theme, theme_palette


def render_caidas(
    sales_global: pd.DataFrame,
    stock_global: pd.DataFrame,
    is_dark: bool,
    min_sales_filter: float,
    max_sales_date: pd.Timestamp,
    min_sales_date: pd.Timestamp,
) -> None:
    """Renderiza la pestaña Caídas y crecimiento."""

    p = theme_palette(is_dark)
    TEXT_MAIN = p["TEXT_MAIN"]

    st.subheader("Caídas y crecimiento de ventas")
    st.caption(
        "Se compara el período seleccionado contra el período inmediatamente anterior "
        "de igual duración."
    )

    caida_period = st.selectbox(
        "Comparativa de períodos",
        [
            "Comparar últimas 4 semanas vs 4 semanas anteriores",
            "Comparar últimas 8 semanas vs 8 semanas anteriores",
            "Comparar últimos 3 meses vs 3 meses anteriores",
        ],
        index=1,
        key="caida_period",
    )
    if "4 semanas" in caida_period:
        ca_start = max_sales_date - pd.Timedelta(days=56)
    elif "8 semanas" in caida_period:
        ca_start = max_sales_date - pd.Timedelta(days=112)
    else:
        ca_start = max_sales_date - pd.Timedelta(days=180)
    ca_start = max(ca_start, min_sales_date)
    st.info(
        f"Período actual: {ca_start.strftime('%d-%m-%Y')} → {max_sales_date.strftime('%d-%m-%Y')}"
    )

    sku_ca = classify_skus(build_sku_summary(sales_global, stock_global, ca_start, max_sales_date))

    fall_ca = sku_ca[
        (sku_ca["venta_prev_60d"] > 0) &
        (sku_ca["venta_prev_60d"] >= min_sales_filter) &
        (sku_ca["diferencia_venta_periodo"] < 0)
    ].sort_values("diferencia_venta_periodo")

    growth_ca = sku_ca[
        (sku_ca["venta_prev_60d"] > 0) &
        (sku_ca["venta_6m"] >= min_sales_filter) &
        (sku_ca["diferencia_venta_periodo"] > 0)
    ].sort_values("diferencia_venta_periodo", ascending=False)

    RENAME = {
        "venta_6m":"Venta período actual",
        "venta_prev_60d":"Venta período anterior",
        "diferencia_venta_periodo":"Diferencia ($)",
        "variacion_60d_pct":"Variación %",
        "Cantidad Disponible":"Stock disponible",
    }

    col_a, col_b = st.columns(2)

    # ── Caídas ──
    with col_a:
        st.subheader("Productos que más redujeron ventas")
        if not fall_ca.empty:
            top_fall = fall_ca.head(15)
            chart_fall = top_fall.sort_values("diferencia_venta_periodo", ascending=False)
            fig_fall = go.Figure(go.Bar(
                x=chart_fall["diferencia_venta_periodo"],
                y=chart_fall["Producto"],
                orientation="h",
                marker_color="#EF4444",
                text=[fmt_money(v) for v in chart_fall["diferencia_venta_periodo"]],
                textposition="inside",
                textfont=dict(size=9, color="#FFFFFF"),
            ))
            fig_fall.update_layout(xaxis_title="Diferencia ($)", yaxis_title="", **plotly_theme(is_dark))
            st.plotly_chart(fig_fall, width="stretch")

            tbl = fall_ca.head(50).copy()
            tbl["Acción sugerida"] = np.where(
                tbl["diferencia_venta_periodo"] < -500000,
                "Investigar causa urgente", "Revisar precio y disponibilidad",
            )
            tbl = tbl.reset_index(drop=True)
            tbl.insert(0, "Ranking", range(1, len(tbl) + 1))
            out = tbl[["Ranking","SKU","Producto","venta_6m","venta_prev_60d",
                        "diferencia_venta_periodo","variacion_60d_pct",
                        "Cantidad Disponible","Acción sugerida"]].rename(columns=RENAME)
            for c in ["Venta período actual","Venta período anterior","Diferencia ($)"]:
                out[c] = out[c].apply(fmt_money)
            out["Variación %"] = out["Variación %"].apply(fmt_pct)
            st.dataframe(out, hide_index=True, width="stretch")
            dl_excel_btn(out, "caidas_ventas.xlsx", "Caídas")
        else:
            st.info("Sin caídas detectadas con los filtros actuales.")

    # ── Crecimientos ──
    with col_b:
        st.subheader("Productos que más aumentaron ventas")
        if not growth_ca.empty:
            top_grow = growth_ca.head(15)
            chart_grow = top_grow.sort_values("diferencia_venta_periodo")
            fig_grow = go.Figure(go.Bar(
                x=chart_grow["diferencia_venta_periodo"],
                y=chart_grow["Producto"],
                orientation="h",
                marker_color="#22C55E",
                text=[fmt_money(v) for v in chart_grow["diferencia_venta_periodo"]],
                textposition="inside",
                textfont=dict(size=9, color="#FFFFFF"),
            ))
            fig_grow.update_layout(xaxis_title="Diferencia ($)", yaxis_title="", **plotly_theme(is_dark))
            st.plotly_chart(fig_grow, width="stretch")

            tbl = growth_ca.head(50).copy()
            tbl["Acción sugerida"] = "Reforzar stock y visibilidad comercial"
            tbl = tbl.reset_index(drop=True)
            tbl.insert(0, "Ranking", range(1, len(tbl) + 1))
            out = tbl[["Ranking","SKU","Producto","venta_6m","venta_prev_60d",
                        "diferencia_venta_periodo","variacion_60d_pct",
                        "Cantidad Disponible","Acción sugerida"]].rename(columns=RENAME)
            for c in ["Venta período actual","Venta período anterior","Diferencia ($)"]:
                out[c] = out[c].apply(fmt_money)
            out["Variación %"] = out["Variación %"].apply(fmt_pct)
            st.dataframe(out, hide_index=True, width="stretch")
            dl_excel_btn(out, "crecimiento_ventas.xlsx", "Crecimiento")
        else:
            st.info("Sin crecimientos detectados con los filtros actuales.")

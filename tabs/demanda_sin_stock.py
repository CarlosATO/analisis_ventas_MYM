"""
tabs/demanda_sin_stock.py — Pestaña "Demanda sin stock"
Gráfico horizontal por venta potencial + selectbox historial + tabla + Excel.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from analytics import build_sku_summary, classify_skus
from helpers import fmt_money, fmt_date, suggest_stockout_action, dl_excel_btn, plotly_theme, theme_palette


def render_demanda_sin_stock(
    sales_global: pd.DataFrame,
    stock_global: pd.DataFrame,
    sales_full: pd.DataFrame,       # ventas completas para historial de SKU
    is_dark: bool,
    max_sales_date: pd.Timestamp,
    min_sales_date: pd.Timestamp,
) -> None:
    """Renderiza la pestaña Demanda histórica sin stock."""

    p = theme_palette(is_dark)
    TEXT_MAIN = p["TEXT_MAIN"]

    st.subheader("Productos con demanda histórica pero sin stock")
    st.caption("Estos productos vendían, pero hoy no tienen inventario disponible.")

    ns_period = st.selectbox(
        "Período de referencia",
        ["Historial completo", "Últimas 12 semanas", "Últimas 24 semanas"],
        key="no_stock_period",
    )
    if ns_period == "Últimas 12 semanas":
        ns_start = max_sales_date - pd.Timedelta(weeks=12)
    elif ns_period == "Últimas 24 semanas":
        ns_start = max_sales_date - pd.Timedelta(weeks=24)
    else:
        ns_start = min_sales_date
    ns_start = max(ns_start, min_sales_date)
    st.info(f"Mostrando ventas desde {ns_start.strftime('%d-%m-%Y')} hasta {max_sales_date.strftime('%d-%m-%Y')}")

    sku_ns = classify_skus(build_sku_summary(sales_global, stock_global, ns_start, max_sales_date))
    dem_ns = sku_ns[sku_ns["alerta"] == "Demanda histórica sin stock"].copy()

    if dem_ns.empty:
        st.info("No se encontraron productos con demanda histórica sin stock.")
        return

    dem_ns["Venta potencial no capturada"] = (
        dem_ns["venta_promedio_mientras_vendia"] * dem_ns["dias_desde_ultima_venta"]
    )
    dem_ns["Acción sugerida"] = dem_ns["dias_desde_ultima_venta"].apply(suggest_stockout_action)
    dem_ns = dem_ns.sort_values("Venta potencial no capturada", ascending=False)

    # Gráfico horizontal Top 15
    top_ns = dem_ns.head(15).sort_values("Venta potencial no capturada")
    fig_ns = go.Figure(go.Bar(
        x=top_ns["Venta potencial no capturada"],
        y=top_ns["Producto"],
        orientation="h",
        marker_color="#F59E0B",
        text=[fmt_money(v) for v in top_ns["Venta potencial no capturada"]],
        textposition="inside",
        textfont=dict(size=9, color="#1E293B"),
    ))
    fig_ns.update_layout(
        xaxis_title="Venta potencial no capturada ($)",
        yaxis_title="",
        **plotly_theme(is_dark),
    )
    st.plotly_chart(fig_ns, width="stretch")

    # Selectbox historial de producto
    prod_opts = ["(seleccionar)"] + list(dem_ns["Producto"].dropna().unique())
    prod_sel  = st.selectbox("Ver historial de ventas semanales de un producto", prod_opts, key="prod_sel_ns")
    if prod_sel != "(seleccionar)":
        sku_sel  = dem_ns[dem_ns["Producto"] == prod_sel]["SKU"].iloc[0]
        hist_raw = sales_full[sales_full["SKU"] == sku_sel].copy()
        if not hist_raw.empty:
            hist_grp = (
                hist_raw.groupby(["Año", "Semana"], as_index=False)
                .agg(venta=("Venta Total Bruta", "sum"), unidades=("Cantidad", "sum"))
                .sort_values(["Año", "Semana"])
            )
            hist_grp["Label"] = hist_grp.apply(
                lambda r: f"S{int(r['Semana'])} ({int(r['Año'])})", axis=1
            )
            fig_hist = go.Figure(go.Bar(
                x=hist_grp["Label"], y=hist_grp["venta"],
                name="Venta semanal", marker_color="#F59E0B",
                text=[fmt_money(v) for v in hist_grp["venta"]],
                textposition="outside",
                textfont=dict(size=9, color=TEXT_MAIN),
            ))
            fig_hist.update_layout(
                title=f"Historial semanal: {prod_sel}",
                xaxis_title="Semana", yaxis_title="Venta ($)",
                **plotly_theme(is_dark),
            )
            st.plotly_chart(fig_hist, width="stretch")
        else:
            st.info("Sin historial de ventas para este producto.")

    # Tabla completa
    tbl = dem_ns.reset_index(drop=True)
    tbl.insert(0, "Ranking", range(1, len(tbl) + 1))
    out = tbl[["Ranking","SKU","Producto","venta_historica_total","unidades_historicas_total",
               "fecha_ultima_venta","dias_desde_ultima_venta",
               "Venta potencial no capturada","Acción sugerida"]].rename(columns={
        "venta_historica_total":"Venta histórica",
        "unidades_historicas_total":"Unidades históricas",
        "fecha_ultima_venta":"Última venta",
        "dias_desde_ultima_venta":"Días sin venta",
    })
    out["Venta histórica"]            = out["Venta histórica"].apply(fmt_money)
    out["Venta potencial no capturada"] = out["Venta potencial no capturada"].apply(fmt_money)
    out["Última venta"] = out["Última venta"].apply(fmt_date)
    st.caption("Venta potencial no capturada: estimación referencial basada en el ritmo de venta histórico.")
    st.dataframe(out, hide_index=True, width="stretch")
    dl_excel_btn(out, "demanda_historica_sin_stock.xlsx", "Demanda sin stock")

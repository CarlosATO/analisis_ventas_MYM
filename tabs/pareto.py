"""
tabs/pareto.py — Pestaña "Pareto 80/20"
Texto ejecutivo dinámico, gráfico combo barras+línea, tabla y exportación Excel.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from analytics import build_sku_summary, pareto_analysis
from helpers import fmt_money, fmt_pct, dl_excel_btn, plotly_theme, theme_palette


def render_pareto(
    sales_global: pd.DataFrame,
    stock_global: pd.DataFrame,
    is_dark: bool,
    max_sales_date: pd.Timestamp,
    min_sales_date: pd.Timestamp,
) -> None:
    """Renderiza la pestaña Pareto 80/20."""

    p = theme_palette(is_dark)
    ACCENT    = p["ACCENT"]
    TEXT_MAIN = p["TEXT_MAIN"]
    CARD_BG   = p["CARD_BG"]
    BORDER    = p["BORDER"]

    st.subheader("Análisis Pareto 80/20")

    pareto_period = st.selectbox(
        "Período para análisis de Pareto",
        ["Últimas 4 semanas", "Últimas 8 semanas", "Últimos 3 meses", "Todo el período"],
        key="pareto_period",
    )
    offsets = {
        "Últimas 4 semanas": pd.Timedelta(weeks=4),
        "Últimas 8 semanas": pd.Timedelta(weeks=8),
        "Últimos 3 meses":   pd.Timedelta(days=90),
    }
    p_start = max_sales_date - offsets.get(pareto_period, pd.Timedelta(0))
    if pareto_period == "Todo el período":
        p_start = min_sales_date
    p_start = max(p_start, min_sales_date)
    st.info(f"Mostrando ventas desde {p_start.strftime('%d-%m-%Y')} hasta {max_sales_date.strftime('%d-%m-%Y')}")

    sku_p   = build_sku_summary(sales_global, stock_global, p_start, max_sales_date)
    pareto_p = pareto_analysis(sku_p)

    if pareto_p.empty:
        st.info("Sin datos de Pareto para el período seleccionado.")
        return

    sku_80_n  = pareto_p[pareto_p["pct_acumulado"] <= 0.80]["SKU"].nunique()
    total_p   = pareto_p["SKU"].nunique()
    pct_sku_p = sku_80_n / total_p if total_p > 0 else 0

    # Texto ejecutivo dinámico
    st.markdown(
        f"""
        <div style="background:{CARD_BG};border:1px solid {BORDER};border-left:5px solid {ACCENT};
                    border-radius:6px;padding:12px 18px;margin-bottom:12px;">
            <strong style="color:{ACCENT};font-size:1.05em;">Resumen Pareto</strong>
            <p style="margin:6px 0 0 0;color:{TEXT_MAIN};">
                <strong>{sku_80_n}</strong> de <strong>{total_p}</strong> productos explican el
                <strong>80%</strong> de la venta.<br>
                Representan el <strong>{fmt_pct(pct_sku_p)}</strong> del total de SKUs vendidos.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Gráfico combo (Top 20)
    chart_p = pareto_p.head(20).copy()
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=chart_p["SKU"], y=chart_p["venta_6m"],
        name="Venta", marker_color=ACCENT,
        text=[fmt_money(v) for v in chart_p["venta_6m"]],
        textposition="outside",
        textfont=dict(size=9, color=TEXT_MAIN),
    ))
    fig.add_trace(go.Scatter(
        x=chart_p["SKU"], y=chart_p["pct_acumulado"] * 100,
        name="% Acumulado", yaxis="y2",
        mode="lines+markers",
        line=dict(color="#F59E0B", width=2),
        hovertemplate="%{x}<br>Acumulado: %{y:.1f}%<extra></extra>",
    ))
    fig.update_layout(**plotly_theme(is_dark))
    fig.update_layout(
        yaxis=dict(title="Venta ($)"),
        yaxis2=dict(title="% Acumulado", overlaying="y", side="right",
                    tickformat=".0f", ticksuffix="%"),
        xaxis=dict(title="SKU"),
        legend=dict(orientation="h"),
    )
    st.plotly_chart(fig, width="stretch")

    # Tabla completa
    tbl = pareto_p.reset_index(drop=True)
    tbl.insert(0, "Ranking", range(1, len(tbl) + 1))
    out = tbl[["Ranking","SKU","Producto / Servicio","venta_6m","pct_acumulado","clasificacion_pareto"]].rename(columns={
        "Producto / Servicio":"Producto", "venta_6m":"Venta del período",
        "pct_acumulado":"% Acumulado",  "clasificacion_pareto":"Clasificación",
    })
    out["Venta del período"] = out["Venta del período"].apply(fmt_money)
    out["% Acumulado"]       = out["% Acumulado"].apply(fmt_pct)
    st.dataframe(out.head(200), hide_index=True, width="stretch")
    dl_excel_btn(out, "pareto_80_20.xlsx", "Pareto")

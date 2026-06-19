"""
tabs/quiebres.py — Pestaña "Quiebres de stock"
Barras horizontales de días de cobertura + scatter en expander + tabla + Excel.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from analytics import build_sku_summary, classify_skus
from helpers import (
    fmt_date, suggest_quiebre_action,
    dl_excel_btn, plotly_theme, theme_palette,
)


def render_quiebres(
    sales_global: pd.DataFrame,
    stock_global: pd.DataFrame,
    is_dark: bool,
    max_sales_date: pd.Timestamp,
    min_sales_date: pd.Timestamp,
) -> None:
    """Renderiza la pestaña Riesgo de quiebre de stock."""

    p = theme_palette(is_dark)
    ACCENT    = p["ACCENT"]
    TEXT_MAIN = p["TEXT_MAIN"]

    st.subheader("Riesgo de quiebre de stock")
    st.caption(
        "Días de cobertura = stock actual ÷ demanda diaria promedio reciente. "
        "Menor cobertura = el stock alcanza para menos días según la rotación."
    )

    qb_period = st.selectbox(
        "Período para calcular demanda diaria",
        ["Últimas 2 semanas", "Últimas 4 semanas", "Últimas 8 semanas"],
        index=1,
        key="quiebre_period",
    )
    offsets = {
        "Últimas 2 semanas": pd.Timedelta(weeks=2),
        "Últimas 4 semanas": pd.Timedelta(weeks=4),
        "Últimas 8 semanas": pd.Timedelta(weeks=8),
    }
    qb_start = max_sales_date - offsets[qb_period]
    qb_start = max(qb_start, min_sales_date)
    st.info(f"Mostrando ventas desde {qb_start.strftime('%d-%m-%Y')} hasta {max_sales_date.strftime('%d-%m-%Y')}")

    sku_qb = classify_skus(build_sku_summary(sales_global, stock_global, qb_start, max_sales_date))

    cov_df = (
        sku_qb[
            (sku_qb["unidades_promedio_diaria_30d"] > 0) &
            (sku_qb["dias_cobertura"].notna())
        ]
        .sort_values("dias_cobertura", ascending=True)
        .head(15)
    )

    if not cov_df.empty:
        cov_df = cov_df.copy()
        cov_df["Label_Cob"] = cov_df["dias_cobertura"].apply(lambda x: f"{x:.0f} días")
        colors_bar = [
            "#EF4444" if d < 7 else "#F59E0B" if d < 15 else "#22C55E"
            for d in cov_df["dias_cobertura"]
        ]
        fig_cob = go.Figure(go.Bar(
            x=cov_df["dias_cobertura"],
            y=cov_df["Producto"],
            orientation="h",
            marker_color=colors_bar,
            text=cov_df["Label_Cob"],
            textposition="inside",
            textfont=dict(size=10, color="#FFFFFF"),
        ))
        fig_cob.update_layout(**plotly_theme(is_dark))
        fig_cob.update_xaxes(title_text="Días de cobertura estimada")
        fig_cob.update_yaxes(title_text="")
        st.plotly_chart(fig_cob, width="stretch")

    # Vista scatter en expander
    with st.expander("Vista técnica: stock disponible vs rotación diaria"):
        cov_scat = sku_qb[sku_qb["unidades_promedio_diaria_30d"] > 0].copy()
        if not cov_scat.empty:
            cov_scat["tamaño_visual"] = cov_scat["venta_6m"].abs().clip(lower=1)
            fig_scat = px.scatter(
                cov_scat,
                x="unidades_promedio_diaria_30d",
                y="Cantidad Disponible",
                size="tamaño_visual",
                hover_name="Producto",
                hover_data=["SKU", "dias_cobertura", "venta_6m", "alerta"],
                title="Stock disponible vs rotación diaria",
                color_discrete_sequence=[ACCENT],
            )
            fig_scat.update_layout(**plotly_theme(is_dark))
            st.plotly_chart(fig_scat, width="stretch")
        else:
            st.info("Sin datos para la vista técnica.")

    # Tabla SKUs en riesgo
    st.subheader("SKUs con menor cobertura")
    crit_qb = (
        sku_qb[sku_qb["alerta"].isin(["Quiebre crítico", "Riesgo de quiebre"])]
        .sort_values("dias_cobertura")
        .reset_index(drop=True)
    )
    if crit_qb.empty:
        st.info("No se detectaron SKUs en riesgo de quiebre.")
        return

    crit_qb.insert(0, "Ranking", range(1, len(crit_qb) + 1))
    crit_qb["Acción sugerida"] = crit_qb["dias_cobertura"].apply(suggest_quiebre_action)
    out = crit_qb[["Ranking","SKU","Producto","dias_cobertura","Cantidad Disponible",
                   "unidades_promedio_diaria_30d","Por recibir","alerta","Acción sugerida"]].rename(columns={
        "dias_cobertura":"Días de cobertura",
        "Cantidad Disponible":"Stock disponible",
        "unidades_promedio_diaria_30d":"Demanda diaria",
        "alerta":"Alerta",
    })
    out["Días de cobertura"] = out["Días de cobertura"].apply(
        lambda x: f"{x:.1f}" if pd.notna(x) else "-"
    )
    out["Demanda diaria"] = out["Demanda diaria"].apply(lambda x: f"{x:.2f}")
    st.dataframe(out, hide_index=True, width="stretch")
    dl_excel_btn(out, "quiebres_stock.xlsx", "Quiebres")

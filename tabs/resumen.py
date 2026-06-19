"""
tabs/resumen.py — Pestaña "Resumen Ejecutivo"
KPIs, evolución semanal con detalle, tendencia mensual, alertas y Top 15.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

from analytics import build_sku_summary, classify_skus, weekly_sales, weekly_sales_by_sku
from helpers import (
    fmt_money, fmt_pct, fmt_date,
    suggest_action, dl_excel_btn, plotly_theme, theme_palette, MESES_ES,
)


def render_resumen(
    sales_global: pd.DataFrame,
    stock_global: pd.DataFrame,
    sales_full: pd.DataFrame,      # ventas completas sin filtros para detalle semanal
    is_dark: bool,
    max_sales_date: pd.Timestamp,
    min_sales_date: pd.Timestamp,
) -> None:
    """Renderiza la pestaña Resumen Ejecutivo."""

    p = theme_palette(is_dark)
    TEXT_MAIN = p["TEXT_MAIN"]
    ACCENT    = p["ACCENT"]
    CARD_BG   = p["CARD_BG"]
    BORDER    = p["BORDER"]

    st.subheader("Resumen Ejecutivo")

    exec_period = st.selectbox(
        "Período de análisis",
        ["Últimas 4 semanas", "Últimas 8 semanas", "Últimas 12 semanas", "Todo el período"],
        key="exec_period",
    )
    offsets = {
        "Últimas 4 semanas": pd.Timedelta(weeks=4),
        "Últimas 8 semanas": pd.Timedelta(weeks=8),
        "Últimas 12 semanas": pd.Timedelta(weeks=12),
    }
    e_start = max_sales_date - offsets.get(exec_period, pd.Timedelta(0))
    if exec_period == "Todo el período":
        e_start = min_sales_date
    e_start = max(e_start, min_sales_date)
    st.info(f"Mostrando ventas desde {e_start.strftime('%d-%m-%Y')} hasta {max_sales_date.strftime('%d-%m-%Y')}")

    sales_e = sales_global[(sales_global["Fecha"] >= e_start) & (sales_global["Fecha"] <= max_sales_date)]
    sku_e   = classify_skus(build_sku_summary(sales_global, stock_global, e_start, max_sales_date))

    # ── KPIs ──
    venta_e      = sales_e["Venta Total Bruta"].sum()
    margen_e     = sales_e["Margen"].sum() if "Margen" in sales_e.columns else venta_e
    sku_activos  = sales_e["SKU"].nunique()
    sku_con_stock = sku_e[sku_e["Cantidad Disponible"] > 0]["SKU"].nunique()
    stock_val    = sku_e["valor_stock_disponible"].sum()

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Venta del período", fmt_money(venta_e))
    c2.metric("Margen estimado",   fmt_money(margen_e))
    c3.metric("SKUs vendidos",     f"{sku_activos:,}".replace(",", "."))
    c4.metric("SKUs con stock",    f"{sku_con_stock:,}".replace(",", "."))
    c5.metric("Stock valorizado",  fmt_money(stock_val))

    dead_n = len(sku_e[sku_e["alerta"] == "Producto muerto con stock"])
    sin_n  = len(sku_e[sku_e["alerta"] == "Demanda histórica sin stock"])
    qb_n   = len(sku_e[sku_e["alerta"] == "Quiebre crítico"])
    cc1, cc2, cc3 = st.columns(3)
    cc1.metric("Stock sin ventas", dead_n, help="Historial completo")
    cc2.metric("Demanda sin stock", sin_n)
    cc3.metric("Quiebre crítico",   qb_n)

    # ── Evolución semanal ──
    st.subheader("Evolución semanal en el período")
    weekly_e = weekly_sales(sales_e)
    if not weekly_e.empty:
        weekly_e["Label"] = weekly_e.apply(
            lambda r: f"S{int(r['Semana'])} ({int(r['Año'])})", axis=1
        )
        fig_week = go.Figure()
        fig_week.add_trace(go.Bar(
            x=weekly_e["Label"], y=weekly_e["venta"],
            name="Venta ($)", marker_color=ACCENT,
            text=[fmt_money(v) for v in weekly_e["venta"]],
            textposition="outside",
            textfont=dict(size=10, color=TEXT_MAIN),
        ))
        fig_week.add_trace(go.Scatter(
            x=weekly_e["Label"], y=weekly_e["unidades"],
            name="Unidades", yaxis="y2",
            mode="lines+markers",
            line=dict(color="#F59E0B", width=2),
            marker=dict(size=5),
        ))
        fig_week.update_layout(**plotly_theme(is_dark))
        fig_week.update_layout(
            yaxis=dict(title="Venta Total ($)"),
            yaxis2=dict(title="Unidades", overlaying="y", side="right"),
            xaxis=dict(title="Semana"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig_week, use_container_width=True, height=480)

        # Detalle por semana
        semana_opts = weekly_e.apply(
            lambda r: (int(r["Año"]), int(r["Semana"]), r["Label"]), axis=1
        ).tolist()
        semana_labels = [s[2] for s in semana_opts]
        sel_label = st.selectbox(
            "Seleccionar semana para ver detalle de productos",
            semana_labels, key="sel_semana_exec",
        )
        sel_anio, sel_sem, _ = semana_opts[semana_labels.index(sel_label)]

        det = weekly_sales_by_sku(sales_full, sel_anio, sel_sem)
        if not det.empty:
            venta_total_sem = det["Venta"].sum()
            unidades_sem    = det["Unidades"].sum()
            margen_sem      = det["Margen"].sum()
            skus_sem        = len(det)

            stock_map = stock_global[["SKU", "Cantidad Disponible"]].drop_duplicates("SKU")
            det = det.merge(stock_map, on="SKU", how="left")
            det["Cantidad Disponible"] = det["Cantidad Disponible"].fillna(0).astype(int)
            det = det.sort_values("Venta", ascending=False).reset_index(drop=True)
            det.insert(0, "Ranking", range(1, len(det) + 1))

            st.markdown(
                f"""
                <div style="background:{CARD_BG};border:1px solid {BORDER};border-left:5px solid {ACCENT};
                            border-radius:6px;padding:12px 18px;margin-top:12px;margin-bottom:12px;">
                    <strong style="color:{ACCENT};font-size:1.1em;">
                        Detalle de ventas — {sel_label}
                    </strong>
                </div>
                """,
                unsafe_allow_html=True,
            )

            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Venta total",        fmt_money(venta_total_sem))
            k2.metric("Unidades vendidas",  f"{unidades_sem:,.0f}".replace(",", "."))
            k3.metric("Margen estimado",    fmt_money(margen_sem))
            k4.metric("SKUs vendidos",      f"{skus_sem:,}".replace(",", "."))

            cols_show = ["Ranking","SKU","Producto","Venta","Unidades","Margen","Cantidad Disponible"]
            ren_map  = {
                "Producto":             "Producto",
                "Venta":                "Venta",
                "Unidades":             "Unidades",
                "Margen":               "Margen estimado",
                "Cantidad Disponible":  "Stock disponible",
            }
            det_show = det[cols_show].rename(columns=ren_map).copy()
            det_show["Venta"]          = det_show["Venta"].apply(fmt_money)
            det_show["Margen estimado"] = det_show["Margen estimado"].apply(fmt_money)
            st.dataframe(det_show, hide_index=True, width="stretch")

            dl_excel_btn(det, f"detalle_semanal_{sel_anio}_{sel_sem}.xlsx",
                          sheet_name="Semana", label="Exportar detalle semanal a Excel")
        else:
            st.info("Sin ventas en esa semana con los filtros actuales.")
    else:
        st.info("No hay datos semanales para este período.")

    # ── Tendencia mensual ──
    st.subheader("Tendencia mensual de ventas")
    sales_m = sales_global[(sales_global["Fecha"] >= e_start) & (sales_global["Fecha"] <= max_sales_date)].copy()
    sales_m["Periodo"] = sales_m["Fecha"].dt.to_period("M")
    mes_actual = pd.Timestamp.now().to_period("M")

    monthly_grp = (
        sales_m.groupby("Periodo", as_index=False)
        .agg(
            venta=("Venta Total Bruta", "sum"),
            unidades=("Cantidad", "sum"),
            margen=("Margen", "sum") if "Margen" in sales_m.columns else ("Venta Total Bruta", "sum"),
            sku_activos=("SKU", "nunique"),
        )
        .sort_values("Periodo")
    )

    def periodo_label(p_obj):
        nombre = MESES_ES.get(p_obj.month, str(p_obj.month))
        lbl = f"{nombre} {p_obj.year}"
        return lbl + " (parcial)" if p_obj == mes_actual else lbl

    monthly_grp["Mes_Label"] = monthly_grp["Periodo"].apply(periodo_label)
    monthly_grp["Ticket promedio"] = np.where(
        monthly_grp["sku_activos"] > 0,
        monthly_grp["venta"] / monthly_grp["sku_activos"], 0,
    )

    if not monthly_grp.empty:
        fig_month = go.Figure()
        fig_month.add_trace(go.Scatter(
            x=monthly_grp["Mes_Label"], y=monthly_grp["venta"],
            mode="lines+markers+text",
            name="Venta mensual",
            line=dict(color=ACCENT, width=2),
            marker=dict(size=7, color=ACCENT),
            text=[fmt_money(v) for v in monthly_grp["venta"]],
            textposition="top center",
            textfont=dict(size=10, color=TEXT_MAIN),
        ))
        fig_month.update_layout(**plotly_theme(is_dark))
        fig_month.update_layout(
            xaxis=dict(title="Mes", tickangle=-30),
            yaxis=dict(title="Venta Total ($)"),
        )
        st.plotly_chart(fig_month, use_container_width=True)

        m_show = monthly_grp[["Mes_Label","venta","unidades","margen","sku_activos","Ticket promedio"]].rename(columns={
            "Mes_Label":"Mes","venta":"Venta","unidades":"Unidades","margen":"Margen",
            "sku_activos":"SKU activos","Ticket promedio":"Ticket promedio ($)",
        }).copy()
        m_show["Venta"]  = m_show["Venta"].apply(fmt_money)
        m_show["Margen"] = m_show["Margen"].apply(fmt_money)
        m_show["Ticket promedio ($)"] = m_show["Ticket promedio ($)"].apply(fmt_money)
        st.dataframe(m_show, hide_index=True, width="stretch")
        dl_excel_btn(m_show, "tendencia_mensual.xlsx", "Mensual")
    else:
        st.info("No hay datos mensuales suficientes.")

    # ── Alertas operacionales ──
    st.subheader("Distribución de alertas operacionales")
    alert_counts = sku_e["alerta"].value_counts().reset_index()
    alert_counts.columns = ["Alerta", "Cantidad"]
    if not alert_counts.empty:
        fig_alert = go.Figure(go.Bar(
            x=alert_counts["Alerta"],
            y=alert_counts["Cantidad"],
            marker_color=ACCENT,
            text=alert_counts["Cantidad"],
            textposition="outside",
            textfont=dict(color=TEXT_MAIN),
        ))
        fig_alert.update_layout(**plotly_theme(is_dark))
        fig_alert.update_xaxes(title_text="Alerta")
        fig_alert.update_yaxes(title_text="SKUs")
        st.plotly_chart(fig_alert, use_container_width=True)

        alerta_sel = st.selectbox(
            "Seleccionar alerta para ver productos",
            ["(ninguna)"] + list(alert_counts["Alerta"]),
            key="alerta_sel_exec",
        )
        if alerta_sel != "(ninguna)":
            a_df = sku_e[sku_e["alerta"] == alerta_sel].copy()
            a_df["Acción sugerida"] = a_df["dias_desde_ultima_venta"].apply(suggest_action)
            a_df = a_df.sort_values("venta_6m", ascending=False).reset_index(drop=True)
            a_df.insert(0, "Ranking", range(1, len(a_df) + 1))
            a_out = a_df[["Ranking","SKU","Producto","alerta","Cantidad Disponible",
                           "venta_6m","fecha_ultima_venta","dias_desde_ultima_venta","Acción sugerida"]].rename(columns={
                "alerta":"Alerta", "Cantidad Disponible":"Stock disponible", "venta_6m":"Venta acumulada",
                "fecha_ultima_venta":"Última venta", "dias_desde_ultima_venta":"Días sin venta",
            })
            a_out["Venta acumulada"] = a_out["Venta acumulada"].apply(fmt_money)
            a_out["Última venta"]    = a_out["Última venta"].apply(fmt_date)
            st.dataframe(a_out, hide_index=True, width="stretch")
            dl_excel_btn(a_out, f"alerta_{alerta_sel.replace(' ','_')}.xlsx", "Alerta")

    # ── Top 15 productos ──
    st.subheader("Top 15 productos por venta en el período")
    top15 = sku_e.sort_values("venta_6m", ascending=False).head(15)
    if not top15.empty:
        top_chart = top15.sort_values("venta_6m")
        fig_top = go.Figure(go.Bar(
            x=top_chart["venta_6m"],
            y=top_chart["Producto"],
            orientation="h",
            marker_color=ACCENT,
            text=[fmt_money(v) for v in top_chart["venta_6m"]],
            textposition="inside",
            textfont=dict(size=10, color="#FFFFFF"),
        ))
        fig_top.update_layout(**plotly_theme(is_dark))
        fig_top.update_xaxes(title_text="Venta ($)")
        fig_top.update_yaxes(title_text="")
        st.plotly_chart(fig_top, use_container_width=True)

        t15 = top15.reset_index(drop=True)
        t15.insert(0, "Ranking", range(1, len(t15) + 1))
        t15_out = t15[["Ranking","SKU","Producto","venta_6m","unidades_6m","margen_6m","Cantidad Disponible"]].rename(columns={
            "venta_6m":"Venta","unidades_6m":"Unidades","margen_6m":"Margen",
            "Cantidad Disponible":"Stock disponible",
        })
        t15_out["Venta"]  = t15_out["Venta"].apply(fmt_money)
        t15_out["Margen"] = t15_out["Margen"].apply(fmt_money)
        st.dataframe(t15_out, hide_index=True, width="stretch")
        dl_excel_btn(t15_out, "top15_productos.xlsx", "Top 15")

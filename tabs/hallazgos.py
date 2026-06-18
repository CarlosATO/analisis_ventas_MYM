"""
tabs/hallazgos.py — Pestaña "Hallazgos Ejecutivos"
6 hallazgos interactivos con tarjeta + expander + tabla + exportación Excel.
"""

import streamlit as st
import pandas as pd
import numpy as np

from analytics import build_sku_summary, classify_skus, pareto_analysis
from helpers import (
    fmt_money, fmt_pct, fmt_date,
    suggest_action, suggest_stockout_action, suggest_quiebre_action,
    dl_excel_btn, theme_palette,
)


def _finding_card(title: str, explanation: str, priority: str,
                  action: str, is_dark: bool, scope: str) -> None:
    """Renderiza una tarjeta de hallazgo ejecutivo con borde de color según prioridad."""
    priority_map = {
        "Alta": "Hallazgo crítico",
        "Media": "Hallazgo relevante",
        "Baja": "Hallazgo informativo",
    }
    display_priority = priority_map.get(priority, priority)
    colors = {
        "Hallazgo crítico":    {"border": "#DC2626", "bg": "#FEF2F2", "text": "#991B1B",
                                 "dark_bg": "#3B0F0F", "dark_text": "#FCA5A5"},
        "Hallazgo relevante":  {"border": "#D97706", "bg": "#FFFBEB", "text": "#92400E",
                                 "dark_bg": "#3B2A0A", "dark_text": "#FCD34D"},
        "Hallazgo informativo":{"border": "#2563EB", "bg": "#EFF6FF", "text": "#1E40AF",
                                 "dark_bg": "#0F1E40", "dark_text": "#93C5FD"},
    }
    c = colors.get(display_priority, colors["Hallazgo informativo"])
    p = theme_palette(is_dark)
    bg         = c["dark_bg"]   if is_dark else c["bg"]
    txt        = c["dark_text"] if is_dark else c["text"]
    border     = c["border"]
    scope_bg   = "#334155"      if is_dark else "#E2E8F0"
    scope_txt  = "#F8FAFC"      if is_dark else "#1E293B"
    body_txt   = p["TEXT_MAIN"]
    action_txt = p["TEXT_SEC"]

    st.markdown(
        f"""
        <div style="border-left:5px solid {border};background:{bg};padding:14px 18px;
                    border-radius:6px;margin-bottom:4px;box-shadow:0 1px 4px rgba(0,0,0,0.08);">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
                <strong style="font-size:1.05em;color:{txt};">{title}</strong>
                <div style="display:flex;gap:6px;align-items:center;">
                    <span style="background:{scope_bg};color:{scope_txt};padding:2px 8px;
                                 border-radius:4px;font-size:0.72em;font-weight:600;">
                        Ámbito: {scope}
                    </span>
                    <span style="background:{border};color:#fff;padding:2px 10px;
                                 border-radius:12px;font-size:0.78em;font-weight:700;">
                        {display_priority}
                    </span>
                </div>
            </div>
            <p style="margin:4px 0;font-size:0.93em;color:{body_txt};">{explanation}</p>
            <div style="margin-top:6px;font-size:0.87em;font-style:italic;color:{action_txt};">
                <strong>Acción sugerida:</strong> {action}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_hallazgos(
    sales_global: pd.DataFrame,
    stock_global: pd.DataFrame,
    is_dark: bool,
    min_sales_filter: float,
    max_sales_date: pd.Timestamp,
    min_sales_date: pd.Timestamp,
) -> None:
    """Renderiza la pestaña completa de Hallazgos Ejecutivos."""

    st.subheader("Hallazgos Ejecutivos")

    findings_period = st.selectbox(
        "Período para hallazgos operacionales",
        ["Últimas 4 semanas", "Últimas 8 semanas", "Últimas 12 semanas", "Todo el período"],
        key="findings_period",
    )
    offsets = {
        "Últimas 4 semanas": pd.Timedelta(weeks=4),
        "Últimas 8 semanas": pd.Timedelta(weeks=8),
        "Últimas 12 semanas": pd.Timedelta(weeks=12),
    }
    f_start = max_sales_date - offsets.get(findings_period, pd.Timedelta(0))
    if findings_period == "Todo el período":
        f_start = min_sales_date
    f_start = max(f_start, min_sales_date)

    st.info(f"Mostrando ventas desde {f_start.strftime('%d-%m-%Y')} hasta {max_sales_date.strftime('%d-%m-%Y')}")

    sku_f   = classify_skus(build_sku_summary(sales_global, stock_global, f_start, max_sales_date))
    sales_f = sales_global[(sales_global["Fecha"] >= f_start) & (sales_global["Fecha"] <= max_sales_date)]

    muertos_f   = sku_f[sku_f["alerta"] == "Producto muerto con stock"]
    sin_stock_f = sku_f[sku_f["alerta"] == "Demanda histórica sin stock"]
    quiebre_f   = sku_f[sku_f["alerta"] == "Quiebre crítico"]
    pareto_f    = pareto_analysis(sku_f)
    sku_80_f    = pareto_f[pareto_f["pct_acumulado"] <= 0.80]
    total_sku_f = pareto_f["SKU"].nunique()

    fall_f = sku_f[
        (sku_f["venta_prev_60d"] >= min_sales_filter) &
        (sku_f["venta_prev_60d"] > 0) &
        (sku_f["diferencia_venta_periodo"] < 0)
    ].sort_values("diferencia_venta_periodo")

    growth_f = sku_f[
        (sku_f["venta_prev_60d"] >= min_sales_filter) &
        (sku_f["venta_prev_60d"] > 0) &
        (sku_f["diferencia_venta_periodo"] > 0)
    ].sort_values("diferencia_venta_periodo", ascending=False)

    # ── H1: Stock sin ventas ──
    num_dead = len(muertos_f)
    val_dead = muertos_f["valor_stock_disponible"].sum()
    _finding_card(
        "Productos con stock sin ventas",
        f"{num_dead} productos tienen stock disponible pero no registran ventas en el período. "
        f"Capital inmovilizado estimado: {fmt_money(val_dead)}.",
        "Alta", "Revisar liquidación, promoción o descuento.", is_dark, "Historial completo",
    )
    with st.expander("Ver productos — Stock sin ventas"):
        if not muertos_f.empty:
            t = muertos_f.copy()
            t["Acción sugerida"] = t["dias_desde_ultima_venta"].apply(suggest_action)
            t["Subestado"] = np.where(t["tuvo_demanda_historica"],
                                      "Tuvo demanda, hoy inmovilizado", "Sin demanda histórica relevante")
            t = t.sort_values("valor_stock_disponible", ascending=False).reset_index(drop=True)
            t.insert(0, "Ranking", range(1, len(t) + 1))
            out = t[["Ranking","SKU","Producto","Subestado","Cantidad Disponible",
                      "valor_stock_disponible","fecha_ultima_venta","dias_desde_ultima_venta","Acción sugerida"]].rename(columns={
                "Cantidad Disponible":"Stock disponible", "valor_stock_disponible":"Valor estimado del stock",
                "fecha_ultima_venta":"Última venta",     "dias_desde_ultima_venta":"Días sin venta",
            })
            out["Valor estimado del stock"] = out["Valor estimado del stock"].apply(fmt_money)
            out["Última venta"] = out["Última venta"].apply(fmt_date)
            st.dataframe(out, hide_index=True, width="stretch")
            dl_excel_btn(out, "h1_stock_sin_ventas.xlsx", "Stock sin ventas")
        else:
            st.info("No se encontraron productos con stock sin ventas.")

    # ── H2: Demanda histórica sin stock ──
    num_sin = len(sin_stock_f)
    val_pot = (sin_stock_f["venta_promedio_mientras_vendia"] * sin_stock_f["dias_desde_ultima_venta"]).sum()
    _finding_card(
        "Productos con demanda histórica pero sin stock",
        f"{num_sin} productos tenían demanda pero hoy no tienen stock disponible. "
        f"Venta potencial no capturada estimada: {fmt_money(val_pot)}.",
        "Alta", "Revisar compra o confirmar si el producto fue descontinuado.", is_dark, "Historial completo",
    )
    with st.expander("Ver productos — Demanda histórica sin stock"):
        if not sin_stock_f.empty:
            t = sin_stock_f.copy()
            t["Venta potencial no capturada"] = t["venta_promedio_mientras_vendia"] * t["dias_desde_ultima_venta"]
            t["Acción sugerida"] = t["dias_desde_ultima_venta"].apply(suggest_stockout_action)
            t = t.sort_values("venta_historica_total", ascending=False).reset_index(drop=True)
            t.insert(0, "Ranking", range(1, len(t) + 1))
            out = t[["Ranking","SKU","Producto","venta_historica_total","fecha_ultima_venta",
                      "dias_desde_ultima_venta","Venta potencial no capturada","Acción sugerida"]].rename(columns={
                "venta_historica_total":"Venta histórica", "fecha_ultima_venta":"Última venta",
                "dias_desde_ultima_venta":"Días sin venta",
            })
            out["Venta histórica"] = out["Venta histórica"].apply(fmt_money)
            out["Venta potencial no capturada"] = out["Venta potencial no capturada"].apply(fmt_money)
            out["Última venta"] = out["Última venta"].apply(fmt_date)
            st.dataframe(out, hide_index=True, width="stretch")
            dl_excel_btn(out, "h2_demanda_sin_stock.xlsx", "Demanda sin stock")
        else:
            st.info("No se encontraron productos en esta situación.")

    # ── H3: Quiebre crítico ──
    _finding_card(
        "Riesgo crítico de quiebre de stock",
        f"{len(quiebre_f)} productos tienen stock que cubre menos de 7 días según su rotación reciente.",
        "Alta", "Realizar pedido de reposición urgente.", is_dark, "Período seleccionado",
    )
    with st.expander("Ver productos — Quiebre crítico"):
        if not quiebre_f.empty:
            t = quiebre_f.sort_values("dias_cobertura").reset_index(drop=True)
            t.insert(0, "Ranking", range(1, len(t) + 1))
            t["Acción sugerida"] = t["dias_cobertura"].apply(suggest_quiebre_action)
            out = t[["Ranking","SKU","Producto","dias_cobertura","Cantidad Disponible",
                      "unidades_promedio_diaria_30d","Acción sugerida"]].rename(columns={
                "dias_cobertura":"Días de cobertura", "Cantidad Disponible":"Stock disponible",
                "unidades_promedio_diaria_30d":"Demanda diaria promedio",
            })
            out["Días de cobertura"] = out["Días de cobertura"].apply(
                lambda x: f"{x:.1f}" if pd.notna(x) else "-")
            out["Demanda diaria promedio"] = out["Demanda diaria promedio"].apply(lambda x: f"{x:.2f}")
            st.dataframe(out, hide_index=True, width="stretch")
            dl_excel_btn(out, "h3_quiebre_critico.xlsx", "Quiebre crítico")
        else:
            st.info("No se detectaron quiebres críticos.")

    # ── H4: Concentración Pareto ──
    sku_80_n = sku_80_f["SKU"].nunique()
    pct_sku  = sku_80_n / total_sku_f if total_sku_f > 0 else 0
    _finding_card(
        "Concentración de ventas (Efecto Pareto)",
        f"{sku_80_n} de {total_sku_f} SKUs ({fmt_pct(pct_sku)}) explican el 80% de la venta en este período.",
        "Media", "Asegurar stock permanente de este grupo y negociar mejores condiciones con proveedores.",
        is_dark, "Período seleccionado",
    )
    with st.expander("Ver productos — Core Pareto 80%"):
        if not sku_80_f.empty:
            t = sku_80_f.reset_index(drop=True)
            t.insert(0, "Ranking", range(1, len(t) + 1))
            out = t[["Ranking","SKU","Producto / Servicio","venta_6m","pct_acumulado"]].rename(columns={
                "Producto / Servicio":"Producto", "venta_6m":"Venta del período", "pct_acumulado":"% Acumulado",
            })
            out["Venta del período"] = out["Venta del período"].apply(fmt_money)
            out["% Acumulado"] = out["% Acumulado"].apply(fmt_pct)
            st.dataframe(out, hide_index=True, width="stretch")
            dl_excel_btn(out, "h4_pareto_core.xlsx", "Core Pareto")
        else:
            st.info("Sin datos de Pareto.")

    # ── H5: Mayor caída ──
    caida_max = fmt_money(fall_f["diferencia_venta_periodo"].min()) if not fall_f.empty else "$0"
    _finding_card(
        "Productos con mayor caída de ventas",
        f"{len(fall_f)} productos redujeron ventas vs el período anterior. "
        f"El de mayor caída perdió {caida_max}.",
        "Media", "Investigar causa de caída: precio, disponibilidad, competencia.",
        is_dark, "Período seleccionado",
    )
    with st.expander("Ver productos — Mayor caída"):
        if not fall_f.empty:
            t = fall_f.head(20).reset_index(drop=True)
            t.insert(0, "Ranking", range(1, len(t) + 1))
            out = t[["Ranking","SKU","Producto","venta_6m","venta_prev_60d",
                      "diferencia_venta_periodo","variacion_60d_pct"]].rename(columns={
                "venta_6m":"Venta período actual",    "venta_prev_60d":"Venta período anterior",
                "diferencia_venta_periodo":"Diferencia ($)", "variacion_60d_pct":"Variación %",
            })
            for c in ["Venta período actual","Venta período anterior","Diferencia ($)"]:
                out[c] = out[c].apply(fmt_money)
            out["Variación %"] = out["Variación %"].apply(fmt_pct)
            st.dataframe(out, hide_index=True, width="stretch")
            dl_excel_btn(out, "h5_caida_ventas.xlsx", "Caída de ventas")
        else:
            st.info("No se detectaron caídas significativas.")

    # ── H6: Mayor crecimiento ──
    crec_max = fmt_money(growth_f["diferencia_venta_periodo"].max()) if not growth_f.empty else "$0"
    _finding_card(
        "Productos con mayor crecimiento",
        f"{len(growth_f)} productos aumentaron ventas vs el período anterior. "
        f"El de mayor crecimiento sumó {crec_max} adicionales.",
        "Baja", "Evaluar incremento de stock y replicar estrategia comercial.",
        is_dark, "Período seleccionado",
    )
    with st.expander("Ver productos — Mayor crecimiento"):
        if not growth_f.empty:
            t = growth_f.head(20).reset_index(drop=True)
            t.insert(0, "Ranking", range(1, len(t) + 1))
            out = t[["Ranking","SKU","Producto","venta_6m","venta_prev_60d",
                      "diferencia_venta_periodo","variacion_60d_pct"]].rename(columns={
                "venta_6m":"Venta período actual",    "venta_prev_60d":"Venta período anterior",
                "diferencia_venta_periodo":"Diferencia ($)", "variacion_60d_pct":"Variación %",
            })
            for c in ["Venta período actual","Venta período anterior","Diferencia ($)"]:
                out[c] = out[c].apply(fmt_money)
            out["Variación %"] = out["Variación %"].apply(fmt_pct)
            st.dataframe(out, hide_index=True, width="stretch")
            dl_excel_btn(out, "h6_crecimiento_ventas.xlsx", "Crecimiento")
        else:
            st.info("No se detectaron crecimientos significativos.")

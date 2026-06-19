"""
helpers.py — Funciones de formato, exportación Excel y estilos Plotly.
Importar desde cualquier módulo de tab o desde app.py.
"""

import io
import pandas as pd
import streamlit as st

# ── Constante de meses en español ──
MESES_ES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}


# ── Formato de valores ──

def fmt_money(value) -> str:
    """$1.234.567 — pesos chilenos sin decimales."""
    try:
        return f"${value:,.0f}".replace(",", ".")
    except Exception:
        return "$0"


def fmt_pct(value) -> str:
    """12.3%"""
    try:
        return f"{value:.1%}"
    except Exception:
        return "-"


def fmt_date(value) -> str:
    """DD-MM-YYYY"""
    try:
        return pd.to_datetime(value).strftime("%d-%m-%Y")
    except Exception:
        return "-"


# ── Acciones sugeridas ──

def suggest_action(days) -> str:
    """Acción para stock inmovilizado según días sin venta."""
    if pd.isna(days):
        return "Liquidar o promocionar"
    if days > 90:
        return "Liquidar o promocionar"
    elif 45 <= days <= 90:
        return "Revisar precio o exhibición"
    else:
        return "Monitorear"


def suggest_stockout_action(days) -> str:
    """Acción para productos sin stock con demanda histórica."""
    if pd.isna(days) or days > 90:
        return "Validar si fue descontinuado. Si no, priorizar reposición piloto."
    else:
        return "Revisar reposición en la próxima compra semanal/quincenal."


def suggest_quiebre_action(dias_cob) -> str:
    """Acción según días de cobertura estimada."""
    if pd.isna(dias_cob) or dias_cob < 7:
        return "Pedido urgente — quiebre inminente"
    elif dias_cob < 15:
        return "Reponer en la próxima compra"
    else:
        return "Monitorear cobertura"


# ── Exportación Excel ──

def export_to_excel(df: pd.DataFrame, sheet_name: str = "Datos") -> bytes:
    """
    Exporta un DataFrame a Excel con formato ejecutivo.
    Retorna bytes listos para st.download_button.
    - Encabezados en negrita con fondo azul oscuro
    - Autofiltro activado
    - Primera fila congelada
    - Ancho de columna automático (máx 40 chars)
    """
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
        wb = writer.book
        ws = writer.sheets[sheet_name]

        header_fmt = wb.add_format({
            "bold": True,
            "bg_color": "#1E3A5F",
            "font_color": "#FFFFFF",
            "border": 1,
            "text_wrap": True,
            "valign": "vcenter",
        })
        for col_num, col_name in enumerate(df.columns):
            ws.write(0, col_num, str(col_name), header_fmt)
            try:
                col_series = df.iloc[:, col_num].fillna("").astype(str)
                max_data_len = col_series.map(len).max() if len(df) > 0 else 10
                header_len = len(str(col_name))
                col_width = min(max(header_len, max_data_len) + 2, 40)
                ws.set_column(col_num, col_num, col_width)
            except Exception:
                ws.set_column(col_num, col_num, 15)

        ws.autofilter(0, 0, 0, len(df.columns) - 1)
        ws.freeze_panes(1, 0)

    return output.getvalue()


def dl_excel_btn(
    df: pd.DataFrame,
    filename: str,
    sheet_name: str = "Datos",
    label: str = "Exportar Excel",
) -> None:
    """
    Renderiza un botón de descarga de Excel reutilizable.
    Usa una key única basada en filename + sheet_name para evitar duplicados.
    """
    data = export_to_excel(df, sheet_name)
    st.download_button(
        label=label,
        data=data,
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=f"dl_{filename}_{sheet_name}",
    )


# ── Plotly ──

def plotly_theme(is_dark: bool) -> dict:
    """
    Diccionario de parámetros de layout para fig.update_layout(**plotly_theme(is_dark)).
    Garantiza fondo transparente, colores de fuente y grilla correctos para cada tema.
    """
    font_color = "#F8FAFC" if is_dark else "#0F172A"
    grid_color = "#334155" if is_dark else "#E2E8F0"
    bg = "rgba(0,0,0,0)"
    return dict(
        template="plotly_dark" if is_dark else "plotly_white",
        paper_bgcolor=bg,
        plot_bgcolor=bg,
        font=dict(color=font_color, family="Inter, sans-serif"),
        xaxis=dict(gridcolor=grid_color, linecolor=grid_color, zerolinecolor=grid_color),
        yaxis=dict(gridcolor=grid_color, linecolor=grid_color, zerolinecolor=grid_color),
        margin=dict(l=10, r=10, t=65, b=10),
    )


# ── Paleta de colores por tema (para HTML inline) ──

def theme_palette(is_dark: bool) -> dict:
    """
    Retorna dict con colores del tema para usar en HTML inline de st.markdown().
    Uso: p = theme_palette(is_dark); p['TEXT_MAIN'], p['CARD_BG'], etc.
    """
    if is_dark:
        return {
            "APP_BG":   "#0F172A",
            "CARD_BG":  "#1E293B",
            "TEXT_MAIN":"#F8FAFC",
            "TEXT_SEC": "#CBD5E1",
            "BORDER":   "#334155",
            "ACCENT":   "#38BDF8",
            "SB_BG":    "#1E293B",
        }
    else:
        return {
            "APP_BG":   "#F8FAFC",
            "CARD_BG":  "#FFFFFF",
            "TEXT_MAIN":"#0F172A",
            "TEXT_SEC": "#334155",
            "BORDER":   "#CBD5E1",
            "ACCENT":   "#0284C7",
            "SB_BG":    "#F1F5F9",
        }

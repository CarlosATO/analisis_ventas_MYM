import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

from data_loader import load_files
from analytics import (
    build_sku_summary,
    classify_skus,
    pareto_analysis,
    monthly_sales,
    weekly_sales,
    export_findings,
)

st.set_page_config(
    page_title="Análisis de Ventas MYM",
    page_icon="📊",
    layout="wide"
)

# Utility formatting functions
def money(value):
    try:
        return f"${value:,.0f}".replace(",", ".")
    except Exception:
        return "$0"

def pct(value):
    try:
        return f"{value:.1%}"
    except Exception:
        return "-"

def suggest_action(days):
    if pd.isna(days):
        return "Liquidar o promocionar"
    if days > 90:
        return "Liquidar o promocionar"
    elif 45 <= days <= 90:
        return "Revisar precio o exhibición"
    else:
        return "Monitorear"

def suggest_stockout_action(days):
    if pd.isna(days) or days > 90:
        return "Validar si fue descontinuado. Si no lo fue, priorizar reposición piloto."
    else:
        return "Revisar reposición en la próxima compra semanal/quincenal."

# Finding Card component without emojis
def finding_card(title, explanation, priority, action, is_dark, scope):
    priority_map = {
        "Alta": "Hallazgo crítico",
        "Media": "Hallazgo relevante",
        "Baja": "Hallazgo informativo"
    }
    display_priority = priority_map.get(priority, priority)
    
    colors = {
        "Hallazgo crítico": {"border": "#DC2626", "bg": "#FEF2F2", "text": "#991B1B", "dark_bg": "#451A03", "dark_text": "#FEF3C7"},
        "Hallazgo relevante": {"border": "#D97706", "bg": "#FFFBEB", "text": "#92400E", "dark_bg": "#452A1A", "dark_text": "#FCD34D"},
        "Hallazgo informativo": {"border": "#2563EB", "bg": "#EFF6FF", "text": "#1E40AF", "dark_bg": "#1A2E40", "dark_text": "#93C5FD"}
    }
    
    c = colors.get(display_priority, colors["Hallazgo informativo"])
    bg_color = c["dark_bg"] if is_dark else c["bg"]
    text_color = c["dark_text"] if is_dark else c["text"]
    border_color = c["border"]
    
    st.markdown(
        f"""
        <div style="
            border-left: 5px solid {border_color};
            background-color: {bg_color};
            padding: 15px;
            border-radius: 4px;
            margin-bottom: 15px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        ">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;">
                <strong style="font-size: 1.1em; color: {text_color};">{title}</strong>
                <div style="display: flex; gap: 8px; align-items: center;">
                    <span style="
                        background-color: {'#334155' if is_dark else '#E2E8F0'};
                        color: {'#F8FAFC' if is_dark else '#1E293B'};
                        padding: 2px 8px;
                        border-radius: 4px;
                        font-size: 0.75em;
                        font-weight: bold;
                    ">Ámbito: {scope}</span>
                    <span style="
                        background-color: {border_color};
                        color: white;
                        padding: 2px 12px;
                        border-radius: 12px;
                        font-size: 0.8em;
                        font-weight: bold;
                    ">{display_priority}</span>
                </div>
            </div>
            <p style="margin: 5px 0; font-size: 0.95em; color: {'#F8FAFC' if is_dark else '#1E293B'};">{explanation}</p>
            <div style="margin-top: 8px; font-size: 0.9em; font-style: italic; color: {'#E2E8F0' if is_dark else '#475569'};">
                <strong>Acción sugerida:</strong> {action}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

# 1. Initialize session state variables
if "data_loaded" not in st.session_state:
    st.session_state.data_loaded = False
    st.session_state.sales = None
    st.session_state.stock = None
    st.session_state.sku_df = None
    st.session_state.pareto = None
    st.session_state.monthly = None
    st.session_state.diagnostics = None
    st.session_state.cross_metrics = None
    st.session_state.fecha_hora_carga = None
    st.session_state.loaded_sales_name = None
    st.session_state.loaded_sales_size = None
    st.session_state.loaded_stock_name = None
    st.session_state.loaded_stock_size = None

# Safe check to prevent KeyError from stale session states across runs
if st.session_state.data_loaded:
    required_cols = ["Categoría", "Marca", "Línea / Tema de producto"]
    if st.session_state.sku_df is None or not all(c in st.session_state.sku_df.columns for c in required_cols):
        st.session_state.clear()
        st.session_state.data_loaded = False
        st.rerun()


# Sidebar file upload configuration at the very top of the sidebar
st.sidebar.subheader("Carga de archivos")

sales_file = st.sidebar.file_uploader(
    "Carga archivo de ventas",
    type=["xlsx", "xls"],
    help="Debe contener las ventas con columnas: SKU, Producto / Servicio, Fecha y Hora Venta, Venta Total Bruta, Cantidad"
)

stock_file = st.sidebar.file_uploader(
    "Carga archivo de stock",
    type=["xlsx", "xls"],
    help="Debe contener el stock con columnas: SKU, Cantidad Disponible (o Disponible / Stock)"
)

# Checking warnings and status for button enabling
sales_file_ok = sales_file is not None
stock_file_ok = stock_file is not None

if not sales_file_ok:
    st.sidebar.warning("Falta archivo de ventas")
if not stock_file_ok:
    st.sidebar.warning("Falta archivo de stock")

files_changed = False
if sales_file_ok and stock_file_ok:
    if not st.session_state.data_loaded:
        st.sidebar.info("Archivos seleccionados. Presione Cargar datos para iniciar el análisis.")
    else:
        # Detect if uploaded files are different from the ones in state
        if (st.session_state.loaded_sales_name != sales_file.name or
            st.session_state.loaded_sales_size != sales_file.size or
            st.session_state.loaded_stock_name != stock_file.name or
            st.session_state.loaded_stock_size != stock_file.size):
            files_changed = True
            st.sidebar.warning("Los archivos seleccionados cambiaron. Presione Cargar datos para actualizar el análisis.")

# Render "Cargar datos" button immediately under warnings
button_disabled = not (sales_file_ok and stock_file_ok)
button_text = "Cargar datos" if not button_disabled else "Seleccione ambos archivos para habilitar la carga."

if st.sidebar.button(
    button_text, 
    type="primary", 
    disabled=button_disabled,
    key="btn_cargar_datos"
):
    with st.spinner("Procesando ventas y stock. Esto puede tardar unos segundos."):
        try:
            sales_df, stock_df, diagnostics = load_files(sales_file, stock_file)
            
            # Initial full range calculations
            min_sales_date = sales_df["Fecha"].min()
            max_sales_date = sales_df["Fecha"].max()
            
            sku_df = build_sku_summary(sales_df, stock_df, min_sales_date, max_sales_date)
            sku_df = classify_skus(sku_df)
            
            # Cross metrics calculations
            sales_skus = set(sales_df["SKU"].unique())
            stock_skus = set(stock_df["SKU"].unique())
            cross_metrics = {
                "skus_sold": len(sales_skus),
                "skus_stock": len(stock_skus),
                "skus_crossed": len(sales_skus & stock_skus),
                "skus_sold_no_stock": len(sales_skus - stock_skus),
                "skus_stock_no_sales": len(stock_skus - sales_skus),
            }
            
            # Save to state
            st.session_state.sales = sales_df
            st.session_state.stock = stock_df
            st.session_state.sku_df = sku_df
            st.session_state.diagnostics = diagnostics
            st.session_state.cross_metrics = cross_metrics
            st.session_state.fecha_hora_carga = pd.Timestamp.now().strftime("%d-%m-%Y %H:%M:%S")
            st.session_state.loaded_sales_name = sales_file.name
            st.session_state.loaded_sales_size = sales_file.size
            st.session_state.loaded_stock_name = stock_file.name
            st.session_state.loaded_stock_size = stock_file.size
            st.session_state.data_loaded = True
            
            st.sidebar.success("Análisis listo para revisar")
            st.rerun()
        except Exception as e:
            st.sidebar.error(f"Error al procesar los archivos: {str(e)}")

# Clear session state button (only if loaded)
if st.session_state.data_loaded:
    if st.sidebar.button("Limpiar análisis"):
        st.session_state.clear()
        st.rerun()

st.sidebar.markdown("---")

# Theme Selector (Always visible, now below loading elements)
st.sidebar.subheader("Configuración visual")
theme_option = st.sidebar.selectbox("Tema visual", ["Claro", "Oscuro"], index=0)
is_dark = (theme_option == "Oscuro")

# Font and Style Injection (always injected)
st.markdown(
    """
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        html, body, [class*="css"], .stApp {
            font-family: 'Inter', sans-serif !important;
        }
    </style>
    """,
    unsafe_allow_html=True
)

if is_dark:
    st.markdown(
        """
        <style>
            /* 1. Header transparency */
            header[data-testid="stHeader"], [data-testid="stHeader"] {
                background-color: transparent !important;
                background: transparent !important;
            }
            
            /* 2. Main App Background */
            div[data-testid="stAppViewContainer"], .stApp {
                background-color: #0F172A !important;
                color: #F8FAFC !important;
            }
            
            /* 3. Sidebar Background */
            div[data-testid="stSidebar"], section[data-testid="stSidebar"] {
                background-color: #1E293B !important;
                border-right: 1px solid #334155 !important;
            }
            
            /* 4. Global text overrides in dark mode */
            .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6, 
            .stApp p, .stApp span, .stApp label, .stApp li, .stApp small {
                color: #F8FAFC !important;
            }
            section[data-testid="stSidebar"] h1,
            section[data-testid="stSidebar"] h2,
            section[data-testid="stSidebar"] h3,
            section[data-testid="stSidebar"] h4,
            section[data-testid="stSidebar"] h5,
            section[data-testid="stSidebar"] h6,
            section[data-testid="stSidebar"] p, 
            section[data-testid="stSidebar"] span, 
            section[data-testid="stSidebar"] label,
            section[data-testid="stSidebar"] li,
            section[data-testid="stSidebar"] small {
                color: #F8FAFC !important;
            }
            
            /* Secondary texts in dark mode */
            p, span, small, .stApp p, .stApp span, .stApp small {
                color: #CBD5E1 !important;
            }
            
            /* 5. Compact sidebar elements and global spacing */
            section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] {
                gap: 8px !important;
            }
            section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div {
                padding-bottom: 2px !important;
                padding-top: 2px !important;
                margin-bottom: 2px !important;
            }
            
            /* Sidebar header division */
            section[data-testid="stSidebar"] h2 {
                font-size: 1.15rem !important;
                font-weight: 700 !important;
                border-bottom: 2px solid #334155 !important;
                padding-bottom: 4px !important;
                margin-top: 15px !important;
                margin-bottom: 10px !important;
                color: #F8FAFC !important;
            }
            
            /* 6. Inputs styling in dark mode */
            div[data-testid="stSelectbox"] [data-baseweb="select"], 
            div[data-testid="stMultiSelect"] [data-baseweb="select"],
            [data-baseweb="select"] {
                background-color: #111827 !important;
                border: 1px solid #334155 !important;
                border-radius: 6px !important;
            }
            div[data-testid="stSelectbox"] [data-baseweb="select"] *,
            div[data-testid="stMultiSelect"] [data-baseweb="select"] *,
            [data-baseweb="select"] * {
                background-color: transparent !important;
                color: #F8FAFC !important;
            }
            input[type="number"], input[type="text"], input, textarea, select {
                background-color: #111827 !important;
                color: #F8FAFC !important;
                border: 1px solid #334155 !important;
                border-radius: 6px !important;
            }
            
            /* Dropdown popups / Portals in dark mode */
            div[role="listbox"], div[data-baseweb="menu"], ul[role="listbox"], [data-baseweb="popover"] {
                background-color: #111827 !important;
                border: 1px solid #334155 !important;
                color: #F8FAFC !important;
            }
            div[role="listbox"] *, div[data-baseweb="menu"] *, ul[role="listbox"] *, [data-baseweb="popover"] * {
                background-color: #111827 !important;
                color: #F8FAFC !important;
            }
            div[role="listbox"] li:hover, div[data-baseweb="menu"] li:hover, ul[role="listbox"] li:hover {
                background-color: #2563EB !important;
                color: #F8FAFC !important;
            }
            
            /* File Uploader styling in dark mode */
            div[data-testid="stFileUploader"] {
                background-color: #1E293B !important;
                border: 2px dashed #334155 !important;
                border-radius: 8px !important;
                padding: 4px !important;
                margin: 2px 0px !important;
            }
            div[data-testid="stFileUploaderDropzone"] {
                background-color: #111827 !important;
                border: 1px dashed #334155 !important;
                border-radius: 6px !important;
                padding: 8px 10px !important;
            }
            div[data-testid="stFileUploaderDropzone"] * {
                color: #CBD5E1 !important;
            }
            div[data-testid="stFileUploaderDropzone"] button {
                background-color: #2563EB !important;
                color: #F8FAFC !important;
                border: 1px solid #334155 !important;
            }
            div[data-testid="stFileUploaderDropzone"] button:hover {
                background-color: #1D4ED8 !important;
            }
            div[data-testid="stFileUploader"] [data-testid="stUploadedFile"] {
                background-color: #111827 !important;
                border: 1px solid #334155 !important;
                border-radius: 6px !important;
                color: #F8FAFC !important;
                margin-top: 6px !important;
                padding: 6px !important;
            }
            div[data-testid="stFileUploader"] [data-testid="stUploadedFile"] * {
                background-color: transparent !important;
                color: #F8FAFC !important;
            }
            
            /* Buttons in dark mode */
            button, .stButton button {
                background-color: #1E293B !important;
                color: #F8FAFC !important;
                border: 1px solid #334155 !important;
                border-radius: 6px !important;
            }
            button:hover, .stButton button:hover {
                background-color: #334155 !important;
                border-color: #475569 !important;
            }
            button[kind="primary"], .stButton button[kind="primary"] {
                background-color: #2563EB !important;
                color: #F8FAFC !important;
                border: none !important;
            }
            button[kind="primary"]:hover, .stButton button[kind="primary"]:hover {
                background-color: #1D4ED8 !important;
                color: #F8FAFC !important;
            }
            button[kind="primary"]:disabled, .stButton button[kind="primary"]:disabled {
                background-color: #1E293B !important;
                color: #64748B !important;
                border: 1px solid #334155 !important;
                cursor: not-allowed !important;
            }
            
            /* Alerts/Notifications in dark mode */
            div[data-testid="stAlert"] {
                border-radius: 6px !important;
                padding: 6px 12px !important;
                margin: 2px 0px !important;
            }
            div[data-testid="stAlert"] * {
                color: inherit !important;
            }
            /* Warning (background #451A03, border #F59E0B, text #FEF3C7) */
            div[data-testid="stAlert"]:has(svg[data-testid*="Warning"]),
            div[data-testid="stAlert"]:has(svg[aria-label*="warning"]),
            div[data-testid="stAlert"]:has(svg[data-testid="stNotificationWarningIcon"]),
            div[data-testid="stAlert"]:has(svg[data-testid="stIconWarning"]) {
                background-color: #451A03 !important;
                border: 1px solid #F59E0B !important;
                color: #FEF3C7 !important;
            }
            /* Error (background #450A0A, border #EF4444, text #FEE2E2) */
            div[data-testid="stAlert"]:has(svg[data-testid*="Error"]),
            div[data-testid="stAlert"]:has(svg[aria-label*="error"]),
            div[data-testid="stAlert"]:has(svg[data-testid="stNotificationErrorIcon"]),
            div[data-testid="stAlert"]:has(svg[data-testid="stIconError"]) {
                background-color: #450A0A !important;
                border: 1px solid #EF4444 !important;
                color: #FEE2E2 !important;
            }
            /* Success (background #052E16, border #22C55E, text #DCFCE7) */
            div[data-testid="stAlert"]:has(svg[data-testid*="Success"]),
            div[data-testid="stAlert"]:has(svg[aria-label*="success"]),
            div[data-testid="stAlert"]:has(svg[data-testid="stNotificationSuccessIcon"]),
            div[data-testid="stAlert"]:has(svg[data-testid="stIconSuccess"]) {
                background-color: #052E16 !important;
                border: 1px solid #22C55E !important;
                color: #DCFCE7 !important;
            }
            /* Info (background #0F1E36, border #2563EB, text #93C5FD) */
            div[data-testid="stAlert"]:has(svg[data-testid*="Info"]),
            div[data-testid="stAlert"]:has(svg[aria-label*="info"]),
            div[data-testid="stAlert"]:has(svg[data-testid="stNotificationInfoIcon"]),
            div[data-testid="stAlert"]:has(svg[data-testid="stIconInfo"]) {
                background-color: #0F1E36 !important;
                border: 1px solid #2563EB !important;
                color: #93C5FD !important;
            }
            
            /* Expander and Tabs */
            div[data-testid="stExpander"] {
                background-color: #1E293B !important;
                border: 1px solid #334155 !important;
            }
            .stTabs [data-baseweb="tab"] {
                color: #94A3B8 !important;
            }
            .stTabs [aria-selected="true"] {
                color: #38BDF8 !important;
                border-bottom-color: #38BDF8 !important;
            }
            
            /* KPIs Metrics */
            div[data-testid="stMetricValue"] {
                color: #38BDF8 !important;
            }
            div[data-testid="stMetricLabel"] {
                color: #94A3B8 !important;
            }
            
            /* Dataframes & Tables */
            .dataframe {
                color: #F8FAFC !important;
                background-color: #1E293B !important;
            }
            table {
                background-color: #111827 !important;
                color: #F8FAFC !important;
                border: 1px solid #334155 !important;
            }
            th {
                background-color: #1E293B !important;
                color: #F8FAFC !important;
                border: 1px solid #334155 !important;
            }
            td {
                border: 1px solid #334155 !important;
                color: #CBD5E1 !important;
            }
        </style>
        """,
        unsafe_allow_html=True
    )
else: # Light Mode (High Contrast text and background)
    st.markdown(
        """
        <style>
            /* 1. Main App Background */
            div[data-testid="stAppViewContainer"], .stApp {
                background-color: #FFFFFF !important;
                color: #0F172A !important;
            }
            p, li, span, label, h1, h2, h3, h4, h5, h6, th, td, small {
                color: #0F172A !important;
            }
            
            /* 2. Sidebar background and text */
            section[data-testid="stSidebar"] {
                background-color: #F8FAFC !important;
                border-right: 1px solid #E2E8F0 !important;
            }
            section[data-testid="stSidebar"] h1,
            section[data-testid="stSidebar"] h2,
            section[data-testid="stSidebar"] h3,
            section[data-testid="stSidebar"] h4,
            section[data-testid="stSidebar"] h5,
            section[data-testid="stSidebar"] h6,
            section[data-testid="stSidebar"] p, 
            section[data-testid="stSidebar"] span, 
            section[data-testid="stSidebar"] label,
            section[data-testid="stSidebar"] li,
            section[data-testid="stSidebar"] small {
                color: #0F172A !important;
                font-weight: 500 !important;
            }
            
            /* Sidebar header division in light mode */
            section[data-testid="stSidebar"] h2 {
                font-size: 1.15rem !important;
                font-weight: 700 !important;
                border-bottom: 2px solid #E2E8F0 !important;
                padding-bottom: 4px !important;
                margin-top: 15px !important;
                margin-bottom: 10px !important;
                color: #0F172A !important;
            }
            
            /* Compact sidebar elements and global spacing */
            section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] {
                gap: 8px !important;
            }
            section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div {
                padding-bottom: 2px !important;
                padding-top: 2px !important;
                margin-bottom: 2px !important;
            }
            
            /* 3. Inputs in light mode */
            div[data-testid="stSelectbox"] [data-baseweb="select"], 
            div[data-testid="stMultiSelect"] [data-baseweb="select"],
            [data-baseweb="select"] {
                background-color: #FFFFFF !important;
                border: 1px solid #CBD5E1 !important;
                border-radius: 4px !important;
            }
            div[data-testid="stSelectbox"] [data-baseweb="select"] *,
            div[data-testid="stMultiSelect"] [data-baseweb="select"] *,
            [data-baseweb="select"] * {
                color: #0F172A !important;
            }
            input[type="number"], input[type="text"], input, textarea, select {
                background-color: #FFFFFF !important;
                color: #0F172A !important;
                border: 1px solid #CBD5E1 !important;
            }
            
            /* Portal options in light mode */
            [data-baseweb="menu"], [data-baseweb="popover"], div[role="listbox"], ul[role="listbox"] {
                background-color: #FFFFFF !important;
                border: 1px solid #CBD5E1 !important;
                color: #0F172A !important;
            }
            [data-baseweb="menu"] *, [data-baseweb="popover"] *, div[role="listbox"] *, ul[role="listbox"] * {
                background-color: #FFFFFF !important;
                color: #0F172A !important;
            }
            [data-baseweb="menu"] li:hover, div[role="listbox"] li:hover, ul[role="listbox"] li:hover {
                background-color: #E2E8F0 !important;
                color: #0F172A !important;
            }
            
            /* 4. Buttons in light mode */
            button, .stButton button {
                background-color: #FFFFFF !important;
                color: #0F172A !important;
                border: 1px solid #CBD5E1 !important;
            }
            button:hover, .stButton button:hover {
                background-color: #F1F5F9 !important;
                color: #0F172A !important;
            }
            button[kind="primary"], .stButton button[kind="primary"] {
                background-color: #2563EB !important;
                color: #FFFFFF !important;
                border: none !important;
            }
            button[kind="primary"]:hover, .stButton button[kind="primary"]:hover {
                background-color: #1D4ED8 !important;
                color: #FFFFFF !important;
            }
            button[kind="primary"]:disabled, .stButton button[kind="primary"]:disabled {
                background-color: #F1F5F9 !important;
                color: #94A3B8 !important;
                border: 1px solid #E2E8F0 !important;
                cursor: not-allowed !important;
            }
            
            /* 5. File Uploader in light mode */
            div[data-testid="stFileUploader"] {
                padding: 4px !important;
                margin: 2px 0px !important;
            }
            div[data-testid="stFileUploaderDropzone"] {
                background-color: #FFFFFF !important;
                border: 1px dashed #CBD5E1 !important;
                color: #0F172A !important;
                padding: 6px 8px !important;
            }
            div[data-testid="stFileUploaderDropzone"] * {
                color: #0F172A !important;
            }
            
            /* 6. Alerts/Notifications in light mode */
            div[data-testid="stAlert"] {
                border-radius: 6px !important;
                padding: 6px 12px !important;
                margin: 2px 0px !important;
            }
            div[data-testid="stAlert"] * {
                color: inherit !important;
            }
            /* Warning (background #FEF3C7, border #D97706, text #78350F) */
            div[data-testid="stAlert"]:has(svg[data-testid*="Warning"]),
            div[data-testid="stAlert"]:has(svg[aria-label*="warning"]),
            div[data-testid="stAlert"]:has(svg[data-testid="stNotificationWarningIcon"]),
            div[data-testid="stAlert"]:has(svg[data-testid="stIconWarning"]) {
                background-color: #FEF3C7 !important;
                border: 1px solid #D97706 !important;
                color: #78350F !important;
            }
            /* Error (background #FEE2E2, border #EF4444, text #991B1B) */
            div[data-testid="stAlert"]:has(svg[data-testid*="Error"]),
            div[data-testid="stAlert"]:has(svg[aria-label*="error"]),
            div[data-testid="stAlert"]:has(svg[data-testid="stNotificationErrorIcon"]),
            div[data-testid="stAlert"]:has(svg[data-testid="stIconError"]) {
                background-color: #FEE2E2 !important;
                border: 1px solid #EF4444 !important;
                color: #991B1B !important;
            }
            /* Success (background #DCFCE7, border #22C55E, text #14532D) */
            div[data-testid="stAlert"]:has(svg[data-testid*="Success"]),
            div[data-testid="stAlert"]:has(svg[aria-label*="success"]),
            div[data-testid="stAlert"]:has(svg[data-testid="stNotificationSuccessIcon"]),
            div[data-testid="stAlert"]:has(svg[data-testid="stIconSuccess"]) {
                background-color: #DCFCE7 !important;
                border: 1px solid #22C55E !important;
                color: #14532D !important;
            }
            /* Info (background #EFF6FF, border #3B82F6, text #1E3A8A) */
            div[data-testid="stAlert"]:has(svg[data-testid*="Info"]),
            div[data-testid="stAlert"]:has(svg[aria-label*="info"]),
            div[data-testid="stAlert"]:has(svg[data-testid="stNotificationInfoIcon"]),
            div[data-testid="stAlert"]:has(svg[data-testid="stIconInfo"]) {
                background-color: #EFF6FF !important;
                border: 1px solid #3B82F6 !important;
                color: #1E3A8A !important;
            }
            
            /* Expander and Tabs */
            div[data-testid="stExpander"] {
                background-color: #FFFFFF !important;
                border: 1px solid #E2E8F0 !important;
            }
            .stTabs [data-baseweb="tab"] {
                color: #475569 !important;
                font-weight: 500 !important;
            }
            .stTabs [aria-selected="true"] {
                color: #0284C7 !important;
                border-bottom-color: #0284C7 !important;
            }
            
            /* KPIs Metrics */
            div[data-testid="stMetricValue"] {
                color: #0284C7 !important;
                font-weight: 700 !important;
            }
            div[data-testid="stMetricLabel"] {
                color: #1E293B !important;
                font-weight: 600 !important;
            }
            
            /* Dataframes */
            .dataframe {
                color: #0F172A !important;
                background-color: #FFFFFF !important;
            }
        </style>
        """,
        unsafe_allow_html=True
    )

# Stop execution if data not loaded
if not st.session_state.data_loaded:
    st.title("Análisis Comercial de Ventas e Inventario MYM")
    st.caption("Carga los archivos de Ventas y de Stock en la barra lateral para iniciar el dashboard comercial.")
    st.info("Esperando carga de archivos (Ventas y Stock) en el panel lateral.")
    st.stop()

# 2. Global Filters (once data is loaded)
st.sidebar.markdown("---")
st.sidebar.subheader("Filtros globales")

categories = sorted([c for c in st.session_state.sku_df["Categoría"].unique() if pd.notna(c) and c != ""])
brands = sorted([b for b in st.session_state.sku_df["Marca"].unique() if pd.notna(b) and b != ""])
lines = sorted([l for l in st.session_state.sku_df["Línea / Tema de producto"].unique() if pd.notna(l) and l != ""])

cat_filter = st.sidebar.selectbox("Categoría", ["Todas"] + categories)
brand_filter = st.sidebar.selectbox("Marca", ["Todas"] + brands)
line_filter = st.sidebar.selectbox("Línea / Tema de producto", ["Todas"] + lines)

# 4. Filter datasets globally (non-destructive)
sales_global = st.session_state.sales.copy()
stock_global = st.session_state.stock.copy()
sku_df_global = st.session_state.sku_df.copy()

if cat_filter != "Todas":
    sku_df_global = sku_df_global[sku_df_global["Categoría"] == cat_filter]
    if "Tipo de Producto / Servicio" in sales_global.columns:
        sales_global = sales_global[sales_global["Tipo de Producto / Servicio"] == cat_filter]

if brand_filter != "Todas":
    sku_df_global = sku_df_global[sku_df_global["Marca"] == brand_filter]
    if "Marca" in sales_global.columns:
        sales_global = sales_global[sales_global["Marca"] == brand_filter]

if line_filter != "Todas":
    sku_df_global = sku_df_global[sku_df_global["Línea / Tema de producto"] == line_filter]
    if "Línea / Tema de producto" in sales_global.columns:
        sales_global = sales_global[sales_global["Línea / Tema de producto"] == line_filter]

# Main dashboard title
st.title("Análisis Comercial de Ventas e Inventario MYM")

# 5. "Estado del análisis" Card (Always on top)
min_date_val = st.session_state.sales["Fecha"].min()
max_date_val = st.session_state.sales["Fecha"].max()
total_loaded_sales = len(st.session_state.sales)
total_skus_sold = st.session_state.cross_metrics["skus_sold"]
total_skus_stock = st.session_state.cross_metrics["skus_stock"]
total_skus_crossed = st.session_state.cross_metrics["skus_crossed"]
stock_col_used = st.session_state.diagnostics["stock_col_origin"]
stock_col_type = st.session_state.diagnostics["stock_col_origin_type"]
fecha_carga = st.session_state.fecha_hora_carga

st.markdown(
    f"""
    <div style="
        background-color: {'#1E293B' if is_dark else '#F8FAFC'};
        border: 1px solid {'#334155' if is_dark else '#E2E8F0'};
        padding: 16px;
        border-radius: 6px;
        margin-bottom: 20px;
    ">
        <h3 style="margin-top:0; color: {'#38BDF8' if is_dark else '#0284C7'}; font-size: 1.1em; margin-bottom: 12px; font-weight: 600;">Estado del análisis</h3>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; font-size: 0.95em; color: {'#F8FAFC' if is_dark else '#0F172A'};">
            <div><strong>Fecha inicial de ventas:</strong> {min_date_val.strftime('%d-%m-%Y')}</div>
            <div><strong>Fecha final de ventas:</strong> {max_date_val.strftime('%d-%m-%Y')}</div>
            <div><strong>Registros de ventas cargados:</strong> {total_loaded_sales:,}</div>
            <div><strong>SKU vendidos:</strong> {total_skus_sold:,}</div>
            <div><strong>SKU con stock:</strong> {total_skus_stock:,}</div>
            <div><strong>SKU cruzados ventas-stock:</strong> {total_skus_crossed:,}</div>
            <div><strong>Columna usada como stock disponible real:</strong> <code>{stock_col_used}</code> ({stock_col_type})</div>
            <div><strong>Fecha y hora de carga:</strong> {fecha_carga}</div>
        </div>
    </div>
    """.replace(",", "."),
    unsafe_allow_html=True
)

# Render Diagnostic Report Expander in sidebar
with st.sidebar.expander("Reporte de Diagnóstico de Carga (SKU)", expanded=False):
    st.markdown(f"- **Ventas (Filas leídas):** {st.session_state.diagnostics['sales_rows']}")
    st.markdown(f"- **Stock (Filas leídas):** {st.session_state.diagnostics['stock_rows']}")
    st.markdown(f"- **Fila cabecera Ventas:** {st.session_state.diagnostics['sales_header_row']}")
    st.markdown(f"- **Fila cabecera Stock:** {st.session_state.diagnostics['stock_header_row']}")
    st.markdown(f"- **Columna de Stock usada:** `{st.session_state.diagnostics['stock_col_origin']}` ({st.session_state.diagnostics['stock_col_origin_type']})")
    st.markdown("---")
    st.markdown(f"- **SKUs únicos vendidos:** {st.session_state.cross_metrics['skus_sold']}")
    st.markdown(f"- **SKUs únicos con stock:** {st.session_state.cross_metrics['skus_stock']}")
    st.markdown(f"- **SKUs cruzados:** {st.session_state.cross_metrics['skus_crossed']}")
    st.markdown(f"- **SKUs vendidos sin stock:** {st.session_state.cross_metrics['skus_sold_no_stock']}")
    st.markdown(f"- **SKUs con stock sin ventas:** {st.session_state.cross_metrics['skus_stock_no_sales']}")

# Filter min sales for rankings
min_sales_filter = st.sidebar.number_input(
    "Venta mínima para rankings ($)",
    min_value=0,
    value=50000,
    step=10000,
    help="Omite productos con ventas insignificantes para evitar distorsiones por porcentajes extremos."
)

# Tabs definitions (no emojis)
tabs = st.tabs([
    "Hallazgos",
    "Resumen Ejecutivo",
    "Pareto 80/20",
    "Productos muertos con stock",
    "Demanda histórica sin stock",
    "Quiebres de stock",
    "Caídas y crecimiento",
    "Base de análisis"
])

max_sales_date = sales_global["Fecha"].max() if not sales_global.empty else pd.Timestamp.now()
min_sales_date = sales_global["Fecha"].min() if not sales_global.empty else pd.Timestamp.now()

# ----------------- TABS IMPLEMENTATIONS -----------------

# Tab 1: Hallazgos
with tabs[0]:
    st.subheader("Resumen de Hallazgos Ejecutivos")
    
    findings_period = st.selectbox(
        "Período para hallazgos operacionales",
        ["Últimas 4 semanas", "Últimas 8 semanas", "Últimas 12 semanas", "Todo el período"],
        key="findings_period"
    )
    
    if findings_period == "Últimas 4 semanas":
        start_date = max_sales_date - pd.Timedelta(weeks=4)
    elif findings_period == "Últimas 8 semanas":
        start_date = max_sales_date - pd.Timedelta(weeks=8)
    elif findings_period == "Últimas 12 semanas":
        start_date = max_sales_date - pd.Timedelta(weeks=12)
    else:
        start_date = min_sales_date
        
    start_date = max(start_date, min_sales_date)
    st.info(f"Mostrando ventas desde {start_date.strftime('%d-%m-%Y')} hasta {max_sales_date.strftime('%d-%m-%Y')}")
    
    # Recalculate local metrics
    sku_df_findings = build_sku_summary(sales_global, stock_global, start_date, max_sales_date)
    sku_df_findings = classify_skus(sku_df_findings)
    
    # Global filtered indicators
    muertos_stock = sku_df_findings[sku_df_findings["alerta"].eq("Producto muerto con stock")]
    demanda_sin_stock = sku_df_findings[sku_df_findings["alerta"].eq("Demanda histórica sin stock")]
    quiebre_critico = sku_df_findings[sku_df_findings["alerta"].eq("Quiebre crítico")]
    
    # 1.1 Muertos con stock inmovilizado
    num_dead = len(muertos_stock)
    val_dead = muertos_stock["valor_stock_disponible"].sum()
    finding_card(
        title="Productos Muertos con Stock Inmovilizado",
        explanation=f"Existen {num_dead} productos con stock disponible que no registran ventas recientes (más de 45 días). Esto representa un capital inmovilizado estimado de {money(val_dead)}.",
        priority="Alta",
        action="Revisar liquidación, promoción, descuento especial o devolución a proveedor.",
        is_dark=is_dark,
        scope="Historial completo"
    )
    
    # 1.2 Demanda histórica sin stock
    num_sin_stock = len(demanda_sin_stock)
    val_potencial_no_capturada = (demanda_sin_stock["venta_promedio_mientras_vendia"] * demanda_sin_stock["dias_desde_ultima_venta"]).sum()
    finding_card(
        title="Productos con demanda histórica, pero sin stock",
        explanation=f"Estos productos vendían anteriormente, pero hoy no tienen stock disponible. La caída de ventas podría deberse a falta de reposición, no necesariamente a baja demanda. Hay {num_sin_stock} productos en esta situación, con una venta potencial no capturada estimada en {money(val_potencial_no_capturada)}.",
        priority="Alta",
        action="Revisar compra o confirmar si el producto fue descontinuado.",
        is_dark=is_dark,
        scope="Historial completo"
    )
    
    # 1.3 Riesgo de quiebre crítico
    num_critical = len(quiebre_critico)
    finding_card(
        title="Riesgo Crítico de Quiebre de Stock",
        explanation=f"Se detectaron {num_critical} productos con un stock disponible actual que cubre menos de 7 días de venta, según su tasa de rotación en el período seleccionado.",
        priority="Alta",
        action="Realizar pedido de reposición urgente al proveedor para evitar quiebre de stock y pérdida de ventas.",
        is_dark=is_dark,
        scope="Período seleccionado"
    )
    
    # 1.4 Pareto
    pareto_findings = pareto_analysis(sku_df_findings)
    sku_80 = pareto_findings[pareto_findings["pct_acumulado"] <= 0.80]["SKU"].nunique()
    total_sku = pareto_findings["SKU"].nunique()
    finding_card(
        title="Concentración de Venta (Efecto Pareto)",
        explanation=f"El análisis de Pareto muestra que un grupo selecto de {sku_80} productos (de un total de {total_sku} SKUs vendidos) concentra aproximadamente el 80% de la venta en este período.",
        priority="Media",
        action="Asegurar el stock permanente de este grupo principal de productos y negociar mejores márgenes o condiciones comerciales con proveedores.",
        is_dark=is_dark,
        scope="Período seleccionado"
    )
    
    # 1.5 Desempeño General
    filtered_sales_findings = sales_global[(sales_global["Fecha"] >= start_date) & (sales_global["Fecha"] <= max_sales_date)]
    venta_total_findings = filtered_sales_findings["Venta Total Bruta"].sum()
    margen_total_findings = filtered_sales_findings["Margen"].sum() if "Margen" in filtered_sales_findings.columns else venta_total_findings
    finding_card(
        title="Desempeño General y Rentabilidad",
        explanation=f"Durante el período seleccionado, se alcanzó una facturación de {money(venta_total_findings)} con un margen de contribución estimado de {money(margen_total_findings)}.",
        priority="Baja",
        action="Analizar la tendencia semanal de ventas para monitorear el cumplimiento de metas comerciales.",
        is_dark=is_dark,
        scope="Período seleccionado"
    )

# Tab 2: Resumen Ejecutivo
with tabs[1]:
    st.subheader("Resumen Ejecutivo")
    
    exec_period = st.selectbox(
        "Período de análisis",
        ["Últimas 4 semanas", "Últimas 8 semanas", "Últimas 12 semanas", "Todo el período"],
        key="exec_period"
    )
    
    if exec_period == "Últimas 4 semanas":
        start_date = max_sales_date - pd.Timedelta(weeks=4)
    elif exec_period == "Últimas 8 semanas":
        start_date = max_sales_date - pd.Timedelta(weeks=8)
    elif exec_period == "Últimas 12 semanas":
        start_date = max_sales_date - pd.Timedelta(weeks=12)
    else:
        start_date = min_sales_date
        
    start_date = max(start_date, min_sales_date)
    st.info(f"Mostrando ventas desde {start_date.strftime('%d-%m-%Y')} hasta {max_sales_date.strftime('%d-%m-%Y')}")
    
    filtered_sales_local = sales_global[(sales_global["Fecha"] >= start_date) & (sales_global["Fecha"] <= max_sales_date)]
    sku_df_local = build_sku_summary(sales_global, stock_global, start_date, max_sales_date)
    sku_df_local = classify_skus(sku_df_local)
    
    # Executive KPIs
    venta_total = filtered_sales_local["Venta Total Bruta"].sum()
    margen_total = filtered_sales_local["Margen"].sum() if "Margen" in filtered_sales_local.columns else venta_total
    sku_activos = filtered_sales_local["SKU"].nunique()
    sku_stock = sku_df_local[sku_df_local["Cantidad Disponible"] > 0]["SKU"].nunique()
    stock_valorizado = sku_df_local["valor_stock_disponible"].sum()
    
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Venta del período", money(venta_total))
    col2.metric("Margen estimado", money(margen_total))
    col3.metric("SKUs vendidos", f"{sku_activos:,}".replace(",", "."))
    col4.metric("SKUs con stock", f"{sku_stock:,}".replace(",", "."))
    col5.metric("Stock valorizado", money(stock_valorizado))
    
    # Alertas agregadas
    muertos_stock_local = sku_df_local[sku_df_local["alerta"].eq("Producto muerto con stock")]
    demanda_sin_stock_local = sku_df_local[sku_df_local["alerta"].eq("Demanda histórica sin stock")]
    quiebre_critico_local = sku_df_local[sku_df_local["alerta"].eq("Quiebre crítico")]
    
    col_l1, col_l2, col_l3 = st.columns(3)
    col_l1.metric("Productos muertos con stock", len(muertos_stock_local), help="Evaluado con el historial completo")
    col_l2.metric("Demanda histórica sin stock", len(demanda_sin_stock_local), help="Productos sin stock que tenían demanda histórica")
    col_l3.metric("Quiebre crítico", len(quiebre_critico_local), help="Cobertura menor a 7 días en el período")
    
    # Weekly Chart
    st.subheader("Evolución semanal en el período")
    weekly_df = weekly_sales(filtered_sales_local)
    if not weekly_df.empty:
        weekly_df["Semana_Display"] = weekly_df.apply(lambda r: f"Semana {int(r['Semana'])} ({int(r['Año'])})", axis=1)
        fig_week = go.Figure()
        fig_week.add_trace(
            go.Bar(
                x=weekly_df["Semana_Display"],
                y=weekly_df["venta"],
                name="Venta Total ($)",
                marker_color="#38BDF8" if is_dark else "#0284C7"
            )
        )
        fig_week.add_trace(
            go.Scatter(
                x=weekly_df["Semana_Display"],
                y=weekly_df["unidades"],
                name="Unidades vendidas",
                yaxis="y2",
                line=dict(color="#F59E0B", width=3)
            )
        )
        fig_week.update_layout(
            yaxis=dict(title="Venta Total ($)"),
            yaxis2=dict(title="Unidades", overlaying="y", side="right"),
            xaxis=dict(title="Semana"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            template="plotly_dark" if is_dark else "plotly_white",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig_week, width="stretch")
    else:
        st.info("No hay suficientes semanas completas de datos para graficar la evolución.")
        
    # Monthly Chart
    st.subheader("Tendencia mensual de ventas")
    monthly_filtered = monthly_sales(filtered_sales_local)
    if not monthly_filtered.empty:
        fig_month = px.line(
            monthly_filtered,
            x="Mes",
            y="venta",
            markers=True,
            title="Venta mensual del período seleccionado"
        )
        fig_month.update_layout(
            yaxis_title="Venta Bruta ($)",
            xaxis_title="Mes",
            template="plotly_dark" if is_dark else "plotly_white",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig_month, width="stretch")
    else:
        st.info("No hay suficientes datos mensuales para graficar la tendencia.")
        
    # Alert Distribution Chart
    st.subheader("Alertas operacionales")
    alert_counts = sku_df_local["alerta"].value_counts().reset_index()
    alert_counts.columns = ["alerta", "cantidad"]
    fig_alert = px.bar(alert_counts, x="alerta", y="cantidad", title="Distribución de alertas por SKU")
    fig_alert.update_layout(
        xaxis_title="Alertas",
        yaxis_title="Cantidad de SKUs",
        template="plotly_dark" if is_dark else "plotly_white",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    st.plotly_chart(fig_alert, width="stretch")
    
    # Top 15 Products Chart
    st.subheader("Top 15 productos por venta")
    top15 = sku_df_local.sort_values("venta_6m", ascending=False).head(15)
    if not top15.empty:
        fig_top = px.bar(
            top15.sort_values("venta_6m"),
            x="venta_6m",
            y="Producto",
            orientation="h",
            title="Top 15 SKUs por venta acumulada en el período"
        )
        fig_top.update_layout(
            xaxis_title="Venta Acumulada ($)",
            yaxis_title="Producto",
            template="plotly_dark" if is_dark else "plotly_white",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig_top, width="stretch")

# Tab 3: Pareto 80/20
with tabs[2]:
    st.subheader("Análisis Pareto 80/20")
    
    pareto_period = st.selectbox(
        "Período para análisis de Pareto",
        ["Últimas 4 semanas", "Últimas 8 semanas", "Últimos 3 meses", "Todo el período"],
        key="pareto_period"
    )
    
    if pareto_period == "Últimas 4 semanas":
        start_date = max_sales_date - pd.Timedelta(weeks=4)
    elif pareto_period == "Últimas 8 semanas":
        start_date = max_sales_date - pd.Timedelta(weeks=8)
    elif pareto_period == "Últimos 3 meses":
        start_date = max_sales_date - pd.Timedelta(days=90)
    else:
        start_date = min_sales_date
        
    start_date = max(start_date, min_sales_date)
    st.info(f"Mostrando ventas desde {start_date.strftime('%d-%m-%Y')} hasta {max_sales_date.strftime('%d-%m-%Y')}")
    
    sku_df_pareto = build_sku_summary(sales_global, stock_global, start_date, max_sales_date)
    pareto_local = pareto_analysis(sku_df_pareto)
    
    if not pareto_local.empty:
        pareto_chart = pareto_local.head(15).copy()
        fig_pareto = go.Figure()
        fig_pareto.add_bar(
            x=pareto_chart["SKU"],
            y=pareto_chart["venta_6m"],
            name="Venta"
        )
        fig_pareto.add_trace(
            go.Scatter(
                x=pareto_chart["SKU"],
                y=pareto_chart["pct_acumulado"],
                name="% acumulado",
                yaxis="y2",
                mode="lines+markers"
            )
        )
        fig_pareto.update_layout(
            title="Pareto de ventas por SKU (Top 15)",
            yaxis=dict(title="Venta ($)"),
            yaxis2=dict(title="% acumulado", overlaying="y", side="right", tickformat=".0%"),
            xaxis=dict(title="SKU"),
            legend=dict(orientation="h"),
            template="plotly_dark" if is_dark else "plotly_white",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig_pareto, width="stretch")
        
        sku_80 = pareto_local[pareto_local["pct_acumulado"] <= 0.80]["SKU"].nunique()
        total_sku = pareto_local["SKU"].nunique()
        st.info(f"{sku_80} de {total_sku} SKU explican aproximadamente el 80% de la venta.")
        
        pareto_display = pareto_local.rename(columns={
            "venta_6m": "Venta acumulada",
            "unidades_6m": "Unidades vendidas",
            "margen_6m": "Margen estimado",
            "venta_acumulada": "Venta acumulada total",
            "pct_acumulado": "Porcentaje acumulado",
            "clasificacion_pareto": "Clasificación Pareto"
        })
        st.dataframe(pareto_display.head(100), width="stretch", hide_index=True)

# Tab 4: Productos muertos con stock
with tabs[3]:
    st.subheader("Productos muertos con stock disponible (Historial completo)")
    
    dead_period = st.selectbox(
        "Rango de inactividad para productos muertos",
        ["Historial completo", "Últimos 45 días", "Últimos 90 días", "Todo el período"],
        key="dead_period"
    )
    
    inactivity_days = 45
    start_date = min_sales_date
    
    if dead_period == "Últimos 45 días":
        inactivity_days = 45
        start_date = max_sales_date - pd.Timedelta(days=45)
    elif dead_period == "Últimos 90 días":
        inactivity_days = 90
        start_date = max_sales_date - pd.Timedelta(days=90)
    elif dead_period == "Todo el período":
        inactivity_days = 45
        start_date = min_sales_date
        
    start_date = max(start_date, min_sales_date)
    st.info(f"Mostrando ventas desde {start_date.strftime('%d-%m-%Y')} hasta {max_sales_date.strftime('%d-%m-%Y')}")
    
    sku_df_dead = build_sku_summary(sales_global, stock_global, start_date, max_sales_date)
    sku_df_dead = classify_skus(sku_df_dead)
    
    # Custom rule for custom inactivity filters
    if inactivity_days != 45:
        cond_muerto_custom = (
            (sku_df_dead["Cantidad Disponible"] > 0) &
            (sku_df_dead["dias_desde_ultima_venta"] >= inactivity_days) &
            (sku_df_dead["venta_6m"] == 0)
        )
        sku_df_dead["alerta"] = np.where(cond_muerto_custom, "Producto muerto con stock", sku_df_dead["alerta"])
        sku_df_dead["prioridad"] = np.where(cond_muerto_custom, "Alta", sku_df_dead["prioridad"])

    dead_local = sku_df_dead[sku_df_dead["alerta"] == "Producto muerto con stock"].copy()
    dead_local["Acción sugerida"] = dead_local["dias_desde_ultima_venta"].apply(suggest_action)
    dead_local["Subestado"] = np.where(
        dead_local["tuvo_demanda_historica"] == True,
        "Tuvo demanda, pero hoy mantiene stock sin vender",
        "Sin demanda histórica relevante"
    )
    dead_local = dead_local.sort_values("valor_stock_disponible", ascending=False)
    
    if not dead_local.empty:
        fig_dead = px.bar(
            dead_local.head(15).sort_values("valor_stock_disponible"),
            x="valor_stock_disponible",
            y="Producto",
            orientation="h",
            title="Top 15 productos muertos por valor de stock inmovilizado"
        )
        fig_dead.update_layout(
            xaxis_title="Valor de Stock ($)",
            yaxis_title="Producto",
            template="plotly_dark" if is_dark else "plotly_white",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig_dead, width="stretch")
        
        dead_display = dead_local[[
            "SKU",
            "Producto",
            "Subestado",
            "Cantidad Disponible",
            "valor_stock_disponible",
            "fecha_ultima_venta",
            "dias_desde_ultima_venta",
            "Acción sugerida"
        ]].rename(columns={
            "Cantidad Disponible": "Stock disponible",
            "valor_stock_disponible": "Valor estimado del stock",
            "fecha_ultima_venta": "Última venta",
            "dias_desde_ultima_venta": "Días sin venta"
        })
        st.dataframe(dead_display, width="stretch", hide_index=True)
    else:
        st.info("No se encontraron productos muertos en stock en esta selección.")

# Tab 5: Demanda histórica sin stock
with tabs[4]:
    st.subheader("Productos con demanda histórica sin stock (Historial completo)")
    
    no_stock_period = st.selectbox(
        "Período para demanda histórica sin stock",
        ["Historial completo", "Últimas 12 semanas", "Últimas 24 semanas", "Todo el período"],
        key="no_stock_period"
    )
    
    if no_stock_period == "Últimas 12 semanas":
        start_date = max_sales_date - pd.Timedelta(weeks=12)
    elif no_stock_period == "Últimas 24 semanas":
        start_date = max_sales_date - pd.Timedelta(weeks=24)
    else:
        start_date = min_sales_date
        
    start_date = max(start_date, min_sales_date)
    st.info(f"Mostrando ventas desde {start_date.strftime('%d-%m-%Y')} hasta {max_sales_date.strftime('%d-%m-%Y')}")
    
    sku_df_no_stock = build_sku_summary(sales_global, stock_global, start_date, max_sales_date)
    sku_df_no_stock = classify_skus(sku_df_no_stock)
    
    dem_sin_stock = sku_df_no_stock[sku_df_no_stock["alerta"] == "Demanda histórica sin stock"].copy()
    dem_sin_stock["Venta potencial no capturada"] = dem_sin_stock["venta_promedio_mientras_vendia"] * dem_sin_stock["dias_desde_ultima_venta"]
    dem_sin_stock["Acción sugerida"] = dem_sin_stock["dias_desde_ultima_venta"].apply(suggest_stockout_action)
    dem_sin_stock = dem_sin_stock.sort_values("venta_historica_total", ascending=False)
    
    if not dem_sin_stock.empty:
        fig_no_stock = px.bar(
            dem_sin_stock.head(15).sort_values("venta_historica_total"),
            x="venta_historica_total",
            y="Producto",
            orientation="h",
            title="Top 15 productos en quiebre ordenados por demanda histórica"
        )
        fig_no_stock.update_layout(
            xaxis_title="Venta Histórica Acumulada ($)",
            yaxis_title="Producto",
            template="plotly_dark" if is_dark else "plotly_white",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig_no_stock, width="stretch")
        
        dem_sin_stock_display = dem_sin_stock[[
            "SKU",
            "Producto",
            "venta_historica_total",
            "unidades_historicas_total",
            "fecha_ultima_venta",
            "dias_desde_ultima_venta",
            "Cantidad Disponible",
            "Venta potencial no capturada",
            "Acción sugerida"
        ]].rename(columns={
            "venta_historica_total": "Venta histórica",
            "unidades_historicas_total": "Unidades históricas",
            "fecha_ultima_venta": "Última venta",
            "dias_desde_ultima_venta": "Días sin venta",
            "Cantidad Disponible": "Stock disponible actual"
        })
        st.dataframe(dem_sin_stock_display, width="stretch", hide_index=True)
        st.caption("⚠️ **Venta potencial no capturada:** Estimación referencial basada en el ritmo de venta histórico mientras el producto estuvo activo.")
    else:
        st.info("No se encontraron productos con demanda histórica sin stock en este filtro.")

# Tab 6: Quiebres de stock
with tabs[5]:
    st.subheader("Riesgo de quiebre de stock")
    
    quiebre_period = st.selectbox(
        "Período para calcular demanda diaria y cobertura",
        ["Últimas 2 semanas", "Últimas 4 semanas", "Últimas 8 semanas"],
        index=1,
        key="quiebre_period"
    )
    
    if quiebre_period == "Últimas 2 semanas":
        start_date = max_sales_date - pd.Timedelta(weeks=2)
    elif quiebre_period == "Últimas 4 semanas":
        start_date = max_sales_date - pd.Timedelta(weeks=4)
    elif quiebre_period == "Últimas 8 semanas":
        start_date = max_sales_date - pd.Timedelta(weeks=8)
        
    start_date = max(start_date, min_sales_date)
    st.info(f"Mostrando ventas desde {start_date.strftime('%d-%m-%Y')} hasta {max_sales_date.strftime('%d-%m-%Y')}")
    
    sku_df_quiebre = build_sku_summary(sales_global, stock_global, start_date, max_sales_date)
    sku_df_quiebre = classify_skus(sku_df_quiebre)
    
    coverage_df = sku_df_quiebre[sku_df_quiebre["unidades_promedio_diaria_30d"] > 0].copy()
    if not coverage_df.empty:
        # Columna segura para size: nunca negativa, mínimo 1 para que el punto sea visible
        coverage_df["tamaño_visual"] = coverage_df["venta_6m"].abs().clip(lower=1)
        # Si todos los valores son 0 (sin venta en periodo), usar tamaño fijo
        if coverage_df["tamaño_visual"].sum() == 0:
            coverage_df["tamaño_visual"] = 1

        fig_cov = px.scatter(
            coverage_df,
            x="unidades_promedio_diaria_30d",
            y="Cantidad Disponible",
            size="tamaño_visual",
            hover_name="Producto",
            hover_data=["SKU", "dias_cobertura", "venta_6m", "alerta"],
            title="Stock disponible vs rotación diaria"
        )
        fig_cov.update_layout(
            xaxis_title="Unidades promedio diarias",
            yaxis_title="Cantidad disponible",
            template="plotly_dark" if is_dark else "plotly_white",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig_cov, width="stretch")
        
    st.subheader("SKUs críticos por cobertura")
    critical = sku_df_quiebre[sku_df_quiebre["alerta"].isin(["Quiebre crítico", "Riesgo de quiebre"])] \
        .sort_values(["alerta", "venta_6m"], ascending=[True, False])
        
    critical_display = critical[[
        "SKU", "Producto", "Cantidad Disponible",
        "unidades_promedio_diaria_30d", "dias_cobertura",
        "venta_6m", "Por recibir", "alerta", "prioridad"
    ]].rename(columns={
        "Cantidad Disponible": "Stock disponible",
        "unidades_promedio_diaria_30d": "Demanda diaria promedio",
        "dias_cobertura": "Días de cobertura",
        "venta_6m": "Venta acumulada",
        "alerta": "Alerta",
        "prioridad": "Prioridad"
    })
    st.dataframe(critical_display, width="stretch", hide_index=True)

# Tab 7: Caídas y crecimiento
with tabs[6]:
    st.subheader("Caídas y crecimiento de ventas")
    
    caida_period = st.selectbox(
        "Comparativa de períodos para caídas y crecimiento",
        [
            "Comparar últimas 4 semanas vs 4 semanas anteriores",
            "Comparar últimas 8 semanas vs 8 semanas anteriores",
            "Comparar últimos 3 meses vs 3 meses anteriores"
        ],
        index=1,
        key="caida_period"
    )
    
    if caida_period == "Comparar últimas 4 semanas vs 4 semanas anteriores":
        start_date = max_sales_date - pd.Timedelta(days=56)
    elif caida_period == "Comparar últimas 8 semanas vs 8 semanas anteriores":
        start_date = max_sales_date - pd.Timedelta(days=112)
    elif caida_period == "Comparar últimos 3 meses vs 3 meses anteriores":
        start_date = max_sales_date - pd.Timedelta(days=180)
        
    start_date = max(start_date, min_sales_date)
    st.info(f"Mostrando ventas desde {start_date.strftime('%d-%m-%Y')} hasta {max_sales_date.strftime('%d-%m-%Y')}")
    
    sku_df_caida = build_sku_summary(sales_global, stock_global, start_date, max_sales_date)
    sku_df_caida = classify_skus(sku_df_caida)
    
    # Caída
    st.subheader("Productos en caída (Ordenados por impacto económico)")
    fall = sku_df_caida[
        (sku_df_caida["venta_prev_60d"] > 0) &
        (sku_df_caida["venta_prev_60d"] >= min_sales_filter) &
        (sku_df_caida["diferencia_venta_periodo"] < 0)
    ].sort_values("diferencia_venta_periodo", ascending=True)
    
    if not fall.empty:
        fig_fall = px.bar(
            fall.head(15).sort_values("diferencia_venta_periodo", ascending=False),
            x="diferencia_venta_periodo",
            y="Producto",
            orientation="h",
            title="Top 15 caída de ventas (Impacto en $)"
        )
        fig_fall.update_layout(
            xaxis_title="Impacto económico ($)",
            yaxis_title="Producto",
            template="plotly_dark" if is_dark else "plotly_white",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig_fall, width="stretch")
        
    # Crecimiento
    st.subheader("Productos en crecimiento (Ordenados por impacto económico)")
    growth = sku_df_caida[
        (sku_df_caida["venta_prev_60d"] > 0) &
        (sku_df_caida["venta_6m"] >= min_sales_filter) &
        (sku_df_caida["diferencia_venta_periodo"] > 0)
    ].sort_values("diferencia_venta_periodo", ascending=False)
    
    if not growth.empty:
        fig_growth = px.bar(
            growth.head(15).sort_values("diferencia_venta_periodo"),
            x="diferencia_venta_periodo",
            y="Producto",
            orientation="h",
            title="Top 15 crecimiento de ventas (Impacto en $)"
        )
        fig_growth.update_layout(
            xaxis_title="Impacto económico ($)",
            yaxis_title="Producto",
            template="plotly_dark" if is_dark else "plotly_white",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig_growth, width="stretch")
        
    col_a, col_b = st.columns(2)
    columns_show = [
        "SKU", "Producto", "venta_6m", "venta_prev_60d",
        "diferencia_venta_periodo", "variacion_60d_pct"
    ]
    
    with col_a:
        st.write("Detalle de Caídas")
        fall_display = fall[columns_show].head(50).rename(columns={
            "venta_6m": "Venta del período",
            "venta_prev_60d": "Venta anterior",
            "diferencia_venta_periodo": "Impacto económico ($)",
            "variacion_60d_pct": "Variación porcentual"
        }).copy()
        if not fall_display.empty:
            fall_display.insert(0, "Ranking", range(1, len(fall_display) + 1))
        st.dataframe(fall_display, width="stretch", hide_index=True)
        
    with col_b:
        st.write("Detalle de Crecimientos")
        growth_display = growth[columns_show].head(50).rename(columns={
            "venta_6m": "Venta del período",
            "venta_prev_60d": "Venta anterior",
            "diferencia_venta_periodo": "Impacto económico ($)",
            "variacion_60d_pct": "Variación porcentual"
        }).copy()
        if not growth_display.empty:
            growth_display.insert(0, "Ranking", range(1, len(growth_display) + 1))
        st.dataframe(growth_display, width="stretch", hide_index=True)

# Tab 8: Base de análisis
with tabs[7]:
    st.subheader("Base analítica consolidada por SKU")
    
    base_display = sku_df_global.rename(columns={
        "venta_6m": "Venta del período",
        "unidades_6m": "Unidades vendidas",
        "margen_6m": "Margen estimado",
        "fecha_primera_venta": "Primera venta",
        "fecha_ultima_venta": "Última venta",
        "dias_desde_ultima_venta": "Días sin venta",
        "Cantidad Disponible": "Stock disponible",
        "unidades_promedio_diaria_30d": "Demanda diaria promedio",
        "dias_cobertura": "Días de cobertura",
        "valor_stock_disponible": "Valor del stock",
        "alerta": "Alerta",
        "prioridad": "Prioridad"
    }).sort_values("Venta del período", ascending=False)
    
    st.dataframe(base_display, width="stretch", hide_index=True)
    
    output_name = "hallazgos_mym.xlsx"
    if st.button("Exportar hallazgos a Excel"):
        export_findings(output_name, sku_df_global, pareto_analysis(sku_df_global), monthly_sales(sales_global))
        with open(output_name, "rb") as f:
            st.download_button(
                "Descargar Excel de hallazgos",
                data=f,
                file_name=output_name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

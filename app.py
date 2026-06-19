"""
app.py — Punto de entrada del Dashboard Comercial MYM
Responsabilidades ÚNICAS de este archivo:
  1. Configuración de página
  2. Session state
  3. Sidebar (carga, filtros, tema)
  4. Inyección de CSS
  5. Encabezado compacto
  6. Routing de tabs → llamadas a render_XXX()
"""

import streamlit as st
import pandas as pd

from data_loader import load_files
from analytics import build_sku_summary, classify_skus

from helpers import theme_palette
from styles import inject_css

from tabs.hallazgos       import render_hallazgos
from tabs.resumen         import render_resumen
from tabs.pareto          import render_pareto
from tabs.stock_sin_ventas import render_stock_sin_ventas
from tabs.demanda_sin_stock import render_demanda_sin_stock
from tabs.quiebres        import render_quiebres
from tabs.caidas          import render_caidas
from tabs.base            import render_base

# ─────────────────────────────────────────────
# CONFIGURACIÓN DE PÁGINA
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="Dashboard Comercial MYM",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────

if "data_loaded" not in st.session_state:
    st.session_state.data_loaded      = False
    st.session_state.sales            = None
    st.session_state.stock            = None
    st.session_state.sku_df           = None
    st.session_state.diagnostics      = None
    st.session_state.cross_metrics    = None
    st.session_state.fecha_hora_carga = None
    st.session_state.loaded_sales_name  = None
    st.session_state.loaded_sales_size  = None
    st.session_state.loaded_stock_name  = None
    st.session_state.loaded_stock_size  = None

# Limpia estado obsoleto si faltan columnas críticas
if st.session_state.data_loaded:
    required_cols = ["Categoría", "Marca", "Línea / Tema de producto"]
    if st.session_state.sku_df is None or not all(
        c in st.session_state.sku_df.columns for c in required_cols
    ):
        st.session_state.clear()
        st.session_state.data_loaded = False
        st.rerun()

# ─────────────────────────────────────────────
# SIDEBAR — CARGA DE ARCHIVOS
# ─────────────────────────────────────────────

st.sidebar.subheader("Carga de archivos")

sales_file = st.sidebar.file_uploader(
    "Archivo de ventas",
    type=["xlsx", "xls"],
    help="Columnas requeridas: SKU, Producto / Servicio, Fecha y Hora Venta, Venta Total Bruta, Cantidad",
)
stock_file = st.sidebar.file_uploader(
    "Archivo de stock",
    type=["xlsx", "xls"],
    help="Columnas requeridas: SKU, Disponible (o Stock)",
)

sales_ok = sales_file is not None
stock_ok = stock_file is not None

if not sales_ok:
    st.sidebar.warning("Falta archivo de ventas")
if not stock_ok:
    st.sidebar.warning("Falta archivo de stock")

if sales_ok and stock_ok:
    if not st.session_state.data_loaded:
        st.sidebar.info("Archivos seleccionados. Presione Cargar datos para iniciar el análisis.")
    else:
        if (
            st.session_state.loaded_sales_name != sales_file.name
            or st.session_state.loaded_sales_size != sales_file.size
            or st.session_state.loaded_stock_name != stock_file.name
            or st.session_state.loaded_stock_size != stock_file.size
        ):
            st.sidebar.warning(
                "Los archivos cambiaron. Presione Cargar datos para actualizar el análisis."
            )

btn_disabled = not (sales_ok and stock_ok)
btn_text     = "Cargar datos" if not btn_disabled else "Seleccione ambos archivos para habilitar la carga."

if st.sidebar.button(btn_text, type="primary", disabled=btn_disabled, key="btn_cargar_datos"):
    with st.spinner("Procesando ventas y stock. Esto puede tardar unos segundos."):
        try:
            sales_df, stock_df, diagnostics = load_files(sales_file, stock_file)
            min_date = sales_df["Fecha"].min()
            max_date = sales_df["Fecha"].max()
            sku_df   = classify_skus(build_sku_summary(sales_df, stock_df, min_date, max_date))
            skus_s   = set(sales_df["SKU"].unique())
            skus_t   = set(stock_df["SKU"].unique())
            st.session_state.sales            = sales_df
            st.session_state.stock            = stock_df
            st.session_state.sku_df           = sku_df
            st.session_state.diagnostics      = diagnostics
            st.session_state.cross_metrics    = {
                "skus_sold":          len(skus_s),
                "skus_stock":         len(skus_t),
                "skus_crossed":       len(skus_s & skus_t),
                "skus_sold_no_stock": len(skus_s - skus_t),
                "skus_stock_no_sales":len(skus_t - skus_s),
            }
            st.session_state.fecha_hora_carga  = pd.Timestamp.now().strftime("%d-%m-%Y %H:%M:%S")
            st.session_state.loaded_sales_name = sales_file.name
            st.session_state.loaded_sales_size = sales_file.size
            st.session_state.loaded_stock_name = stock_file.name
            st.session_state.loaded_stock_size = stock_file.size
            st.session_state.data_loaded = True
            st.sidebar.success("Análisis listo para revisar")
            st.rerun()
        except Exception as e:
            st.sidebar.error(f"Error al procesar los archivos: {str(e)}")

if st.session_state.data_loaded:
    if st.sidebar.button("Limpiar análisis", key="btn_limpiar"):
        st.session_state.clear()
        st.rerun()

st.sidebar.markdown("---")

# ─────────────────────────────────────────────
# SIDEBAR — FILTROS GLOBALES
# ─────────────────────────────────────────────

cat_filter   = "Todas"
brand_filter = "Todas"
line_filter  = "Todas"
min_sales_filter = 50000

if st.session_state.data_loaded:
    st.sidebar.subheader("Filtros globales")
    _sku = st.session_state.sku_df
    cats  = sorted([c for c in _sku["Categoría"].unique()              if pd.notna(c) and c != ""])
    brnds = sorted([b for b in _sku["Marca"].unique()                  if pd.notna(b) and b != ""])
    lns   = sorted([l for l in _sku["Línea / Tema de producto"].unique() if pd.notna(l) and l != ""])
    cat_filter   = st.sidebar.selectbox("Categoría", ["Todas"] + cats,  key="cat_filter")
    brand_filter = st.sidebar.selectbox("Marca",     ["Todas"] + brnds, key="brand_filter")
    line_filter  = st.sidebar.selectbox("Línea / Tema de producto", ["Todas"] + lns, key="line_filter")
    min_sales_filter = st.sidebar.number_input(
        "Venta mínima para rankings ($)",
        min_value=0, value=50000, step=10000,
        help="Filtra productos con ventas insignificantes en rankings.",
    )

st.sidebar.markdown("---")

# ─────────────────────────────────────────────
# SIDEBAR — TEMA VISUAL
# ─────────────────────────────────────────────

st.sidebar.subheader("Configuración visual")
theme_option = st.sidebar.selectbox("Tema visual", ["Claro", "Oscuro"], index=0, key="theme_sel")
is_dark = theme_option == "Oscuro"

# ─────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────

inject_css(is_dark)

# ─────────────────────────────────────────────
# LANDING (sin datos)
# ─────────────────────────────────────────────

p = theme_palette(is_dark)
TEXT_MAIN = p["TEXT_MAIN"]
TEXT_SEC  = p["TEXT_SEC"]
CARD_BG   = p["CARD_BG"]
BORDER    = p["BORDER"]
ACCENT    = p["ACCENT"]

if not st.session_state.data_loaded:
    st.markdown(
        f"""
        <div style="padding:32px 0 12px 0;">
            <h1 style="margin:0;font-size:2rem;font-weight:700;color:{TEXT_MAIN};">
                Dashboard Comercial MYM
            </h1>
            <p style="margin:6px 0 0 0;font-size:1rem;color:{TEXT_SEC};">
                Ventas, stock y oportunidades comerciales a partir de archivos Bsale.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.info("Carga los archivos de ventas y stock en la barra lateral para iniciar el análisis.")
    st.stop()

# ─────────────────────────────────────────────
# DATOS — FILTROS GLOBALES
# ─────────────────────────────────────────────

sales_global   = st.session_state.sales.copy()
stock_global   = st.session_state.stock.copy()
sku_df_global  = st.session_state.sku_df.copy()
sales_full     = st.session_state.sales  # referencia sin filtros para detalle semanal

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

min_sales_date = sales_global["Fecha"].min()
max_sales_date = sales_global["Fecha"].max()

# ─────────────────────────────────────────────
# ENCABEZADO COMPACTO
# ─────────────────────────────────────────────

diag         = st.session_state.diagnostics
cross        = st.session_state.cross_metrics
fecha_carga  = st.session_state.fecha_hora_carga
stock_col    = diag.get("stock_col_origin", "—")

st.markdown(
    f"""
    <div style="background:{CARD_BG};border:1px solid {BORDER};border-radius:8px;
                padding:14px 20px;margin-bottom:16px;">
        <div style="display:flex;align-items:baseline;gap:14px;flex-wrap:wrap;">
            <h1 style="margin:0;font-size:1.55rem;font-weight:700;color:{TEXT_MAIN};">
                Dashboard Comercial MYM
            </h1>
            <span style="font-size:0.9rem;color:{TEXT_SEC};">
                Ventas, stock y oportunidades comerciales desde archivos Bsale.
            </span>
        </div>
        <div style="display:flex;gap:24px;flex-wrap:wrap;margin-top:8px;font-size:0.85rem;color:{TEXT_SEC};">
            <span>Ventas: <strong style="color:{TEXT_MAIN};">
                {min_sales_date.strftime('%d-%m-%Y')} → {max_sales_date.strftime('%d-%m-%Y')}
            </strong></span>
            <span>Fuente de datos: <strong style="color:{TEXT_MAIN};">archivos cargados manualmente por el usuario</strong></span>
            <span>Actualizado: <strong style="color:{TEXT_MAIN};">{fecha_carga}</strong></span>
            <span>Stock usado: <strong style="color:{TEXT_MAIN};">{stock_col}</strong></span>
            <span>SKU vendidos: <strong style="color:{TEXT_MAIN};">{cross['skus_sold']}</strong></span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Diagnóstico técnico en expander lateral
with st.sidebar.expander("Diagnóstico de carga", expanded=False):
    st.markdown(f"- **Ventas (filas):** {diag['sales_rows']:,}")
    st.markdown(f"- **Stock (filas):** {diag['stock_rows']:,}")
    st.markdown(f"- **Encabezado ventas:** fila {diag['sales_header_row']}")
    st.markdown(f"- **Encabezado stock:** fila {diag['stock_header_row']}")
    st.markdown(f"- **Columna stock:** `{diag['stock_col_origin']}` ({diag['stock_col_origin_type']})")
    st.markdown("---")
    st.markdown(f"- **SKU vendidos:** {cross['skus_sold']:,}")
    st.markdown(f"- **SKU con stock:** {cross['skus_stock']:,}")
    st.markdown(f"- **SKU cruzados:** {cross['skus_crossed']:,}")
    st.markdown(f"- **Vendidos sin stock:** {cross['skus_sold_no_stock']:,}")
    st.markdown(f"- **Stock sin ventas:** {cross['skus_stock_no_sales']:,}")

# ─────────────────────────────────────────────
# TABS — ROUTING
# ─────────────────────────────────────────────

tabs = st.tabs([
    "Hallazgos",
    "Resumen Ejecutivo",
    "Pareto 80/20",
    "Stock sin ventas",
    "Demanda sin stock",
    "Quiebres de stock",
    "Caídas y crecimiento",
    "Base de análisis",
])

with tabs[0]:
    render_hallazgos(
        sales_global, stock_global,
        is_dark, min_sales_filter,
        max_sales_date, min_sales_date,
    )

with tabs[1]:
    render_resumen(
        sales_global, stock_global, sales_full,
        is_dark, max_sales_date, min_sales_date,
    )

with tabs[2]:
    render_pareto(
        sales_global, stock_global,
        is_dark, max_sales_date, min_sales_date,
    )

with tabs[3]:
    render_stock_sin_ventas(
        sales_global, stock_global,
        is_dark, max_sales_date, min_sales_date,
    )

with tabs[4]:
    render_demanda_sin_stock(
        sales_global, stock_global, sales_full,
        is_dark, max_sales_date, min_sales_date,
    )

with tabs[5]:
    render_quiebres(
        sales_global, stock_global,
        is_dark, max_sales_date, min_sales_date,
    )

with tabs[6]:
    render_caidas(
        sales_global, stock_global,
        is_dark, min_sales_filter,
        max_sales_date, min_sales_date,
    )

with tabs[7]:
    render_base(sku_df_global, is_dark)

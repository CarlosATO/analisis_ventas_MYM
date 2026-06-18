"""
styles.py — Inyección de CSS completo según tema visual.
Llamar inject_css(is_dark) UNA vez desde app.py después de determinar el tema.
"""

import streamlit as st


def inject_css(is_dark: bool) -> None:
    """
    Inyecta el CSS completo del dashboard en la página.
    Cubre: fondo, sidebar, inputs, file uploader, botones,
    alertas semánticas, tabs, métricas, expanders, tablas y texto.
    """

    APP_BG   = "#0F172A" if is_dark else "#F8FAFC"
    CARD_BG  = "#1E293B" if is_dark else "#FFFFFF"
    TEXT_MAIN = "#F8FAFC" if is_dark else "#0F172A"
    TEXT_SEC = "#CBD5E1" if is_dark else "#334155"
    BORDER   = "#334155" if is_dark else "#CBD5E1"
    ACCENT   = "#38BDF8" if is_dark else "#0284C7"
    SB_BG    = "#1E293B" if is_dark else "#F1F5F9"

    # Alertas semánticas — claro
    if is_dark:
        warn_css  = "background:#451A03 !important;border:1px solid #F59E0B !important;color:#FEF3C7 !important;"
        err_css   = "background:#450A0A !important;border:1px solid #EF4444 !important;color:#FEE2E2 !important;"
        succ_css  = "background:#052E16 !important;border:1px solid #22C55E !important;color:#DCFCE7 !important;"
        info_css  = "background:#0F1E36 !important;border:1px solid #2563EB !important;color:#93C5FD !important;"
    else:
        warn_css  = "background:#FEF3C7 !important;border:1px solid #D97706 !important;color:#78350F !important;"
        err_css   = "background:#FEE2E2 !important;border:1px solid #EF4444 !important;color:#991B1B !important;"
        succ_css  = "background:#DCFCE7 !important;border:1px solid #22C55E !important;color:#14532D !important;"
        info_css  = "background:#EFF6FF !important;border:1px solid #3B82F6 !important;color:#1E3A8A !important;"

    st.markdown(
        f"""
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
        <style>
            /* ── Tipografía base ── */
            html, body, [class*="css"], .stApp {{
                font-family: 'Inter', sans-serif !important;
            }}

            /* ── Fondo general ── */
            div[data-testid="stAppViewContainer"], .stApp {{
                background-color: {APP_BG} !important;
                color: {TEXT_MAIN} !important;
            }}

            /* ── Header transparente ── */
            header[data-testid="stHeader"], [data-testid="stHeader"] {{
                background: transparent !important;
                box-shadow: none !important;
            }}

            /* ── Sidebar ── */
            section[data-testid="stSidebar"],
            div[data-testid="stSidebar"] {{
                background-color: {SB_BG} !important;
                border-right: 1px solid {BORDER} !important;
            }}
            section[data-testid="stSidebar"] * {{
                color: {TEXT_MAIN} !important;
            }}
            section[data-testid="stSidebar"] h2 {{
                font-size: 0.88rem !important;
                font-weight: 700 !important;
                letter-spacing: 0.05em !important;
                text-transform: uppercase !important;
                color: {TEXT_SEC} !important;
                border-bottom: 1px solid {BORDER} !important;
                padding-bottom: 3px !important;
                margin-top: 8px !important;
                margin-bottom: 5px !important;
            }}
            section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] {{
                gap: 3px !important;
            }}
            section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div {{
                padding-top: 1px !important;
                padding-bottom: 1px !important;
            }}

            /* ── Selectbox y dropdowns ── */
            [data-baseweb="select"] {{
                background-color: {CARD_BG} !important;
                border: 1px solid {BORDER} !important;
                border-radius: 6px !important;
            }}
            [data-baseweb="select"] * {{
                background-color: {CARD_BG} !important;
                color: {TEXT_MAIN} !important;
            }}
            [data-baseweb="menu"],
            [data-baseweb="popover"],
            div[role="listbox"],
            ul[role="listbox"] {{
                background-color: {CARD_BG} !important;
                border: 1px solid {BORDER} !important;
                color: {TEXT_MAIN} !important;
            }}
            [data-baseweb="menu"] *,
            div[role="listbox"] *,
            ul[role="listbox"] * {{
                background-color: {CARD_BG} !important;
                color: {TEXT_MAIN} !important;
            }}

            /* ── Inputs de texto ── */
            input, textarea {{
                background-color: {CARD_BG} !important;
                color: {TEXT_MAIN} !important;
                border: 1px solid {BORDER} !important;
            }}

            /* ── File uploader ── */
            div[data-testid="stFileUploader"] {{
                background-color: {CARD_BG} !important;
                border: 2px dashed {BORDER} !important;
                border-radius: 8px !important;
                padding: 4px !important;
            }}
            div[data-testid="stFileUploaderDropzone"] {{
                background-color: {APP_BG} !important;
                border: 1px dashed {BORDER} !important;
                border-radius: 6px !important;
                padding: 6px 10px !important;
            }}
            div[data-testid="stFileUploaderDropzone"] * {{
                color: {TEXT_SEC} !important;
            }}
            div[data-testid="stFileUploader"] [data-testid="stUploadedFile"] {{
                background-color: {CARD_BG} !important;
                border: 1px solid {BORDER} !important;
                border-radius: 6px !important;
                padding: 4px 8px !important;
                margin-top: 4px !important;
            }}
            div[data-testid="stFileUploader"] [data-testid="stUploadedFile"] * {{
                background-color: transparent !important;
                color: {TEXT_MAIN} !important;
            }}

            /* ── Botones ── */
            button, .stButton button {{
                background-color: {CARD_BG} !important;
                color: {TEXT_MAIN} !important;
                border: 1px solid {BORDER} !important;
                border-radius: 6px !important;
            }}
            button[kind="primary"], .stButton button[kind="primary"] {{
                background-color: #2563EB !important;
                color: #fff !important;
                border: none !important;
            }}
            button[kind="primary"]:hover {{
                background-color: #1D4ED8 !important;
            }}
            button[kind="primary"]:disabled {{
                background-color: {CARD_BG} !important;
                color: {TEXT_SEC} !important;
                border: 1px solid {BORDER} !important;
                cursor: not-allowed !important;
                opacity: 0.7 !important;
            }}

            /* ── Alertas semánticas ── */
            div[data-testid="stAlert"] {{
                border-radius: 6px !important;
                padding: 6px 12px !important;
                margin: 3px 0 !important;
            }}
            div[data-testid="stAlert"] * {{ color: inherit !important; }}
            div[data-testid="stAlert"]:has(svg[data-testid*="Warning"]) {{
                {warn_css}
            }}
            div[data-testid="stAlert"]:has(svg[data-testid*="Error"]) {{
                {err_css}
            }}
            div[data-testid="stAlert"]:has(svg[data-testid*="Success"]) {{
                {succ_css}
            }}
            div[data-testid="stAlert"]:has(svg[data-testid*="Info"]) {{
                {info_css}
            }}

            /* ── Tabs ── */
            .stTabs [data-baseweb="tab"] {{
                color: {TEXT_SEC} !important;
                font-weight: 500;
                font-size: 0.9rem;
            }}
            .stTabs [aria-selected="true"] {{
                color: {ACCENT} !important;
                border-bottom-color: {ACCENT} !important;
            }}

            /* ── Métricas ── */
            div[data-testid="stMetricValue"] {{
                color: {ACCENT} !important;
                font-weight: 700;
            }}
            div[data-testid="stMetricLabel"] {{
                color: {TEXT_SEC} !important;
                font-size: 0.85rem;
            }}
            div[data-testid="stMetricDelta"] {{
                font-size: 0.82rem;
            }}

            /* ── Expanders ── */
            div[data-testid="stExpander"] {{
                background: {CARD_BG} !important;
                border: 1px solid {BORDER} !important;
                border-radius: 8px !important;
            }}
            div[data-testid="stExpander"] summary {{
                color: {TEXT_MAIN} !important;
                font-weight: 500;
            }}

            /* ── Dataframes / Tablas ── */
            .dataframe th {{
                background: {CARD_BG} !important;
                color: {TEXT_MAIN} !important;
                border: 1px solid {BORDER} !important;
                font-weight: 600 !important;
            }}
            .dataframe td {{
                color: {TEXT_SEC} !important;
                border: 1px solid {BORDER} !important;
            }}
            [data-testid="stDataFrame"] {{
                border: 1px solid {BORDER} !important;
                border-radius: 6px !important;
            }}

            /* ── Tipografía general ── */
            h1, h2, h3, h4, h5, h6 {{
                color: {TEXT_MAIN} !important;
            }}
            p, li, small, .stCaption {{
                color: {TEXT_SEC} !important;
            }}
            label {{
                color: {TEXT_MAIN} !important;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )

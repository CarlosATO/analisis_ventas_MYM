import pandas as pd
import numpy as np
from pathlib import Path

REQUIRED_SALES_COLUMNS = [
    "SKU",
    "Producto / Servicio",
    "Fecha y Hora Venta",
    "Venta Total Bruta",
    "Cantidad",
]

REQUIRED_STOCK_COLUMNS = [
    "SKU",
    "Cantidad Disponible",
]

def _clean_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza espacios accidentales en nombres de columnas."""
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    return df

def _to_number(series: pd.Series) -> pd.Series:
    """Convierte columnas numéricas aunque vengan con texto, separadores o valores vacíos."""
    return pd.to_numeric(series, errors="coerce").fillna(0)

def _normalize_sku(series: pd.Series) -> pd.Series:
    """
    Normaliza el SKU según las reglas:
    - Convertir a texto.
    - Quitar espacios al inicio y al final.
    - Eliminar ".0" si Excel lo convirtió desde número.
    - Convertir valores vacíos, nan o None en cadena vacía.
    """
    def _norm(val):
        if pd.isna(val) or val is None:
            return ""
        s = str(val).strip()
        if s.endswith(".0"):
            s = s[:-2]
        if s.lower() in ["nan", "none", "null", ""]:
            return ""
        return s
    return series.apply(_norm)

def _load_file_with_dynamic_header(file_obj, file_type: str) -> tuple[pd.DataFrame, int, list[str]]:
    """
    Carga un archivo Excel buscando de forma dinámica la fila de cabecera.
    """
    try:
        # Cargamos todo sin cabeceras para buscar la fila correcta
        df_raw = pd.read_excel(file_obj, header=None)
    except Exception as e:
        raise ValueError(f"Error al leer el archivo de {file_type}: {e}")

    header_idx = None

    for idx, row in df_raw.iterrows():
        # Convertimos las celdas no vacías a texto limpio en minúsculas
        row_str = [str(val).strip().lower() for val in row if pd.notna(val)]

        if file_type == "ventas":
            # Debe contener "sku" y al menos una columna más de ventas
            has_sku = any(s == "sku" for s in row_str)
            has_other = any(
                col in row_str
                for col in [
                    "producto / servicio",
                    "fecha y hora venta",
                    "venta total bruta",
                    "cantidad",
                ]
            )
            if has_sku and has_other:
                header_idx = idx
                break
        elif file_type == "stock":
            # Debe contener "sku" y además ("stock" o "disponible")
            has_sku = any(s == "sku" for s in row_str)
            has_stock = any("stock" in s or "disponible" in s for s in row_str)
            if has_sku and has_stock:
                header_idx = idx
                break

    if header_idx is None:
        header_idx = 0

    # Extraemos las cabeceras originales
    raw_headers = list(df_raw.iloc[header_idx])
    headers = [str(col).strip() if pd.notna(col) else f"Col_{i}" for i, col in enumerate(raw_headers)]

    # Creamos el DataFrame reestructurado
    df = df_raw.iloc[header_idx + 1 :].copy()
    df.columns = headers
    df = df.reset_index(drop=True)

    # Mostrar en consola
    print(f"Fila de encabezado detectada en {file_type}: {header_idx}")

    return df, header_idx, raw_headers

def load_files(sales_file, stock_file) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """
    Carga los archivos de ventas y stock de MYM.
    Normaliza encabezados y aplica reglas de negocio para la columna de Stock Disponible.
    """
    # 1. Cargar con detección de cabeceras
    sales_raw, sales_header_row, sales_original_cols = _load_file_with_dynamic_header(sales_file, "ventas")
    stock_raw, stock_header_row, stock_original_cols = _load_file_with_dynamic_header(stock_file, "stock")

    # 2. Sistema de Alias y Normalización para Ventas
    sales_cols_map = {}
    normalized_sales_cols = []
    for col in sales_raw.columns:
        col_lower = str(col).strip().lower()
        if col_lower == "sku":
            normalized_sales_cols.append("SKU")
            sales_cols_map[col] = "SKU"
        elif col_lower == "producto / servicio":
            normalized_sales_cols.append("Producto / Servicio")
            sales_cols_map[col] = "Producto / Servicio"
        elif col_lower == "fecha y hora venta":
            normalized_sales_cols.append("Fecha y Hora Venta")
            sales_cols_map[col] = "Fecha y Hora Venta"
        elif col_lower == "venta total bruta":
            normalized_sales_cols.append("Venta Total Bruta")
            sales_cols_map[col] = "Venta Total Bruta"
        elif col_lower == "cantidad":
            normalized_sales_cols.append("Cantidad")
            sales_cols_map[col] = "Cantidad"
        elif "linea" in col_lower or "tema" in col_lower:
            normalized_sales_cols.append("Línea / Tema de producto")
            sales_cols_map[col] = "Línea / Tema de producto"
        else:
            normalized_sales_cols.append(str(col).strip())
    sales_raw.columns = normalized_sales_cols

    # 3. Sistema de Alias y Prioridad para Stock
    # Prioridad: 1. Disponible, 2. Stock (Fallback)
    disponible_col = None
    stock_col_fallback = None

    for col in stock_raw.columns:
        col_lower = str(col).strip().lower()
        if "disponible" in col_lower:
            disponible_col = col
            break
        elif "stock" in col_lower:
            if stock_col_fallback is None:
                stock_col_fallback = col

    columna_origen_stock_disponible = None
    if disponible_col is not None:
        columna_origen_stock_disponible = disponible_col
        stock_col_origin_type = "Disponible"
    elif stock_col_fallback is not None:
        columna_origen_stock_disponible = stock_col_fallback
        stock_col_origin_type = "Stock (Fallback)"
    else:
        raise ValueError(
            "El archivo de stock no contiene las columnas mínimas esperadas. "
            "No se encontró una columna que represente el Stock Disponible (e.g. 'Disponible' o 'Stock')."
        )

    normalized_stock_cols = []
    for col in stock_raw.columns:
        col_lower = str(col).strip().lower()
        if col == columna_origen_stock_disponible:
            normalized_stock_cols.append("Cantidad Disponible")
        elif col_lower == "sku":
            normalized_stock_cols.append("SKU")
        elif col_lower == "producto":
            normalized_stock_cols.append("Producto")
        elif "linea" in col_lower or "tema" in col_lower:
            normalized_stock_cols.append("Línea / Tema de producto")
        else:
            normalized_stock_cols.append(str(col).strip())
    stock_raw.columns = normalized_stock_cols

    # 4. Validar columnas mínimas obligatorias después de alias
    missing_sales = [c for c in REQUIRED_SALES_COLUMNS if c not in sales_raw.columns]
    missing_stock = [c for c in REQUIRED_STOCK_COLUMNS if c not in stock_raw.columns]

    if missing_sales:
        raise ValueError(
            f"El archivo de ventas no contiene las columnas mínimas esperadas. "
            f"Faltan: {missing_sales}. Columnas detectadas: {list(sales_original_cols)}"
        )

    if missing_stock:
        raise ValueError(
            f"El archivo de stock no contiene las columnas mínimas esperadas. "
            f"Faltan: {missing_stock}. Columnas detectadas: {list(stock_original_cols)}"
        )

    # 5. Normalización de SKU y Exclusión de Valores Vacíos
    sales_raw["SKU"] = _normalize_sku(sales_raw["SKU"])
    stock_raw["SKU"] = _normalize_sku(stock_raw["SKU"])

    sales = sales_raw[sales_raw["SKU"] != ""].copy()
    stock = stock_raw[stock_raw["SKU"] != ""].copy()

    # 6. Conversión de Fechas y Tipos
    sales["Fecha"] = pd.to_datetime(
        sales["Fecha y Hora Venta"],
        errors="coerce",
        dayfirst=True
    )

    for col in [
        "Venta Total Bruta",
        "Venta Total Neta",
        "Cantidad",
        "Costo Total Neto",
        "Margen",
        "Descuento Bruto",
        "% Descuento",
        "% Margen",
    ]:
        if col in sales.columns:
            sales[col] = _to_number(sales[col])

    for col in [
        "Cantidad Disponible",
        "Stock",
        "Costo Neto Prom. Unitario",
        "Costo Neto Prom. Total",
        "Cantidad por Despachar",
        "Por recibir",
        "Precio Venta Bruto",
        "Margen Unitario",
        "Último costo",
    ]:
        if col in stock.columns:
            stock[col] = _to_number(stock[col])

    # Columnas derivadas de fecha
    sales = sales.dropna(subset=["Fecha"])
    sales["Mes"] = sales["Fecha"].dt.to_period("M").astype(str)
    sales["Semana"] = sales["Fecha"].dt.isocalendar().week.astype(int)
    sales["Año"] = sales["Fecha"].dt.year
    sales["Mes_Num"] = sales["Fecha"].dt.month

    # 7. Diagnósticos
    diagnostics = {
        "sales_header_row": sales_header_row,
        "stock_header_row": stock_header_row,
        "sales_rows": len(sales),
        "stock_rows": len(stock),
        "stock_col_origin": columna_origen_stock_disponible,
        "stock_col_origin_type": stock_col_origin_type,
        "sales_cols_detected": [str(c) for c in sales_original_cols if pd.notna(c)],
        "stock_cols_detected": [str(c) for c in stock_original_cols if pd.notna(c)],
    }

    return sales, stock, diagnostics

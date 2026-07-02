import sys
import traceback
import pandas as pd
import numpy as np

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

def _norm(name: str) -> str:
    """Normaliza un nombre: elimina acentos, mayúsculas, espacios/guiones a _."""
    import unicodedata
    text = unicodedata.normalize("NFKD", str(name).strip())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text.upper().replace(" ", "_").replace("-", "_").replace("/", "_")

def _find_column(df: pd.DataFrame, aliases: set[str]) -> str | None:
    """Busca una columna en el DataFrame que coincida con algún alias (todo en MAYÚSCULAS)."""
    norm_aliases = {_norm(a) for a in aliases}
    for col in df.columns:
        if _norm(col) in norm_aliases:
            return col
    return None

def _match_col(df: pd.DataFrame, *names: str) -> str | None:
    """Devuelve la primera columna del DataFrame que normalizada coincida con algún name dado respetando la prioridad de los alias."""
    for name in names:
        target = _norm(name)
        for col in df.columns:
            if _norm(col) == target:
                return col
    return None

def _drop_duplicate_columns(df: pd.DataFrame, file_type: str) -> pd.DataFrame:
    """Evita errores de pandas cuando el Excel trae columnas repetidas o alias duplicados."""
    duplicated = df.columns[df.columns.duplicated()].tolist()
    if duplicated:
        print(f"Columnas duplicadas en {file_type}; se conserva la primera: {duplicated}", file=sys.stderr)
        df = df.loc[:, ~df.columns.duplicated()].copy()
    return df

def _clean_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza espacios accidentales en nombres de columnas."""
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    return df

def _to_number(series: pd.Series) -> pd.Series:
    """Convierte columnas numéricas aunque vengan con texto, separadores o valores vacíos."""
    return pd.to_numeric(series, errors="coerce").fillna(0)

def _normalize_sku(series: pd.Series) -> pd.Series:
    def _sku_norm(val):
        if pd.isna(val) or val is None:
            return ""
        s = str(val).strip()
        if s.endswith(".0"):
            s = s[:-2]
        if s.lower() in ["nan", "none", "null", ""]:
            return ""
        return s
    return series.apply(_sku_norm)

SKU_ALIASES = {"SKU", "CODIGO", "CÓDIGO", "SKU_PRODUCTO", "CODIGO_PRODUCTO", "CÓDIGO_PRODUCTO", "ID_PRODUCTO", "ID", "COD", "CODE"}
SALES_HEADER_ALIASES = {"PRODUCTO___SERVICIO", "FECHA_DE_EMISION", "FECHA_Y_HORA_VENTA", "VENTA_TOTAL_BRUTA", "VENTA_TOTAL_NETA", "CANTIDAD"}
STOCK_HEADER_ALIASES = {"SKU", "PRODUCTO", "CANTIDAD_DISPONIBLE", "STOCK", "TIPO_DE_PRODUCTO", "MARCA"}

def _load_file_with_dynamic_header(file_obj, file_type: str, min_match: int = 2) -> tuple[pd.DataFrame, int, list[str]]:
    if not hasattr(file_obj, "read"):
        raise ValueError(f"El objeto recibido para {file_type} no es un flujo de bytes válido")
    file_obj.seek(0)
    try:
        df_raw = pd.read_excel(file_obj, header=None)
    except Exception as e:
        traceback.print_exc()
        raise ValueError(f"Error al leer el archivo de {file_type}. Verifique que sea un Excel válido. Detalle: {e}")

    header_idx = 0
    if file_type == "ventas":
        targets = {_norm(a) for a in SALES_HEADER_ALIASES}
    else:
        targets = {_norm(a) for a in STOCK_HEADER_ALIASES}

    for idx, row in df_raw.iterrows():
        row_norm = {_norm(str(v)) for v in row if pd.notna(v)}
        matches = len(row_norm & targets)
        if matches >= min_match and _norm("sku") in row_norm:
            header_idx = idx
            break

    raw_headers = list(df_raw.iloc[header_idx])
    headers = [str(col).strip() if pd.notna(col) else f"Col_{i}" for i, col in enumerate(raw_headers)]

    df = df_raw.iloc[header_idx + 1 :].copy()
    df.columns = headers
    df = df.reset_index(drop=True)

    print(f"Fila de encabezado detectada en {file_type}: {header_idx}")

    return df, header_idx, raw_headers

def _map_columns_sales(sales_raw: pd.DataFrame) -> pd.DataFrame:
    df = sales_raw.copy()
    col_map: dict[str, str] = {}

    col = _match_col(df, "SKU", "CODIGO", "CÓDIGO", "SKU_PRODUCTO", "CODIGO_PRODUCTO", "ID")
    if col:
        col_map[col] = "SKU"

    col = _match_col(df, "PRODUCTO / SERVICIO", "PRODUCTO")
    if col:
        col_map[col] = "Producto / Servicio"

    col = _match_col(df, "FECHA DE EMISION", "FECHA Y HORA VENTA", "FECHA")
    if col:
        col_map[col] = "Fecha y Hora Venta"

    col = _match_col(df, "VENTA TOTAL BRUTA", "VENTA TOTAL NETA", "VENTA", "TOTAL VENTA")
    if col:
        col_map[col] = "Venta Total Bruta"

    col = _match_col(df, "CANTIDAD", "UNIDADES", "QTY")
    if col:
        col_map[col] = "Cantidad"

    col = _match_col(df, "TIPO DE PRODUCTO / SERVICIO", "TIPO DE PRODUCTO", "PROVEEDOR")
    if col:
        col_map[col] = "Tipo de Producto / Servicio"

    col = _match_col(df, "MARCA")
    if col:
        col_map[col] = "Marca"

    for c in df.columns:
        if c not in col_map:
            col_map[c] = str(c).strip()

    missing = [k for k in ("SKU", "Producto / Servicio", "Fecha y Hora Venta", "Venta Total Bruta", "Cantidad") if k not in col_map.values()]
    if missing:
        raise ValueError(
            f"Columnas requeridas faltantes en ventas: {missing}. "
            f"Columnas detectadas en el archivo: {list(df.columns)}"
        )

    df.columns = [col_map[c] for c in df.columns]
    df = _drop_duplicate_columns(df, "ventas")
    return df


def _map_columns_stock(stock_raw: pd.DataFrame) -> tuple[pd.DataFrame, str, str]:
    df = stock_raw.copy()
    col_map: dict[str, str] = {}

    col = _match_col(df, "SKU", "CODIGO", "CÓDIGO", "SKU_PRODUCTO", "CODIGO_PRODUCTO", "ID")
    if col:
        col_map[col] = "SKU"

    col = _match_col(df, "PRODUCTO")
    if col:
        col_map[col] = "Producto"

    col_stock = _match_col(df, "CANTIDAD DISPONIBLE", "STOCK", "STOCK DISPONIBLE", "DISPONIBLE")
    if col_stock:
        col_map[col_stock] = "Cantidad Disponible"

    col = _match_col(df, "TIPO DE PRODUCTO", "CATEGORIA", "CATEGORÍA")
    if col:
        col_map[col] = "Tipo de Producto"

    col = _match_col(df, "MARCA")
    if col:
        col_map[col] = "Marca"

    for c in df.columns:
        if c not in col_map:
            col_map[c] = str(c).strip()

    missing = [k for k in ("SKU", "Cantidad Disponible") if k not in col_map.values()]
    if missing:
        raise ValueError(
            f"Columnas requeridas faltantes en stock: {missing}. "
            f"Columnas detectadas en el archivo: {list(df.columns)}"
        )

    df.columns = [col_map[c] for c in df.columns]
    df = _drop_duplicate_columns(df, "stock")
    origen_stock = col_stock or "Cantidad Disponible"
    tipo_stock = "Disponible" if "DISPONIBLE" in _norm(origen_stock) else "Stock (Fallback)"
    return df, origen_stock, tipo_stock


def load_files(sales_file, stock_file) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """
    Carga los archivos de ventas y stock de MYM.
    Normaliza encabezados y aplica reglas de negocio para la columna de Stock Disponible.
    """
    sales_raw, sales_header_row, sales_original_cols = _load_file_with_dynamic_header(sales_file, "ventas")
    stock_raw, stock_header_row, stock_original_cols = _load_file_with_dynamic_header(stock_file, "stock")

    sales = _map_columns_sales(sales_raw)
    stock, columna_origen_stock_disponible, stock_col_origin_type = _map_columns_stock(stock_raw)

    sales["SKU"] = _normalize_sku(sales["SKU"])
    stock["SKU"] = _normalize_sku(stock["SKU"])

    sales = sales[sales["SKU"] != ""].copy()
    stock = stock[stock["SKU"] != ""].copy()

    sales["Fecha"] = pd.to_datetime(
        sales["Fecha y Hora Venta"],
        errors="coerce",
        dayfirst=True
    )

    for col in [
        "Venta Total Bruta", "Venta Total Neta", "Cantidad",
        "Costo Total Neto", "Margen", "Descuento Bruto",
        "% Descuento", "% Margen",
    ]:
        if col in sales.columns:
            sales[col] = _to_number(sales[col])

    for col in [
        "Cantidad Disponible", "Stock",
        "Costo Neto Prom. Unitario", "Costo Neto Prom. Total",
        "Cantidad por Despachar", "Por recibir", "Precio Venta Bruto",
        "Margen Unitario", "Último costo",
    ]:
        if col in stock.columns:
            stock[col] = _to_number(stock[col])

    sales = sales.dropna(subset=["Fecha"])
    if sales.empty:
        raise ValueError(
            "Ninguna fila de ventas tiene una fecha válida después del procesamiento. "
            "Verifique que la columna de fecha (ej. 'Fecha de Emisión' o 'Fecha y Hora Venta') "
            "contenga fechas en formato día/mes/año."
        )
    sales["Mes"] = sales["Fecha"].dt.to_period("M").astype(str)
    sales["Semana"] = sales["Fecha"].dt.isocalendar().week.astype(int)
    sales["Año"] = sales["Fecha"].dt.year
    sales["Mes_Num"] = sales["Fecha"].dt.month

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

import pandas as pd
import numpy as np
import math
import unicodedata

# SKU de conceptos comerciales no inventariables
# Estos SKU participan en ventas totales e indicadores financieros
# pero NO en rankings, Pareto, hallazgos, ni análisis de productos
EXCLUDED_SKUS = {"2202", "0001", "P000038"}

def is_commercial_concept(sku: str) -> bool:
    return str(sku).strip() in EXCLUDED_SKUS

def filter_commercial(df: pd.DataFrame, exclude: bool = True) -> pd.DataFrame:
    """Excluye SKU de conceptos comerciales del DataFrame."""
    if not exclude or "SKU" not in df.columns:
        return df
    return df[~df["SKU"].apply(is_commercial_concept)].copy()


def build_sku_summary(sales: pd.DataFrame, stock: pd.DataFrame, start_date=None, end_date=None) -> pd.DataFrame:
    """
    Construye tabla maestra por SKU cruzando ventas + stock.
    Permite filtrar los cálculos de venta operacional por un rango de fechas.
    """
    if start_date is None:
        start_date = sales["Fecha"].min()
    if end_date is None:
        end_date = sales["Fecha"].max()

    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)

    duration_days = (end_date - start_date).days
    if duration_days <= 0:
        duration_days = 30

    # Filtrar ventas por período seleccionado para cálculos operacionales
    sales_period = sales[(sales["Fecha"] >= start_date) & (sales["Fecha"] <= end_date)]

    product_cols = ["SKU", "Producto / Servicio", "Tipo de Producto / Servicio", "Marca", "Línea / Tema de producto"]
    existing_product_cols = [c for c in product_cols if c in sales.columns]

    product_master = (
        sales[existing_product_cols]
        .dropna(subset=["SKU"])
        .drop_duplicates("SKU")
    )

    # Ventas del período seleccionado
    sales_summary = (
        sales_period.groupby("SKU", as_index=False)
        .agg(
            venta_6m=("Venta Total Bruta", "sum"),
            unidades_6m=("Cantidad", "sum"),
            margen_6m=("Margen", "sum") if "Margen" in sales_period.columns else ("Venta Total Bruta", "sum"),
            documentos=("Numero del documento", "nunique") if "Numero del documento" in sales_period.columns else ("SKU", "count"),
        )
    )

    # Historial completo (para fecha_ultima_venta, total histórico y documentos)
    history_summary = (
        sales.groupby("SKU", as_index=False)
        .agg(
            venta_historica_total=("Venta Total Bruta", "sum"),
            unidades_historicas_total=("Cantidad", "sum"),
            documentos_historicos=("Numero del documento", "nunique") if "Numero del documento" in sales.columns else ("SKU", "count"),
            fecha_primera_venta=("Fecha", "min"),
            fecha_ultima_venta=("Fecha", "max"),
        )
    )

    monthly = (
        sales_period.groupby(["SKU", "Mes"], as_index=False)
        .agg(venta_mes=("Venta Total Bruta", "sum"), unidades_mes=("Cantidad", "sum"))
    )

    # Mitades de período dinámicas para crecimiento/caída
    half_days = max(1, duration_days // 2)
    mid_date = end_date - pd.Timedelta(days=half_days)

    last_60 = (
        sales[(sales["Fecha"] >= mid_date) & (sales["Fecha"] <= end_date)]
        .groupby("SKU", as_index=False)
        .agg(venta_60d=("Venta Total Bruta", "sum"), unidades_60d=("Cantidad", "sum"))
    )

    prev_60 = (
        sales[(sales["Fecha"] >= start_date) & (sales["Fecha"] < mid_date)]
        .groupby("SKU", as_index=False)
        .agg(venta_prev_60d=("Venta Total Bruta", "sum"), unidades_prev_60d=("Cantidad", "sum"))
    )

    first_month = sales_period["Mes"].min() if not sales_period.empty else None
    last_month = sales_period["Mes"].max() if not sales_period.empty else None

    if first_month is not None:
        first_month_sales = (
            monthly[monthly["Mes"] == first_month][["SKU", "venta_mes", "unidades_mes"]]
            .rename(columns={"venta_mes": "venta_primer_mes", "unidades_mes": "unidades_primer_mes"})
        )
    else:
        first_month_sales = pd.DataFrame(columns=["SKU", "venta_primer_mes", "unidades_primer_mes"])

    if last_month is not None:
        last_month_sales = (
            monthly[monthly["Mes"] == last_month][["SKU", "venta_mes", "unidades_mes"]]
            .rename(columns={"venta_mes": "venta_ultimo_mes", "unidades_mes": "unidades_ultimo_mes"})
        )
    else:
        last_month_sales = pd.DataFrame(columns=["SKU", "venta_ultimo_mes", "unidades_ultimo_mes"])

    stock_cols = [
        "SKU",
        "Producto",
        "Variante",
        "Tipo de Producto",
        "Cantidad Disponible",
        "Stock",
        "Costo Neto Prom. Unitario",
        "Costo Neto Prom. Total",
        "Por recibir",
        "Precio Venta Bruto",
        "Marca",
        "Línea / Tema de producto",
    ]
    existing_stock_cols = [c for c in stock_cols if c in stock.columns]
    stock_summary = stock[existing_stock_cols].drop_duplicates("SKU")

    all_skus = pd.DataFrame(
        list(set(product_master["SKU"]) | set(stock_summary["SKU"])),
        columns=["SKU"]
    )

    df = (
        all_skus
        .merge(product_master, on="SKU", how="left")
        .merge(sales_summary, on="SKU", how="left")
        .merge(history_summary, on="SKU", how="left")
        .merge(first_month_sales, on="SKU", how="left")
        .merge(last_month_sales, on="SKU", how="left")
        .merge(last_60, on="SKU", how="left")
        .merge(prev_60, on="SKU", how="left")
        .merge(stock_summary, on="SKU", how="left")
    )

    # Consolidar Marca
    if "Marca_x" in df.columns and "Marca_y" in df.columns:
        df["Marca"] = df["Marca_x"].fillna(df["Marca_y"]).fillna("Sin Marca")
        df = df.drop(columns=["Marca_x", "Marca_y"])
    elif "Marca_x" in df.columns:
        df["Marca"] = df["Marca_x"].fillna("Sin Marca")
        df = df.drop(columns=["Marca_x"])
    elif "Marca_y" in df.columns:
        df["Marca"] = df["Marca_y"].fillna("Sin Marca")
        df = df.drop(columns=["Marca_y"])
    elif "Marca" in df.columns:
        df["Marca"] = df["Marca"].fillna("Sin Marca")
    else:
        df["Marca"] = "Sin Marca"

    # Consolidar Línea / Tema de producto
    if "Línea / Tema de producto_x" in df.columns and "Línea / Tema de producto_y" in df.columns:
        df["Línea / Tema de producto"] = df["Línea / Tema de producto_x"].fillna(df["Línea / Tema de producto_y"]).fillna("Sin Línea/Tema")
        df = df.drop(columns=["Línea / Tema de producto_x", "Línea / Tema de producto_y"])
    elif "Línea / Tema de producto_x" in df.columns:
        df["Línea / Tema de producto"] = df["Línea / Tema de producto_x"].fillna("Sin Línea/Tema")
        df = df.drop(columns=["Línea / Tema de producto_x"])
    elif "Línea / Tema de producto_y" in df.columns:
        df["Línea / Tema de producto"] = df["Línea / Tema de producto_y"].fillna("Sin Línea/Tema")
        df = df.drop(columns=["Línea / Tema de producto_y"])
    elif "Línea / Tema de producto" in df.columns:
        df["Línea / Tema de producto"] = df["Línea / Tema de producto"].fillna("Sin Línea/Tema")
    else:
        df["Línea / Tema de producto"] = "Sin Línea/Tema"

    # Consolidar Categoría
    tipo_sales = "Tipo de Producto / Servicio" in df.columns
    tipo_stock = "Tipo de Producto" in df.columns
    if tipo_sales and tipo_stock:
        df["Categoría"] = df["Tipo de Producto / Servicio"].fillna(df["Tipo de Producto"]).fillna("Sin Categoría")
    elif tipo_sales:
        df["Categoría"] = df["Tipo de Producto / Servicio"].fillna("Sin Categoría")
    elif tipo_stock:
        df["Categoría"] = df["Tipo de Producto"].fillna("Sin Categoría")
    else:
        df["Categoría"] = "Sin Categoría"

    numeric_cols = [
        "venta_6m", "unidades_6m", "margen_6m",
        "venta_primer_mes", "unidades_primer_mes",
        "venta_ultimo_mes", "unidades_ultimo_mes",
        "venta_60d", "unidades_60d",
        "venta_prev_60d", "unidades_prev_60d",
        "venta_historica_total", "unidades_historicas_total", "documentos_historicos",
        "Cantidad Disponible", "Stock",
        "Costo Neto Prom. Unitario", "Costo Neto Prom. Total",
        "Por recibir", "Precio Venta Bruto"
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Promedios en base a la duración del período
    df["venta_promedio_diaria_30d"] = df["venta_6m"] / duration_days
    df["unidades_promedio_diaria_30d"] = df["unidades_6m"] / duration_days

    df["dias_cobertura"] = np.where(
        df["unidades_promedio_diaria_30d"] > 0,
        df["Cantidad Disponible"] / df["unidades_promedio_diaria_30d"],
        np.nan
    )

    if "Costo Neto Prom. Unitario" in df.columns:
        df["valor_stock_disponible"] = df["Cantidad Disponible"] * df["Costo Neto Prom. Unitario"]
    else:
        df["valor_stock_disponible"] = 0.0

    df["variacion_ultimo_vs_primer_mes_pct"] = np.where(
        df["venta_primer_mes"] > 0,
        (df["venta_ultimo_mes"] - df["venta_primer_mes"]) / df["venta_primer_mes"],
        np.nan
    )

    df["variacion_60d_pct"] = np.where(
        df["venta_prev_60d"] > 0,
        (df["venta_60d"] - df["venta_prev_60d"]) / df["venta_prev_60d"],
        np.nan
    )

    df["diferencia_venta_periodo"] = df["venta_60d"] - df["venta_prev_60d"]

    reference_date = sales["Fecha"].max()
    df["dias_desde_ultima_venta"] = (reference_date - df["fecha_ultima_venta"]).dt.days

    # Venta promedio diaria mientras vendía (basada en el período en activo)
    dias_activo = (df["fecha_ultima_venta"] - df["fecha_primera_venta"]).dt.days + 1
    df["venta_promedio_mientras_vendia"] = np.where(
        dias_activo > 0,
        df["venta_historica_total"] / dias_activo,
        df["venta_historica_total"]
    )

    if "Producto / Servicio" in df.columns:
        if "Producto" in df.columns:
            df["Producto"] = df["Producto / Servicio"].fillna(df["Producto"])
        else:
            df["Producto"] = df["Producto / Servicio"]

    return df


def classify_skus(df: pd.DataFrame) -> pd.DataFrame:
    """
    Agrega clasificaciones ejecutivas.
    """
    df = df.copy()

    # Definir si tuvo demanda histórica relevante
    df["tuvo_demanda_historica"] = (
        (df["venta_historica_total"] >= 100000) |
        (df["unidades_historicas_total"] >= 5) |
        (df["documentos_historicos"] >= 3)
    )

    # Reglas de Clasificación
    # A) Producto muerto con stock (stock > 0, sin ventas en el período)
    venta_cero = df["venta_6m"].fillna(0) == 0
    sin_fecha_venta = df["dias_desde_ultima_venta"].isna() | (df["dias_desde_ultima_venta"] >= 45)
    cond_muerto_real = (
        (df["Cantidad Disponible"] > 0) &
        sin_fecha_venta &
        venta_cero
    )

    # B) Demanda histórica sin stock (stock <= 0, dias >= 14, tuvo demanda relevante)
    cond_demanda_sin_stock = (
        (df["Cantidad Disponible"] <= 0) &
        (df["dias_desde_ultima_venta"].notna()) &
        (df["dias_desde_ultima_venta"] >= 14) &
        (df["tuvo_demanda_historica"] == True)
    )

    cond_quiebre_critico = (df["dias_cobertura"].notna()) & (df["dias_cobertura"] < 7) & (df["Cantidad Disponible"] > 0)
    cond_riesgo_quiebre = (df["dias_cobertura"].notna()) & (df["dias_cobertura"] < 15) & (df["Cantidad Disponible"] > 0)

    cond_caida = (df["venta_60d"] < df["venta_prev_60d"] * 0.2) & (df["venta_prev_60d"] > 0) & (df["Cantidad Disponible"] > 0)
    cond_crecimiento = (df["venta_60d"] > df["venta_prev_60d"] * 1.5) & (df["venta_prev_60d"] > 0)

    conditions = [
        cond_muerto_real,
        cond_demanda_sin_stock,
        cond_quiebre_critico,
        cond_riesgo_quiebre,
        cond_caida,
        cond_crecimiento
    ]

    choices = [
        "Producto muerto con stock",
        "Demanda histórica sin stock",
        "Quiebre crítico",
        "Riesgo de quiebre",
        "Venta en caída con stock",
        "Producto en crecimiento",
    ]

    df["alerta"] = np.select(conditions, choices, default="Normal")

    df["prioridad"] = np.select(
        [
            df["alerta"].eq("Producto muerto con stock"),
            df["alerta"].eq("Demanda histórica sin stock"),
            df["alerta"].eq("Quiebre crítico"),
            df["alerta"].eq("Venta en caída con stock"),
            df["alerta"].eq("Riesgo de quiebre"),
        ],
        ["Alta", "Alta", "Alta", "Media-Alta", "Media"],
        default="Normal"
    )

    return df


def pareto_analysis(df: pd.DataFrame) -> pd.DataFrame:
    pareto = df[["SKU", "Producto / Servicio", "venta_6m", "unidades_6m", "margen_6m"]].copy()
    pareto = pareto.sort_values("venta_6m", ascending=False)
    total = pareto["venta_6m"].sum()
    pareto["venta_acumulada"] = pareto["venta_6m"].cumsum()
    pareto["pct_acumulado"] = np.where(total > 0, pareto["venta_acumulada"] / total, 0)
    pareto["clasificacion_pareto"] = np.where(pareto["pct_acumulado"] <= 0.80, "A: Core ventas", "B/C: Cola larga")
    return pareto


def monthly_sales(sales: pd.DataFrame) -> pd.DataFrame:
    return (
        sales.groupby("Mes", as_index=False)
        .agg(
            venta=("Venta Total Bruta", "sum"),
            unidades=("Cantidad", "sum"),
            margen=("Margen", "sum") if "Margen" in sales.columns else ("Venta Total Bruta", "sum"),
            sku_activos=("SKU", "nunique"),
        )
        .sort_values("Mes")
    )


def export_findings(output_path: str, sku_df: pd.DataFrame, pareto: pd.DataFrame, monthly: pd.DataFrame) -> None:
    """
    Exporta hallazgos a Excel para entregar a gerencia.
    """
    with pd.ExcelWriter(output_path, engine="xlsxwriter") as writer:
        monthly.to_excel(writer, sheet_name="Resumen mensual", index=False)
        pareto.to_excel(writer, sheet_name="Pareto", index=False)

        sku_df[sku_df["alerta"].eq("Producto muerto con stock")] \
            .sort_values("valor_stock_disponible", ascending=False) \
            .to_excel(writer, sheet_name="Muertos con stock", index=False)

        sku_df[sku_df["alerta"].eq("Quiebre crítico")] \
            .sort_values("venta_6m", ascending=False) \
            .to_excel(writer, sheet_name="Quiebre critico", index=False)

        sku_df[sku_df["alerta"].eq("Venta en caída con stock")] \
            .sort_values("valor_stock_disponible", ascending=False) \
            .to_excel(writer, sheet_name="Caida con stock", index=False)

        sku_df.sort_values("venta_6m", ascending=False) \
            .to_excel(writer, sheet_name="Base SKU", index=False)


def weekly_sales(sales: pd.DataFrame) -> pd.DataFrame:
    """
    Agrupa las ventas por semana del período seleccionado para graficar la tendencia.
    """
    return (
        sales.groupby(["Año", "Semana"], as_index=False)
        .agg(
            venta=("Venta Total Bruta", "sum"),
            unidades=("Cantidad", "sum")
        )
        .sort_values(["Año", "Semana"])
    )


def weekly_sales_by_sku(sales: pd.DataFrame, anio: int, semana: int) -> pd.DataFrame:
    """
    Retorna ventas detalladas por SKU para una semana y año específicos.
    """
    mask = (sales["Año"] == anio) & (sales["Semana"] == semana)
    filtered = sales[mask]
    if filtered.empty:
        return pd.DataFrame(columns=["SKU", "Producto", "Venta", "Unidades", "Margen"])

    grp = filtered.groupby("SKU", as_index=False).agg(
        Producto=("Producto / Servicio", "first"),
        Venta=("Venta Total Bruta", "sum"),
        Unidades=("Cantidad", "sum"),
        Margen=("Margen", "sum") if "Margen" in filtered.columns else ("Venta Total Bruta", "sum"),
    )
    return grp.sort_values("Venta", ascending=False)


SUPPLIER_ALIASES = {
    "proveedor",
    "nombre proveedor",
    "razon social proveedor",
    "supplier",
    "vendor",
    "tipo de producto / servicio",
}

MONTHS_ES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
    7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}


def _norm_col_name(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value).strip().lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return " ".join(text.split())


def detect_supplier_column(df: pd.DataFrame) -> str | None:
    for col in df.columns:
        if _norm_col_name(col) in SUPPLIER_ALIASES:
            return col
    return None

def has_supplier_column(sales: pd.DataFrame, stock: pd.DataFrame) -> bool:
    return detect_supplier_column(stock) is not None or detect_supplier_column(sales) is not None

def calculo_reposicion(
    sales: pd.DataFrame, stock: pd.DataFrame,
    dias_analisis: int, cobertura_objetivo: int,
    proveedor: str = "", marca: str = "", categoria: str = "",
    stock_min: float = 0, exclude_commercial: bool = True,
    incluir_sin_stock_sin_venta: bool = False
) -> dict:
    VALID_DIAS = (7, 14, 21, 28, 35, 42, 49, 56, 84, 112, 182, 365)
    if dias_analisis not in VALID_DIAS:
        # Round to nearest valid value
        dias_analisis = min(VALID_DIAS, key=lambda x: abs(x - dias_analisis))
    if cobertura_objetivo not in (2, 4, 6, 8, 12, 16):
        cobertura_objetivo = 2

    if exclude_commercial:
        sales = filter_commercial(sales)
        stock = filter_commercial(stock)

    max_date = sales["Fecha"].max()
    min_date = sales["Fecha"].min()

    num_bloques = dias_analisis // 7
    
    bloques_starts_recent_first = [max_date - pd.Timedelta(days=7*i + 6) for i in range(num_bloques)]
    
    bloques = []
    for start in reversed(bloques_starts_recent_first):
        end = start + pd.Timedelta(days=6)
        col_name = f"{start.strftime('%d-%m')} a {end.strftime('%d-%m')}"
        bloques.append((start, end, col_name))
        
    start_date = max(bloques[0][0], min_date)

    sales_period = sales[(sales["Fecha"] >= start_date) & (sales["Fecha"] <= max_date)].copy()
    
    def get_block_col(d):
        for b_start, b_end, col in bloques:
            if b_start <= d <= b_end:
                return col
        return None
        
    sales_period["block_col"] = sales_period["Fecha"].apply(get_block_col)
    sales_period = sales_period.dropna(subset=["block_col"])

    unidades_por_sku = sales_period.groupby("SKU").agg(
        total_unidades_vendidas=("Cantidad", "sum")
    ).reset_index()

    pivot = sales_period.pivot_table(
        index="SKU", columns="block_col", values="Cantidad", aggfunc="sum", fill_value=0
    ).reset_index()

    semanas_cols = [b[2] for b in bloques]
    
    for col in semanas_cols:
        if col not in pivot.columns:
            pivot[col] = 0

    drop_week_cols = [c for c in pivot.columns if c != "SKU" and c not in semanas_cols]
    if drop_week_cols:
        pivot = pivot.drop(columns=drop_week_cols)

    unidades_por_sku = unidades_por_sku.merge(pivot, on="SKU", how="left")
    unidades_por_sku[semanas_cols] = unidades_por_sku[semanas_cols].fillna(0)

    num_bloques_tendencia = (num_bloques // 2) * 2
    mitad = max(1, num_bloques_tendencia // 2)
    
    cols_tendencia = semanas_cols[-num_bloques_tendencia:] if num_bloques_tendencia > 0 else []
    cols_anteriores = cols_tendencia[:mitad]
    cols_recientes = cols_tendencia[mitad:]

    if cols_recientes and cols_anteriores:
        unidades_por_sku["unidades_recientes"] = unidades_por_sku[cols_recientes].sum(axis=1)
        unidades_por_sku["unidades_anteriores"] = unidades_por_sku[cols_anteriores].sum(axis=1)
    else:
        unidades_por_sku["unidades_recientes"] = 0
        unidades_por_sku["unidades_anteriores"] = 0

    unidades_por_sku["tendencia_pct"] = np.where(
        unidades_por_sku["unidades_anteriores"] > 0,
        (unidades_por_sku["unidades_recientes"] - unidades_por_sku["unidades_anteriores"]) / unidades_por_sku["unidades_anteriores"],
        np.nan
    )
    unidades_por_sku["estado_tendencia"] = np.select(
        [
            unidades_por_sku["tendencia_pct"] > 0.15,
            unidades_por_sku["tendencia_pct"] < -0.15,
            unidades_por_sku["tendencia_pct"].notna(),
        ],
        ["Creciendo", "Cayendo", "Estable"],
        default="Sin comparación"
    )

    supplier_stock_col = detect_supplier_column(stock)
    supplier_sales_col = detect_supplier_column(sales)
    proveedor_disponible = supplier_stock_col is not None or supplier_sales_col is not None
    stock_cols = ["SKU", "Producto", "Variante", "Marca", "Tipo de Producto", "Cantidad Disponible", "Costo Neto Prom. Unitario"]
    if supplier_stock_col is not None:
        stock_cols.append(supplier_stock_col)
    existing_stock_cols = [c for c in stock_cols if c in stock.columns]
    
    df = stock[existing_stock_cols].drop_duplicates("SKU").copy()
    if supplier_stock_col is not None and supplier_stock_col != "Proveedor":
        df = df.rename(columns={supplier_stock_col: "Proveedor"})
    elif supplier_sales_col is not None:
        supplier_map = sales[["SKU", supplier_sales_col]].dropna(subset=[supplier_sales_col]).drop_duplicates("SKU")
        supplier_map = supplier_map.rename(columns={supplier_sales_col: "Proveedor"})
        df = df.merge(supplier_map, on="SKU", how="left")
    
    if "Categoría" not in df.columns and "Tipo de Producto" in df.columns:
        df["Categoría"] = df["Tipo de Producto"]
    if "Categoría" not in df.columns:
        df["Categoría"] = "Sin Categoría"
    
    if "Proveedor" not in df.columns:
        df["Proveedor"] = "Sin Proveedor"
    if "Marca" not in df.columns:
        df["Marca"] = "Sin Marca"
    if "Producto" not in df.columns:
        df["Producto"] = df["SKU"]
    if "Costo Neto Prom. Unitario" not in df.columns:
        df["Costo Neto Prom. Unitario"] = 0

    if "Variante" not in df.columns:
        df["Variante"] = "-"
    df["Variante"] = df["Variante"].fillna("-")

    df["Proveedor"] = df["Proveedor"].fillna("Sin Proveedor")
    df["Marca"] = df["Marca"].fillna("Sin Marca")
    df["Categoría"] = df["Categoría"].fillna("Sin Categoría")
    df["Cantidad Disponible"] = pd.to_numeric(df["Cantidad Disponible"], errors="coerce").fillna(0)
    df["Costo Neto Prom. Unitario"] = pd.to_numeric(df["Costo Neto Prom. Unitario"], errors="coerce").fillna(0)

    if proveedor and proveedor != "Todos":
        df = df[df["Proveedor"] == proveedor]
    if marca and marca != "Todas":
        df = df[df["Marca"] == marca]
    if categoria and categoria != "Todas":
        df = df[df["Categoría"] == categoria]
    if stock_min > 0:
        df = df[df["Cantidad Disponible"] >= stock_min]

    df = df.merge(unidades_por_sku, on="SKU", how="left")
    df["total_unidades_vendidas"] = df["total_unidades_vendidas"].fillna(0)
    for c in semanas_cols:
        if c not in df.columns:
            df[c] = 0
        else:
            df[c] = df[c].fillna(0)

    df["tendencia_pct"] = df.get("tendencia_pct", np.nan)
    df["estado_tendencia"] = df.get("estado_tendencia", "Sin comparación")
    df["promedio_semanal"] = (df["total_unidades_vendidas"] / dias_analisis) * 7
    
    df["cobertura_actual"] = np.where(
        df["promedio_semanal"] > 0,
        df["Cantidad Disponible"] / df["promedio_semanal"],
        np.nan
    )

    df["stock_objetivo"] = df["promedio_semanal"] * cobertura_objetivo
    df["stock_objetivo"] = df["stock_objetivo"].apply(lambda x: math.ceil(x))
    
    df["compra_sugerida"] = df["stock_objetivo"] - df["Cantidad Disponible"]
    df["compra_sugerida"] = np.where(df["compra_sugerida"] < 0, 0, df["compra_sugerida"])
    df["compra_sugerida"] = df["compra_sugerida"].apply(lambda x: math.ceil(x))

    sin_stock_sin_movimiento = (df["Cantidad Disponible"] == 0) & (df["total_unidades_vendidas"] == 0)
    if not incluir_sin_stock_sin_venta:
        df = df[~sin_stock_sin_movimiento].copy()
        sin_stock_sin_movimiento = (df["Cantidad Disponible"] == 0) & (df["total_unidades_vendidas"] == 0)
    else:
        df.loc[sin_stock_sin_movimiento, "compra_sugerida"] = 0

    conditions = [
        sin_stock_sin_movimiento,
        df["promedio_semanal"] == 0,
        df["cobertura_actual"] < 2,
        (df["cobertura_actual"] >= 2) & (df["cobertura_actual"] < 6),
        (df["cobertura_actual"] >= 6) & (df["compra_sugerida"] > 0),
        (df["cobertura_actual"] >= 6) & (df["compra_sugerida"] == 0)
    ]
    choices = ["Sin stock / sin movimiento", "Sin movimiento", "Crítico", "Reponer", "Completar objetivo", "Stock sano"]
    df["estado_stock"] = np.select(conditions, choices, default="Stock sano")
    df["accion_sugerida"] = np.select(
        conditions,
        [
            "Agregar manualmente solo si se desea reactivar el producto",
            "No comprar",
            "Comprar urgente",
            "Incluir en próxima compra",
            "Comprar solo si se desea llegar a cobertura objetivo",
            "No comprar por ahora",
        ],
        default="No comprar por ahora"
    )
    df["prioridad"] = df["estado_stock"]

    df["monto_estimado_compra"] = df["compra_sugerida"] * df["Costo Neto Prom. Unitario"]

    prioridad_map = {"Crítico": 1, "Reponer": 2, "Completar objetivo": 3, "Stock sano": 4, "Sin movimiento": 5, "Sin stock / sin movimiento": 6}
    df["_sort"] = df["estado_stock"].map(prioridad_map)
    df = df.sort_values(["_sort", "compra_sugerida"], ascending=[True, False]).drop(columns=["_sort"])
    df = df.reset_index(drop=True)

    sku_evaluados = len(df)
    sku_criticos = len(df[df["prioridad"] == "Crítico"])
    sku_reponer = len(df[df["prioridad"] == "Reponer"])
    sku_completar_objetivo = len(df[df["prioridad"] == "Completar objetivo"])
    unidades_sugeridas = int(df["compra_sugerida"].sum())
    monto_estimado = float(df["monto_estimado_compra"].sum())
    
    has_missing_cost = bool((df[df["compra_sugerida"] > 0]["Costo Neto Prom. Unitario"] == 0).any())

    return {
        "filtros": {
            "proveedor": proveedor or "Todos",
            "marca": marca or "Todas",
            "categoria": categoria or "Todas",
            "dias_analisis": dias_analisis,
            "cobertura_objetivo": cobertura_objetivo,
            "stock_minimo": stock_min,
            "incluir_sin_stock_sin_venta": incluir_sin_stock_sin_venta
        },
        "proveedor_disponible": proveedor_disponible,
        "aviso_proveedor": "" if proveedor_disponible else "No se detectó columna de proveedor explícita. Los proveedores se están tomando desde 'Tipo de Producto / Servicio'.",
        "resumen": {
            "proveedor_seleccionado": proveedor or "Todos",
            "sku_evaluados": sku_evaluados,
            "sku_criticos": sku_criticos,
            "sku_reponer": sku_reponer,
            "sku_completar_objetivo": sku_completar_objetivo,
            "unidades_sugeridas": unidades_sugeridas,
            "monto_estimado_compra": monto_estimado,
            "has_missing_cost": has_missing_cost,
            "advertencia_costo": "Algunos productos no tienen costo disponible. El monto estimado puede estar incompleto." if has_missing_cost else ""
        },
        "preparacion_orden_compra": {
            "seleccion_productos_habilitada": False,
            "campo_clave": "SKU",
            "siguiente_fase": "Generar propuesta de Orden de Compra desde productos seleccionados"
        },
        "productos": df,
        "semanas_cols": semanas_cols
    }

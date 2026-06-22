import io

with open("main.py", "r", encoding="utf-8") as f:
    content = f.read()

# get_stock_sin_ventas
target1 = """def get_stock_sin_ventas(
    analysis_id: str,
    period: str = Query("Todo", description="Período sin ventas: 30, 60, 90, 180 días o Todo"),
    exclude_commercial: bool = Query(True),
    categoria: str = Query("", description="Filtrar por categoría"),
    marca: str = Query("", description="Filtrar por marca"),
    stock_min: float = Query(0, description="Stock mínimo"),
):
    data = _get_data(analysis_id)
    max_date = data["max_date"]
    min_date = data["min_date"]

    days_map = {"30": 30, "60": 60, "90": 90, "180": 180}
    inact_days = days_map.get(period, 0)
    d_start = max_date - pd.Timedelta(days=inact_days) if period in days_map else min_date
    d_start = max(d_start, min_date)

    sku = classify_skus(build_sku_summary(data["sales"], data["stock"], d_start, max_date))"""

replacement1 = """def get_stock_sin_ventas(
    analysis_id: str,
    start_date: str = Query(""), end_date: str = Query(""),
    exclude_commercial: bool = Query(True),
    categoria: str = Query("", description="Filtrar por categoría"),
    marca: str = Query("", description="Filtrar por marca"),
    stock_min: float = Query(0, description="Stock mínimo"),
):
    data = _get_data(analysis_id)
    d_start, h_end = _parse_dates(data, start_date, end_date)

    sku = classify_skus(build_sku_summary(data["sales"], data["stock"], d_start, h_end))"""

content = content.replace(target1, replacement1)

# Inside get_stock_sin_ventas
content = content.replace('if period in days_map:', 'if True:')
content = content.replace('"periodo": f"{period} días" if period in days_map else "Todo",', '"start_date": start_date, "end_date": end_date,')

# get_demanda_sin_stock
target2 = """def get_demanda_sin_stock(
    analysis_id: str,
    period: str = Query("Historial completo", description="Periodo de referencia"),
    exclude_commercial: bool = Query(True),
    categoria: str = Query("", description="Filtrar por categoría"),
    marca: str = Query("", description="Filtrar por marca"),
    dias_min: int = Query(0, description="Días mínimos sin stock"),
):
    data = _get_data(analysis_id)
    max_date = data["max_date"]
    min_date = data["min_date"]

    ns_start = max_date - pd.Timedelta(weeks=12) if "12" in period else \\
               max_date - pd.Timedelta(weeks=24) if "24" in period else min_date
    ns_start = max(ns_start, min_date)

    sku = classify_skus(build_sku_summary(data["sales"], data["stock"], ns_start, max_date))"""

replacement2 = """def get_demanda_sin_stock(
    analysis_id: str,
    start_date: str = Query(""), end_date: str = Query(""),
    exclude_commercial: bool = Query(True),
    categoria: str = Query("", description="Filtrar por categoría"),
    marca: str = Query("", description="Filtrar por marca"),
    dias_min: int = Query(0, description="Días mínimos sin stock"),
):
    data = _get_data(analysis_id)
    ns_start, h_end = _parse_dates(data, start_date, end_date)

    sku = classify_skus(build_sku_summary(data["sales"], data["stock"], ns_start, h_end))"""

content = content.replace(target2, replacement2)

# get_quiebres
target3 = """def get_quiebres(
    analysis_id: str,
    period: str = Query("Últimas 4 semanas", description="Periodo para demanda diaria"),
    exclude_commercial: bool = Query(True),
    categoria: str = Query("", description="Filtrar por categoría"),
    marca: str = Query("", description="Filtrar por marca"),
):
    data = _get_data(analysis_id)
    max_date = data["max_date"]
    min_date = data["min_date"]

    offsets = {
        "Últimas 4 semanas": pd.Timedelta(weeks=4),
        "Últimas 8 semanas": pd.Timedelta(weeks=8),
        "Últimas 12 semanas": pd.Timedelta(weeks=12),
    }
    qb_start = max_date - offsets.get(period, pd.Timedelta(weeks=4))
    qb_start = max(qb_start, min_date)

    dias_efectivos = (max_date - qb_start).days
    if dias_efectivos < 1:
        dias_efectivos = 1

    sku = classify_skus(build_sku_summary(data["sales"], data["stock"], qb_start, max_date))"""

replacement3 = """def get_quiebres(
    analysis_id: str,
    start_date: str = Query(""), end_date: str = Query(""),
    exclude_commercial: bool = Query(True),
    categoria: str = Query("", description="Filtrar por categoría"),
    marca: str = Query("", description="Filtrar por marca"),
):
    data = _get_data(analysis_id)
    qb_start, h_end = _parse_dates(data, start_date, end_date)

    dias_efectivos = (h_end - qb_start).days
    if dias_efectivos < 1:
        dias_efectivos = 1

    sku = classify_skus(build_sku_summary(data["sales"], data["stock"], qb_start, h_end))"""

content = content.replace(target3, replacement3)

# get_caidas_crecimiento
target4 = """def get_caidas_crecimiento(
    analysis_id: str,
    period: str = Query("Comparar últimas 8 semanas vs 8 semanas anteriores", description="Periodo comparativo"),
    exclude_commercial: bool = Query(True),
    umbral_pct: float = Query(0, description="Umbral mínimo de variación porcentual"),
):
    data = _get_data(analysis_id)
    max_date = data["max_date"]
    min_date = data["min_date"]

    if "4 semanas" in period:
        ca_start = max_date - pd.Timedelta(days=56)
    elif "8 semanas" in period:
        ca_start = max_date - pd.Timedelta(days=112)
    else:
        ca_start = max_date - pd.Timedelta(days=180)
    ca_start = max(ca_start, min_date)

    sku = classify_skus(build_sku_summary(data["sales"], data["stock"], ca_start, max_date))"""

replacement4 = """def get_caidas_crecimiento(
    analysis_id: str,
    start_date: str = Query(""), end_date: str = Query(""),
    exclude_commercial: bool = Query(True),
    umbral_pct: float = Query(0, description="Umbral mínimo de variación porcentual"),
):
    data = _get_data(analysis_id)
    ca_start, h_end = _parse_dates(data, start_date, end_date)

    sku = classify_skus(build_sku_summary(data["sales"], data["stock"], ca_start, h_end))"""

content = content.replace(target4, replacement4)

with open("main.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Pass 6 done")

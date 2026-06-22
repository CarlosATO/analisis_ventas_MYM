import io

with open("main.py", "r", encoding="utf-8") as f:
    content = f.read()

# get_stock_sin_ventas
target = """def get_stock_sin_ventas(
    analysis_id: str,
    period: str = Query("Todo", description="Período sin ventas: 30, 60, 90, 180 días o Todo"),
    exclude_commercial: bool = Query(True),
    categoria: str = Query(""),
    marca: str = Query(""),
    stock_min: float = Query(0, description="Stock mínimo"),
):
    data = _get_data(analysis_id)
    max_date = data["max_date"]
    min_date = data["min_date"]

    offsets = {
        "30 días": pd.Timedelta(days=30),
        "60 días": pd.Timedelta(days=60),
        "90 días": pd.Timedelta(days=90),
        "180 días": pd.Timedelta(days=180),
    }
    h_start = max_date - offsets.get(period, pd.Timedelta(0))
    if period in ("Todo", "Historial completo"):
        h_start = min_date
    h_start = max(h_start, min_date)

    sku = classify_skus(build_sku_summary(data["sales"], data["stock"], h_start, max_date))"""
replacement = """def get_stock_sin_ventas(
    analysis_id: str,
    start_date: str = Query(""), end_date: str = Query(""),
    exclude_commercial: bool = Query(True),
    categoria: str = Query(""),
    marca: str = Query(""),
    stock_min: float = Query(0, description="Stock mínimo"),
):
    data = _get_data(analysis_id)
    h_start, h_end = _parse_dates(data, start_date, end_date)

    sku = classify_skus(build_sku_summary(data["sales"], data["stock"], h_start, h_end))"""
content = content.replace(target, replacement)

target = """def export_stock_sin_ventas_excel(analysis_id: str):
    data = _get_data(analysis_id)
    sd = get_stock_sin_ventas(analysis_id, "Todo", True, "", "", 0)"""
replacement = """def export_stock_sin_ventas_excel(analysis_id: str, start_date: str = Query(""), end_date: str = Query("")):
    data = _get_data(analysis_id)
    sd = get_stock_sin_ventas(analysis_id, start_date, end_date, True, "", "", 0)"""
content = content.replace(target, replacement)

# get_demanda_sin_stock
target = """def get_demanda_sin_stock(
    analysis_id: str,
    period: str = Query("Historial completo", description="Periodo de referencia"),
    exclude_commercial: bool = Query(True),
    categoria: str = Query(""),
    marca: str = Query(""),
    dias_min: int = Query(0, description="Días mínimos sin stock"),
):
    data = _get_data(analysis_id)
    max_date = data["max_date"]
    min_date = data["min_date"]

    offsets = {
        "Últimas 4 semanas": pd.Timedelta(weeks=4),
        "Últimas 8 semanas": pd.Timedelta(weeks=8),
        "Últimas 12 semanas": pd.Timedelta(weeks=12),
    }
    h_start = max_date - offsets.get(period, pd.Timedelta(0))
    if period in ("Todo el período", "Historial completo"):
        h_start = min_date
    h_start = max(h_start, min_date)

    sku = classify_skus(build_sku_summary(data["sales"], data["stock"], h_start, max_date))"""
replacement = """def get_demanda_sin_stock(
    analysis_id: str,
    start_date: str = Query(""), end_date: str = Query(""),
    exclude_commercial: bool = Query(True),
    categoria: str = Query(""),
    marca: str = Query(""),
    dias_min: int = Query(0, description="Días mínimos sin stock"),
):
    data = _get_data(analysis_id)
    h_start, h_end = _parse_dates(data, start_date, end_date)

    sku = classify_skus(build_sku_summary(data["sales"], data["stock"], h_start, h_end))"""
content = content.replace(target, replacement)

target = """def export_demanda_sin_stock_excel(analysis_id: str):
    data = _get_data(analysis_id)
    dd = get_demanda_sin_stock(analysis_id, "Historial completo", True, 0, 0)"""
replacement = """def export_demanda_sin_stock_excel(analysis_id: str, start_date: str = Query(""), end_date: str = Query("")):
    data = _get_data(analysis_id)
    dd = get_demanda_sin_stock(analysis_id, start_date, end_date, True, "", "", 0)"""
content = content.replace(target, replacement)

# get_quiebres
target = """def get_quiebres(
    analysis_id: str,
    period: str = Query("Últimas 4 semanas", description="Periodo para demanda diaria"),
    exclude_commercial: bool = Query(True),
    categoria: str = Query(""),
    marca: str = Query(""),
):
    data = _get_data(analysis_id)
    max_date = data["max_date"]
    min_date = data["min_date"]

    offsets = {
        "Últimas 4 semanas": pd.Timedelta(weeks=4),
        "Últimas 8 semanas": pd.Timedelta(weeks=8),
        "Últimas 12 semanas": pd.Timedelta(weeks=12),
    }
    h_start = max_date - offsets.get(period, pd.Timedelta(weeks=4))
    if period in ("Todo el período", "Historial completo"):
        h_start = min_date
    h_start = max(h_start, min_date)

    dias_efectivos = (max_date - h_start).days
    if dias_efectivos < 1:
        dias_efectivos = 1

    sku = classify_skus(build_sku_summary(data["sales"], data["stock"], h_start, max_date))"""
replacement = """def get_quiebres(
    analysis_id: str,
    start_date: str = Query(""), end_date: str = Query(""),
    exclude_commercial: bool = Query(True),
    categoria: str = Query(""),
    marca: str = Query(""),
):
    data = _get_data(analysis_id)
    h_start, h_end = _parse_dates(data, start_date, end_date)

    dias_efectivos = (h_end - h_start).days
    if dias_efectivos < 1:
        dias_efectivos = 1

    sku = classify_skus(build_sku_summary(data["sales"], data["stock"], h_start, h_end))"""
content = content.replace(target, replacement)

target = """def export_quiebres_excel(analysis_id: str):
    data = _get_data(analysis_id)
    qd = get_quiebres(analysis_id, "Últimas 4 semanas")"""
replacement = """def export_quiebres_excel(analysis_id: str, start_date: str = Query(""), end_date: str = Query("")):
    data = _get_data(analysis_id)
    qd = get_quiebres(analysis_id, start_date, end_date)"""
content = content.replace(target, replacement)


# get_caidas_crecimiento
target = """def get_caidas_crecimiento(
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
replacement = """def get_caidas_crecimiento(
    analysis_id: str,
    start_date: str = Query(""), end_date: str = Query(""),
    exclude_commercial: bool = Query(True),
    umbral_pct: float = Query(0, description="Umbral mínimo de variación porcentual"),
):
    data = _get_data(analysis_id)
    h_start, h_end = _parse_dates(data, start_date, end_date)

    sku = classify_skus(build_sku_summary(data["sales"], data["stock"], h_start, h_end))"""
content = content.replace(target, replacement)

target = """def export_caidas_crecimiento_excel(analysis_id: str, tipo: str):
    data = _get_data(analysis_id)
    cc = get_caidas_crecimiento(analysis_id, "Comparar últimas 8 semanas vs 8 semanas anteriores", True, 0)"""
replacement = """def export_caidas_crecimiento_excel(analysis_id: str, tipo: str, start_date: str = Query(""), end_date: str = Query("")):
    data = _get_data(analysis_id)
    cc = get_caidas_crecimiento(analysis_id, start_date, end_date, True, 0)"""
content = content.replace(target, replacement)


with open("main.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Pass 3 done")

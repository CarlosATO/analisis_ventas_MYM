import io

with open("main.py", "r", encoding="utf-8") as f:
    content = f.read()

# Replace get_hallazgos
target = """def get_hallazgos(
    analysis_id: str,
    period: str = Query("Todo el período"),
    exclude_commercial: bool = Query(True),
    categoria: str = Query(""),
    marca: str = Query(""),
    stock_min: float = Query(0, description="Stock mínimo"),
    venta_min: float = Query(0, description="Venta mínima"),
):
    data = _get_data(analysis_id)
    hallazgos = _build_hallazgos(
        analysis_id, period, exclude_commercial, categoria, marca, stock_min, venta_min
    )"""
replacement = """def get_hallazgos(
    analysis_id: str,
    start_date: str = Query(""), end_date: str = Query(""),
    exclude_commercial: bool = Query(True),
    categoria: str = Query(""),
    marca: str = Query(""),
    stock_min: float = Query(0, description="Stock mínimo"),
    venta_min: float = Query(0, description="Venta mínima"),
):
    data = _get_data(analysis_id)
    hallazgos = _build_hallazgos(
        analysis_id, start_date, end_date, exclude_commercial, categoria, marca, stock_min, venta_min
    )"""
content = content.replace(target, replacement)

# export_hallazgos_excel
target = """def export_hallazgos_excel(analysis_id: str, tipo: str):
    data = _get_data(analysis_id)
    hallazgos = _build_hallazgos(analysis_id, "Todo el período")"""
replacement = """def export_hallazgos_excel(analysis_id: str, tipo: str, start_date: str = Query(""), end_date: str = Query("")):
    data = _get_data(analysis_id)
    hallazgos = _build_hallazgos(analysis_id, start_date, end_date)"""
content = content.replace(target, replacement)

# export_hallazgos_pdf
target = """def export_hallazgos_pdf(analysis_id: str, tipo: str):
    data = _get_data(analysis_id)
    hallazgos = _build_hallazgos(analysis_id, "Todo el período")"""
replacement = """def export_hallazgos_pdf(analysis_id: str, tipo: str, start_date: str = Query(""), end_date: str = Query("")):
    data = _get_data(analysis_id)
    hallazgos = _build_hallazgos(analysis_id, start_date, end_date)"""
content = content.replace(target, replacement)

# get_pareto
target = """def get_pareto(
    analysis_id: str,
    period: str = Query("Todo el período", description="Período de análisis"),
    exclude_commercial: bool = Query(True),
    categoria: str = Query(""),
    marca: str = Query(""),
    stock_min: float = Query(0, description="Stock mínimo"),
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
    if period == "Todo el período":
        h_start = min_date
    h_start = max(h_start, min_date)

    sku = classify_skus(build_sku_summary(data["sales"], data["stock"], h_start, max_date))"""
replacement = """def get_pareto(
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

# export_pareto_excel
target = """def export_pareto_excel(analysis_id: str):
    data = _get_data(analysis_id)
    pdata = get_pareto(analysis_id, "Todo el período", True)"""
replacement = """def export_pareto_excel(analysis_id: str, start_date: str = Query(""), end_date: str = Query("")):
    data = _get_data(analysis_id)
    pdata = get_pareto(analysis_id, start_date, end_date, True)"""
content = content.replace(target, replacement)

# export_pareto_pdf
target = """def export_pareto_pdf(analysis_id: str):
    data = _get_data(analysis_id)
    pdata = get_pareto(analysis_id, "Todo el período", True)"""
replacement = """def export_pareto_pdf(analysis_id: str, start_date: str = Query(""), end_date: str = Query("")):
    data = _get_data(analysis_id)
    pdata = get_pareto(analysis_id, start_date, end_date, True)"""
content = content.replace(target, replacement)

with open("main.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Pass 2 done")

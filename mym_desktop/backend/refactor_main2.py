import io

with open("main.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Insert _parse_dates function
target1 = """def _get_data(analysis_id: str):
    data = analyses.get(analysis_id)
    if data is None:
        raise HTTPException(404, "Análisis no encontrado")
    return data"""

replacement1 = """def _get_data(analysis_id: str):
    data = analyses.get(analysis_id)
    if data is None:
        raise HTTPException(404, "Análisis no encontrado")
    return data

def _parse_dates(data, start_date: str, end_date: str):
    max_date = data["max_date"]
    min_date = data["min_date"]
    import pandas as pd
    try:
        h_start = pd.to_datetime(start_date) if start_date else min_date
    except:
        h_start = min_date

    try:
        h_end = pd.to_datetime(end_date) if end_date else max_date
    except:
        h_end = max_date

    h_start = max(h_start, min_date)
    h_end = min(h_end, max_date)
    
    if h_start > h_end:
        h_start, h_end = h_end, h_start
        
    return h_start, h_end"""

content = content.replace(target1, replacement1)

# 2. Update _build_hallazgos
target2 = """def _build_hallazgos(
    analysis_id: str, period: str,
    exclude_commercial: bool = True,
    categoria: str = "", marca: str = "",
    stock_min: float = 0, venta_min: float = 0,
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

replacement2 = """def _build_hallazgos(
    analysis_id: str, start_date: str = "", end_date: str = "",
    exclude_commercial: bool = True,
    categoria: str = "", marca: str = "",
    stock_min: float = 0, venta_min: float = 0,
):
    data = _get_data(analysis_id)
    h_start, h_end = _parse_dates(data, start_date, end_date)

    sku = classify_skus(build_sku_summary(data["sales"], data["stock"], h_start, h_end))"""

content = content.replace(target2, replacement2)

with open("main.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Pass 1 done")

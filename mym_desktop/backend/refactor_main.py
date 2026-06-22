import re

with open("mym_desktop/backend/main.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update _build_hallazgos definition
content = re.sub(
    r"def _build_hallazgos\(\s*analysis_id: str, period: str,",
    r"def _build_hallazgos(\n    analysis_id: str,\n    start_date: str = \"\", end_date: str = \"\",",
    content
)

# 2. Update logic inside _build_hallazgos
logic_replacement = """    data = _get_data(analysis_id)
    max_date = data["max_date"]
    min_date = data["min_date"]

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

    sku = classify_skus(build_sku_summary(data["sales"], data["stock"], h_start, h_end))"""

# find the existing logic
existing_logic_pattern = r'    data = _get_data\(analysis_id\)\s+max_date = data\["max_date"\]\s+min_date = data\["min_date"\]\s+offsets = \{.*?\}.*?sku = classify_skus\(build_sku_summary\(data\["sales"\], data\["stock"\], h_start, max_date\)\)'

content = re.sub(existing_logic_pattern, logic_replacement, content, flags=re.DOTALL)

# 3. Update route parameters
content = re.sub(
    r"period: str = Query\([^)]+\),",
    r'start_date: str = Query(""),\n    end_date: str = Query(""),',
    content
)

# 4. Update get_ calls inside main.py
# get_hallazgos(analysis_id, "Todo el período", ...
content = re.sub(
    r'get_hallazgos\(analysis_id, "[^"]+",',
    r'get_hallazgos(analysis_id, "", "",',
    content
)
content = re.sub(
    r'get_pareto\(analysis_id, "[^"]+",',
    r'get_pareto(analysis_id, "", "",',
    content
)
content = re.sub(
    r'get_stock_sin_ventas\(analysis_id, "[^"]+",',
    r'get_stock_sin_ventas(analysis_id, "", "",',
    content
)
content = re.sub(
    r'get_demanda_sin_stock\(analysis_id, "[^"]+",',
    r'get_demanda_sin_stock(analysis_id, "", "",',
    content
)
content = re.sub(
    r'get_quiebres\(analysis_id, "[^"]+",',
    r'get_quiebres(analysis_id, "", "",',
    content
)
content = re.sub(
    r'get_caidas_crecimiento\(analysis_id, "[^"]+",',
    r'get_caidas_crecimiento(analysis_id, "", "",',
    content
)
content = re.sub(
    r'_build_hallazgos\(analysis_id, "[^"]+"\)',
    r'_build_hallazgos(analysis_id, "", "")',
    content
)

# 5. Update the individual route functions to parse dates
# For Pareto, Stock sin Ventas, Demanda sin stock, Quiebres, Caidas
def replace_route_logic(content, func_name):
    # Find the function body start
    pattern = rf"(def {func_name}\([^)]+\):\s+data = _get_data\(analysis_id\)\s+max_date = data\[\"max_date\"\]\s+min_date = data\[\"min_date\"\]\s+)(.*?)(\s+sku = )"
    
    # We replace the inside logic (the `if period ... ca_start = ...`) with our start_date / end_date parser
    parser = r"""
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
"""
    
    # Actually wait, some of them define it differently. Let's do it carefully.
    return content

content = replace_route_logic(content, "get_pareto")

with open("mym_desktop/backend/main.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Done")

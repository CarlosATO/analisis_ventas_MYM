import io

with open("main.py", "r", encoding="utf-8") as f:
    content = f.read()

target_parse = """def _parse_dates(data, start_date: str, end_date: str):
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

replacement_parse = """def _parse_dates(data, start_date: str, end_date: str):
    max_date = data["max_date"]
    min_date = data["min_date"]
    import pandas as pd
    
    if not start_date:
        h_start = min_date
    else:
        h_start = pd.to_datetime(start_date, errors="coerce", dayfirst=False)
        if pd.isna(h_start):
            raise HTTPException(400, "Formato de fecha inválido. Use YYYY-MM-DD.")
            
    if not end_date:
        h_end = max_date
    else:
        h_end = pd.to_datetime(end_date, errors="coerce", dayfirst=False)
        if pd.isna(h_end):
            raise HTTPException(400, "Formato de fecha inválido. Use YYYY-MM-DD.")

    h_start = max(h_start, min_date)
    h_end = min(h_end, max_date)
    
    if h_start > h_end:
        h_start, h_end = h_end, h_start
        
    return h_start, h_end"""

content = content.replace(target_parse, replacement_parse)

target_upload = """            "date_range": {
                "min": min_date.strftime("%d-%m-%Y"),
                "max": max_date.strftime("%d-%m-%Y"),
            },"""

replacement_upload = """            "date_range": {
                "min": min_date.strftime("%Y-%m-%d"),
                "max": max_date.strftime("%Y-%m-%d"),
            },"""

content = content.replace(target_upload, replacement_upload)

with open("main.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Dates fixed in main.py")

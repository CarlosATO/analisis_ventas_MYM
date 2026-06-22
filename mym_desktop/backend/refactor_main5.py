import io
import re

with open("main.py", "r", encoding="utf-8") as f:
    content = f.read()

# Replace "periodo": period  with  "start_date": start_date, "end_date": end_date
content = content.replace('"periodo": period,', '"start_date": start_date, "end_date": end_date,')

# Replace pdf.cell(18, 5, "PERIODO:") with pdf.cell(35, 5, "RANGO ANALIZADO:")
content = content.replace('pdf.cell(18, 5, "PERIODO:")', 'pdf.cell(35, 5, "RANGO ANALIZADO:")')

# Replace f'{filtros.get("periodo", "")}' with f'{filtros.get("start_date", "")} a {filtros.get("end_date", "")}'
content = content.replace('f\'{filtros.get("periodo", "")}\'', 'f\'{filtros.get("start_date", "")} a {filtros.get("end_date", "")}\'')

# Also in _reposicion_payload_df the export says "Período a analizar: ... días"
# This shouldn't be touched because Reposicion is untouched.

with open("main.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Pass 5 done")

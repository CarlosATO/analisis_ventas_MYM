import io
import re

with open("src/lib/api.ts", "r", encoding="utf-8") as f:
    content = f.read()

# Replace period with start_date and end_date in parameters
content = re.sub(
    r"period\?:\s*string",
    r"start_date?: string; end_date?: string",
    content
)

# In the params dictionaries, replace period: opts?.period with start_date: opts?.start_date, end_date: opts?.end_date
content = re.sub(
    r"period:\s*opts\?\.period",
    r"start_date: opts?.start_date, end_date: opts?.end_date",
    content
)

# Export URLs need to include start_date and end_date
def update_export(func_name, route, has_tipo=False):
    global content
    if has_tipo:
        target = f"""export function {func_name}(analysisId: string, tipo: string): string {{
  return `${{API}}/api/${{analysisId}}{route}/${{tipo}}`
}}"""
        replacement = f"""export function {func_name}(analysisId: string, tipo: string, startDate?: string, endDate?: string): string {{
  const params = new URLSearchParams()
  if (startDate) params.append("start_date", startDate)
  if (endDate) params.append("end_date", endDate)
  const qs = params.toString() ? "?" + params.toString() : ""
  return `${{API}}/api/${{analysisId}}{route}/${{tipo}}${{qs}}`
}}"""
        content = content.replace(target, replacement)
    else:
        target = f"""export function {func_name}(analysisId: string): string {{
  return `${{API}}/api/${{analysisId}}{route}`
}}"""
        replacement = f"""export function {func_name}(analysisId: string, startDate?: string, endDate?: string): string {{
  const params = new URLSearchParams()
  if (startDate) params.append("start_date", startDate)
  if (endDate) params.append("end_date", endDate)
  const qs = params.toString() ? "?" + params.toString() : ""
  return `${{API}}/api/${{analysisId}}{route}${{qs}}`
}}"""
        content = content.replace(target, replacement)

update_export("getHallazgosExportUrl", "/export/hallazgos", True)
update_export("getParetoExportUrl", "/export/pareto")
update_export("getStockSinVentasExportUrl", "/export/stock-sin-ventas")
update_export("getDemandaExportUrl", "/export/demanda-sin-stock")
update_export("getQuiebresExportUrl", "/export/quiebres")
update_export("getCaidasExportUrl", "/export/caidas-crecimiento", True)

with open("src/lib/api.ts", "w", encoding="utf-8") as f:
    f.write(content)

print("api.ts refactor done")

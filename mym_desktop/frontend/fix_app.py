import io
import re

with open("src/App.tsx", "r", encoding="utf-8") as f:
    content = f.read()

# Replace Hallazgos FilterSelect
content = re.sub(
    r'<FilterSelect label="Per[^\"]+" value=\{hPeriod\} onChange=\{v => \{ setHPeriod\(v\); setHallazgos\(null\) \}\}\n\s+options=\{[^}]+\}\]\} />',
    r'<FilterDateRange startValue={hStartDate} endValue={hEndDate} onStartChange={v => {setHStartDate(v); setHallazgos(null)}} onEndChange={v => {setHEndDate(v); setHallazgos(null)}} />',
    content
)

# Replace Stock SV FilterSelect
content = re.sub(
    r'<FilterSelect label="Per[^\"]+ sin ventas" value=\{ssPeriod\} onChange=\{v => \{ setSsPeriod\(v\); setStockSv\(null\) \}\}\n\s+options=\{[^}]+\}\]\} />',
    r'<FilterDateRange startValue={ssStartDate} endValue={ssEndDate} onStartChange={v => {setSsStartDate(v); setStockSv(null)}} onEndChange={v => {setSsEndDate(v); setStockSv(null)}} />',
    content
)

# Replace Demanda FilterSelect
content = re.sub(
    r'<FilterSelect label="Per[^\"]+" value=\{dPeriod\} onChange=\{v => \{ setDPeriod\(v\); setDemanda\(null\) \}\}\n\s+options=\{[^}]+\}\]\} />',
    r'<FilterDateRange startValue={dStartDate} endValue={dEndDate} onStartChange={v => {setDStartDate(v); setDemanda(null)}} onEndChange={v => {setDEndDate(v); setDemanda(null)}} />',
    content
)

# Replace Quiebres FilterSelect
content = re.sub(
    r'<FilterSelect label="Per[^\"]+" value=\{qPeriod\} onChange=\{v => \{ setQPeriod\(v\); setQuiebres\(null\) \}\}\n\s+options=\{[^}]+\}\]\} />',
    r'<FilterDateRange startValue={qStartDate} endValue={qEndDate} onStartChange={v => {setQStartDate(v); setQuiebres(null)}} onEndChange={v => {setQEndDate(v); setQuiebres(null)}} />',
    content
)

# Replace Caidas FilterSelect
content = re.sub(
    r'<FilterSelect label="Comparaci.n" value=\{cPeriod\} onChange=\{v => \{ setCPeriod\(v\); setCaidas\(null\) \}\}\n\s+options=\{[^}]+\}\n\s+\{[^}]+\}\]\} />',
    r'<FilterDateRange startValue={cStartDate} endValue={cEndDate} onStartChange={v => {setCStartDate(v); setCaidas(null)}} onEndChange={v => {setCEndDate(v); setCaidas(null)}} />',
    content
)

# Fix Pareto export URL to pass start/end dates
content = content.replace(
    'getParetoExportUrl(analysisId)',
    'getParetoExportUrl(analysisId, pStartDate, pEndDate)'
)
content = content.replace(
    'getStockSinVentasExportUrl(analysisId)',
    'getStockSinVentasExportUrl(analysisId, ssStartDate, ssEndDate)'
)
content = content.replace(
    'getDemandaExportUrl(analysisId)',
    'getDemandaExportUrl(analysisId, dStartDate, dEndDate)'
)
content = content.replace(
    'getQuiebresExportUrl(analysisId)',
    'getQuiebresExportUrl(analysisId, qStartDate, qEndDate)'
)

content = re.sub(
    r'getHallazgosExportUrl\(analysisId,\s*"([^"]+)"\)',
    r'getHallazgosExportUrl(analysisId, "\1", hStartDate, hEndDate)',
    content
)
content = re.sub(
    r'getCaidasCrecimientoExportUrl\(analysisId,\s*"([^"]+)"\)',
    r'getCaidasExportUrl(analysisId, "\1", cStartDate, cEndDate)',
    content
)

# Also, pareto didn't have a FilterDateRange because I didn't see one. But we should add it!
content = content.replace(
    '<FilterCheckbox label="Excluir conceptos comerciales" checked={pExclude}',
    '<FilterDateRange startValue={pStartDate} endValue={pEndDate} onStartChange={v => {setPStartDate(v); setPareto(null)}} onEndChange={v => {setPEndDate(v); setPareto(null)}} />\n              <FilterCheckbox label="Excluir conceptos comerciales" checked={pExclude}'
)

with open("src/App.tsx", "w", encoding="utf-8") as f:
    f.write(content)
print("Fix pass done")

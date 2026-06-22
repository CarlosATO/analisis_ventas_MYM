import io
import re

with open("src/App.tsx", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Insert helper components before `export default function App()`
components_code = """function FilterDateRange({
  startValue, endValue, onStartChange, onEndChange
}: {
  startValue: string, endValue: string,
  onStartChange: (v: string) => void, onEndChange: (v: string) => void
}) {
  return (
    <div className="flex items-center gap-4 text-sm text-gray-700 bg-gray-50 px-3 py-2 rounded-md border border-gray-200">
      <div className="flex items-center gap-2">
        <label className="font-semibold whitespace-nowrap">Desde:</label>
        <input type="date" value={startValue} max={endValue || undefined} onChange={e => onStartChange(e.target.value)} className="border-gray-300 rounded px-2 py-1 text-sm bg-white focus:ring-blue-500 focus:border-blue-500" />
      </div>
      <div className="flex items-center gap-2">
        <label className="font-semibold whitespace-nowrap">Hasta:</label>
        <input type="date" value={endValue} min={startValue || undefined} onChange={e => onEndChange(e.target.value)} className="border-gray-300 rounded px-2 py-1 text-sm bg-white focus:ring-blue-500 focus:border-blue-500" />
      </div>
    </div>
  )
}

function DateRangeBadge({ start, end }: { start?: string, end?: string }) {
  if (!start && !end) return null;
  const fmt = (d: string) => {
    if (!d) return "";
    const parts = d.split("-");
    if (parts.length === 3) return `${parts[2]}-${parts[1]}-${parts[0]}`;
    return d;
  }
  return (
    <div className="bg-indigo-50 border border-indigo-200 text-indigo-800 px-3 py-2 rounded-md mb-4 font-medium text-sm flex items-center gap-2 shadow-sm w-max">
      <svg className="w-5 h-5 opacity-80" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
      Rango analizado: {fmt(start!)} a {fmt(end!)}
    </div>
  )
}

export default function App() {"""
content = content.replace("export default function App() {", components_code)

# 2. Replace state definitions
content = re.sub(r'const \[hPeriod, setHPeriod\] = useState\([^)]+\)', 'const [hStartDate, setHStartDate] = useState("")\\n  const [hEndDate, setHEndDate] = useState("")', content)
content = re.sub(r'const \[pPeriod, setPPeriod\] = useState\([^)]+\)', 'const [pStartDate, setPStartDate] = useState("")\\n  const [pEndDate, setPEndDate] = useState("")', content)
content = re.sub(r'const \[ssPeriod, setSsPeriod\] = useState\([^)]+\)', 'const [ssStartDate, setSsStartDate] = useState("")\\n  const [ssEndDate, setSsEndDate] = useState("")', content)
content = re.sub(r'const \[dPeriod, setDPeriod\] = useState\([^)]+\)', 'const [dStartDate, setDStartDate] = useState("")\\n  const [dEndDate, setDEndDate] = useState("")', content)
content = re.sub(r'const \[qPeriod, setQPeriod\] = useState\([^)]+\)', 'const [qStartDate, setQStartDate] = useState("")\\n  const [qEndDate, setQEndDate] = useState("")', content)
content = re.sub(r'const \[cPeriod, setCPeriod\] = useState\([^)]+\)', 'const [cStartDate, setCStartDate] = useState("")\\n  const [cEndDate, setCEndDate] = useState("")', content)

# 3. Inject default assignments inside handleCargarDatos
# find: setFilesChanged(false)
injection = """        setFilesChanged(false)
        setHStartDate(res.date_range.min)
        setHEndDate(res.date_range.max)
        setPStartDate(res.date_range.min)
        setPEndDate(res.date_range.max)
        setSsStartDate(res.date_range.min)
        setSsEndDate(res.date_range.max)
        setDStartDate(res.date_range.min)
        setDEndDate(res.date_range.max)
        setQStartDate(res.date_range.min)
        setQEndDate(res.date_range.max)
        setCStartDate(res.date_range.min)
        setCEndDate(res.date_range.max)"""
content = content.replace("setFilesChanged(false)", injection)

# 4. Replace API call dependencies
content = content.replace("period: hPeriod", "start_date: hStartDate, end_date: hEndDate")
content = content.replace("period: pPeriod", "start_date: pStartDate, end_date: pEndDate")
content = content.replace("period: ssPeriod", "start_date: ssStartDate, end_date: ssEndDate")
content = content.replace("period: dPeriod", "start_date: dStartDate, end_date: dEndDate")
content = content.replace("period: qPeriod", "start_date: qStartDate, end_date: qEndDate")
content = content.replace("period: cPeriod", "start_date: cStartDate, end_date: cEndDate")

# 5. Replace dependency arrays
content = re.sub(r'hPeriod,([^\]]+)\]\)', r'hStartDate, hEndDate,\1])', content)
content = re.sub(r'pPeriod,([^\]]+)\]\)', r'pStartDate, pEndDate,\1])', content)
content = re.sub(r'ssPeriod,([^\]]+)\]\)', r'ssStartDate, ssEndDate,\1])', content)
content = re.sub(r'dPeriod,([^\]]+)\]\)', r'dStartDate, dEndDate,\1])', content)
content = re.sub(r'qPeriod,([^\]]+)\]\)', r'qStartDate, qEndDate,\1])', content)
content = re.sub(r'cPeriod,([^\]]+)\]\)', r'cStartDate, cEndDate,\1])', content)

# 6. Replace FilterSelect UI
import re

# We need to find and replace the <FilterSelect label="Período" ... /> blocks.
content = re.sub(
    r'<FilterSelect label="Período"[^>]+hPeriod[^>]+/>',
    r'<FilterDateRange startValue={hStartDate} endValue={hEndDate} onStartChange={v => {setHStartDate(v); setHallazgos(null)}} onEndChange={v => {setHEndDate(v); setHallazgos(null)}} />',
    content
)
content = re.sub(
    r'<FilterSelect label="Período"[^>]+pPeriod[^>]+/>',
    r'<FilterDateRange startValue={pStartDate} endValue={pEndDate} onStartChange={v => {setPStartDate(v); setPareto(null)}} onEndChange={v => {setPEndDate(v); setPareto(null)}} />',
    content
)
content = re.sub(
    r'<FilterSelect label="Período sin ventas"[^>]+ssPeriod[^>]+/>',
    r'<FilterDateRange startValue={ssStartDate} endValue={ssEndDate} onStartChange={v => {setSsStartDate(v); setStockSv(null)}} onEndChange={v => {setSsEndDate(v); setStockSv(null)}} />',
    content
)
content = re.sub(
    r'<FilterSelect label="Período"[^>]+dPeriod[^>]+/>',
    r'<FilterDateRange startValue={dStartDate} endValue={dEndDate} onStartChange={v => {setDStartDate(v); setDemanda(null)}} onEndChange={v => {setDEndDate(v); setDemanda(null)}} />',
    content
)
content = re.sub(
    r'<FilterSelect label="Período"[^>]+qPeriod[^>]+/>',
    r'<FilterDateRange startValue={qStartDate} endValue={qEndDate} onStartChange={v => {setQStartDate(v); setQuiebres(null)}} onEndChange={v => {setQEndDate(v); setQuiebres(null)}} />',
    content
)
content = re.sub(
    r'<FilterSelect label="Comparación"[^>]+cPeriod[^>]+/>',
    r'<FilterDateRange startValue={cStartDate} endValue={cEndDate} onStartChange={v => {setCStartDate(v); setCaidas(null)}} onEndChange={v => {setCEndDate(v); setCaidas(null)}} />',
    content
)

# 7. Add DateRangeBadge inside the views
# We look for <div className="overflow-x-auto"> or similar where we can safely prepend the badge.
# Or better, just after the <FilterPanel> inside the tabs.
content = content.replace('</FilterPanel>\n              {hallazgos &&', '</FilterPanel>\n              {hallazgos && <DateRangeBadge start={hallazgos.filtros?.start_date} end={hallazgos.filtros?.end_date} />}\n              {hallazgos &&')
content = content.replace('</FilterPanel>\n              {pareto &&', '</FilterPanel>\n              {pareto && <DateRangeBadge start={pareto.filtros?.start_date} end={pareto.filtros?.end_date} />}\n              {pareto &&')
content = content.replace('</FilterPanel>\n              {stockSv &&', '</FilterPanel>\n              {stockSv && <DateRangeBadge start={stockSv.filtros?.start_date} end={stockSv.filtros?.end_date} />}\n              {stockSv &&')
content = content.replace('</FilterPanel>\n              {demanda &&', '</FilterPanel>\n              {demanda && <DateRangeBadge start={demanda.filtros?.start_date} end={demanda.filtros?.end_date} />}\n              {demanda &&')
content = content.replace('</FilterPanel>\n              {quiebres &&', '</FilterPanel>\n              {quiebres && <DateRangeBadge start={quiebres.filtros?.start_date} end={quiebres.filtros?.end_date} />}\n              {quiebres &&')
content = content.replace('</FilterPanel>\n              {caidas &&', '</FilterPanel>\n              {caidas && <DateRangeBadge start={caidas.filtros?.start_date} end={caidas.filtros?.end_date} />}\n              {caidas &&')

# 8. FilterBadge removal for 'Período' in Reports, since DateBadge handles it now.
# Replace `<FilterBadge label="Período" value={filtros.periodo} />` with nothing
content = re.sub(r'<FilterBadge label="Período" value=\{filtros\.periodo\} />\n', '', content)

with open("src/App.tsx", "w", encoding="utf-8") as f:
    f.write(content)

print("App.tsx refactor complete")

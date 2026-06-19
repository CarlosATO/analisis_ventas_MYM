import { useState, useCallback } from "react"
import { Upload, Download, TrendingDown, TrendingUp, AlertTriangle, BarChart3, Package, ShoppingCart, ShieldAlert, Filter } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardTitle, CardValue } from "@/components/ui/card"
import { Table, THead, TBody, TR, TH, TD } from "@/components/ui/table"
import { Dialog } from "@/components/ui/dialog"
import { uploadFiles, getWeekly, getWeekDetail, getWeeklyExportUrl, getHallazgos, getHallazgosExportUrl, getPareto, getParetoExportUrl, getStockSinVentas, getStockSinVentasExportUrl, getDemandaSinStock, getDemandaExportUrl, getQuiebres, getQuiebresExportUrl, getCaidasCrecimiento, getCaidasCrecimientoExportUrl } from "@/lib/api"
import type { UploadResponse, WeeklyPoint, WeekDetailResponse, HallazgosResponse, ParetoResponse, StockSinVentasResponse, DemandaSinStockResponse, QuiebresResponse, CaidasCrecimientoResponse, ProductRow, FiltrosActivos } from "@/types"
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Line, ComposedChart } from "recharts"

const _clp = new Intl.NumberFormat("es-CL", { style: "currency", currency: "CLP", maximumFractionDigits: 0 })
const fmtMoney = (n: number) => _clp.format(n)
const fmtPct = (n: number | null) => n != null ? `${(n * 100).toFixed(1)}%` : "-"
const fmtDate = (d: string) => { try { return d ? new Date(d).toLocaleDateString("es-CL") : "-" } catch { return d } }

type Tab = "resumen" | "hallazgos" | "pareto" | "stock" | "demanda" | "quiebres" | "caidas"

// ── Filter display component ──
function FilterBadge({ label, value }: { label: string; value: string | number | boolean | undefined | null }) {
  if (value === undefined || value === null || value === "" || value === false) return null
  const display = typeof value === "boolean" ? (value ? "sí" : "no") : String(value)
  return (
    <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full" style={{ backgroundColor: "var(--muted)", color: "var(--foreground)" }}>
      <Filter className="h-3 w-3" />
      {label}: <strong>{display}</strong>
    </span>
  )
}

function FiltrosDisplay({ filtros, count }: { filtros?: FiltrosActivos; count?: number }) {
  if (!filtros) return null
  return (
    <div className="flex flex-wrap gap-2 mb-3">
      <FilterBadge label="Período" value={filtros.periodo} />
      <FilterBadge label="Excluir comerciales" value={filtros.excluir_conceptos_comerciales} />
      <FilterBadge label="Categoría" value={filtros.categoria && filtros.categoria !== "Todas" ? filtros.categoria : undefined} />
      <FilterBadge label="Marca" value={filtros.marca && filtros.marca !== "Todas" ? filtros.marca : undefined} />
      <FilterBadge label="Stock mín" value={filtros.stock_minimo && filtros.stock_minimo > 0 ? filtros.stock_minimo : undefined} />
      {count !== undefined && (
        <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full font-semibold" style={{ backgroundColor: "var(--accent)", color: "#fff" }}>
          Resultado: {count.toLocaleString("es-CL")}
        </span>
      )}
    </div>
  )
}

function ProductTable({ productos, showMargen = true, showStock = true }: { productos: ProductRow[]; showMargen?: boolean; showStock?: boolean }) {
  return (
    <Table>
      <THead>
        <TR><TH>#</TH><TH>SKU</TH><TH>Producto</TH><TH className="text-right">Venta</TH><TH className="text-right">Unidades</TH>
          {showMargen && <TH className="text-right">Margen</TH>}
          {showStock && <TH className="text-right">Stock</TH>}
        </TR>
      </THead>
      <TBody>
        {productos.map(p => (
          <TR key={p.ranking}>
            <TD className="font-medium">{p.ranking}</TD>
            <TD style={{ color: "var(--muted)", fontSize: "0.8rem" }}>{p.sku}</TD>
            <TD>{p.producto}</TD>
            <TD className="text-right font-medium">{fmtMoney(p.venta)}</TD>
            <TD className="text-right">{p.unidades.toLocaleString("es-CL")}</TD>
            {showMargen && <TD className="text-right">{fmtMoney(p.margen)}</TD>}
            {showStock && <TD className="text-right">{p.stock_disponible.toLocaleString("es-CL")}</TD>}
          </TR>
        ))}
      </TBody>
    </Table>
  )
}

function HallazgoCard({ icon, title, summary, priority, onView, onExport }: {
  icon: React.ReactNode; title: string; summary: string; priority: "Alta" | "Media" | "Baja"; onView: () => void; onExport?: () => void
}) {
  const borderColor = priority === "Alta" ? "#dc2626" : priority === "Media" ? "#d97706" : "#2563eb"
  return (
    <div className="rounded-lg border p-4 flex flex-col gap-3" style={{ borderLeft: `5px solid ${borderColor}`, borderColor: "var(--border)", backgroundColor: "var(--card)" }}>
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2">
          <span style={{ color: borderColor }}>{icon}</span>
          <h3 className="font-semibold text-sm" style={{ color: "var(--foreground)" }}>{title}</h3>
        </div>
        <span className="text-xs font-bold px-2 py-0.5 rounded-full text-white" style={{ backgroundColor: borderColor }}>
          {priority === "Alta" ? "Crítico" : priority === "Media" ? "Relevante" : "Info"}
        </span>
      </div>
      <p className="text-sm" style={{ color: "var(--muted)" }}>{summary}</p>
      <div className="flex gap-2 mt-auto">
        <Button variant="secondary" size="sm" onClick={onView}>Ver productos</Button>
        {onExport && <Button variant="ghost" size="sm" onClick={onExport}><Download className="h-3 w-3 mr-1" />Excel</Button>}
      </div>
    </div>
  )
}

// ── Filter Panel Component ──
function FilterPanel({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex flex-wrap items-end gap-3 p-4 rounded-lg border mb-4" style={{ borderColor: "var(--border)", backgroundColor: "var(--card)" }}>
      {children}
    </div>
  )
}

function FilterSelect({ label, value, onChange, options }: {
  label: string; value: string; onChange: (v: string) => void; options: { value: string; label: string }[]
}) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-xs font-medium" style={{ color: "var(--muted)" }}>{label}</label>
      <select value={value} onChange={e => onChange(e.target.value)}
        className="text-sm rounded-md border px-3 py-1.5" style={{ borderColor: "var(--border)", backgroundColor: "var(--background)", color: "var(--foreground)" }}>
        {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </div>
  )
}

function FilterCheckbox({ label, checked, onChange }: { label: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="flex items-center gap-2 text-sm cursor-pointer" style={{ color: "var(--foreground)" }}>
      <input type="checkbox" checked={checked} onChange={e => onChange(e.target.checked)} className="rounded" />
      {label}
    </label>
  )
}

// ════════════════════════════════════
// APP
// ════════════════════════════════════

export default function App() {
  const [salesFile, setSalesFile] = useState<File | null>(null)
  const [stockFile, setStockFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [uploaded, setUploaded] = useState<UploadResponse | null>(null)
  const [analysisId, setAnalysisId] = useState<string | null>(null)
  const [tab, setTab] = useState<Tab>("resumen")
  const [theme, setTheme] = useState<"light" | "dark">("light")
  const [weeklyData, setWeeklyData] = useState<WeeklyPoint[]>([])
  const [detail, setDetail] = useState<WeekDetailResponse | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)

  // Hallazgos
  const [hallazgos, setHallazgos] = useState<HallazgosResponse | null>(null)
  const [hallazgosModal, setHallazgosModal] = useState<{ title: string; productos: ProductRow[]; exportUrl: string } | null>(null)
  const [hPeriod, setHPeriod] = useState("Todo el período")
  const [hCategoria, setHCategoria] = useState("")
  const [hMarca, setHMarca] = useState("")
  const [hExclude, setHExclude] = useState(true)

  // Pareto
  const [pareto, setPareto] = useState<ParetoResponse | null>(null)
  const [pExclude, setPExclude] = useState(true)

  // Stock SV
  const [stockSv, setStockSv] = useState<StockSinVentasResponse | null>(null)
  const [ssPeriod, setSsPeriod] = useState("Todo")
  const [ssExclude, setSsExclude] = useState(true)
  const [ssCategoria, setSsCategoria] = useState("")
  const [ssMarca, setSsMarca] = useState("")
  const [ssStockMin, setSsStockMin] = useState(0)

  // Demanda
  const [demanda, setDemanda] = useState<DemandaSinStockResponse | null>(null)
  const [dPeriod, setDPeriod] = useState("Historial completo")
  const [dExclude, setDExclude] = useState(true)

  // Quiebres
  const [quiebres, setQuiebres] = useState<QuiebresResponse | null>(null)
  const [qPeriod, setQPeriod] = useState("Últimas 4 semanas")
  const [qExclude, setQExclude] = useState(true)

  // Caidas
  const [caidas, setCaidas] = useState<CaidasCrecimientoResponse | null>(null)
  const [cPeriod, setCPeriod] = useState("Comparar últimas 8 semanas vs 8 semanas anteriores")
  const [cExclude, setCExclude] = useState(true)

  const isDark = theme === "dark"
  const chartText = isDark ? "#f8fafc" : "#0f172a"
  const chartGrid = isDark ? "#334155" : "#e2e8f0"
  const chartAccent = isDark ? "#38bdf8" : "#0284c7"

  const toggleTheme = () => {
    const next = theme === "light" ? "dark" : "light"
    setTheme(next)
    document.documentElement.classList.toggle("dark", next === "dark")
  }

  const handleUpload = async () => {
    if (!salesFile || !stockFile) return
    setLoading(true)
    try {
      const res = await uploadFiles(salesFile, stockFile)
      setUploaded(res)
      setAnalysisId(res.analysis_id)
      const weekly = await getWeekly(res.analysis_id)
      setWeeklyData(weekly.weeks.filter(w => w.venta >= 0))
      setTab("resumen")
    } catch (e: any) { alert(e.message) }
    finally { setLoading(false) }
  }

  const loadHallazgos = useCallback(async () => {
    if (!analysisId) return
    setHallazgos(await getHallazgos(analysisId, { period: hPeriod, exclude_commercial: hExclude, categoria: hCategoria, marca: hMarca }))
  }, [analysisId, hPeriod, hExclude, hCategoria, hMarca])

  const loadPareto = useCallback(async () => {
    if (!analysisId) return
    setPareto(await getPareto(analysisId, { exclude_commercial: pExclude }))
  }, [analysisId, pExclude])

  const loadStockSv = useCallback(async () => {
    if (!analysisId) return
    setStockSv(await getStockSinVentas(analysisId, { period: ssPeriod, exclude_commercial: ssExclude, categoria: ssCategoria, marca: ssMarca, stock_min: ssStockMin || undefined }))
  }, [analysisId, ssPeriod, ssExclude, ssCategoria, ssMarca, ssStockMin])

  const loadDemanda = useCallback(async () => {
    if (!analysisId) return
    setDemanda(await getDemandaSinStock(analysisId, { period: dPeriod, exclude_commercial: dExclude }))
  }, [analysisId, dPeriod, dExclude])

  const loadQuiebres = useCallback(async () => {
    if (!analysisId) return
    setQuiebres(await getQuiebres(analysisId, { period: qPeriod, exclude_commercial: qExclude }))
  }, [analysisId, qPeriod, qExclude])

  const loadCaidas = useCallback(async () => {
    if (!analysisId) return
    setCaidas(await getCaidasCrecimiento(analysisId, { period: cPeriod, exclude_commercial: cExclude }))
  }, [analysisId, cPeriod, cExclude])

  const switchTab = async (t: Tab) => {
    setTab(t)
    if (!analysisId) return
    try {
      if (t === "hallazgos") await loadHallazgos()
      else if (t === "pareto") await loadPareto()
      else if (t === "stock") await loadStockSv()
      else if (t === "demanda") await loadDemanda()
      else if (t === "quiebres") await loadQuiebres()
      else if (t === "caidas") await loadCaidas()
    } catch (e: any) { alert(e.message) }
  }

  const handleBarClick = async (data: any) => {
    if (!data?.activePayload?.[0]?.payload || !analysisId) return
    const p = data.activePayload[0].payload as WeeklyPoint
    setDetailLoading(true)
    try { setDetail(await getWeekDetail(analysisId, p.year, p.week)) }
    catch (e: any) { alert(e.message) }
    finally { setDetailLoading(false) }
  }

  const TABS: { key: Tab; label: string }[] = [
    { key: "resumen", label: "Evolución semanal" },
    { key: "hallazgos", label: "Hallazgos" },
    { key: "pareto", label: "Pareto" },
    { key: "stock", label: "Stock sin ventas" },
    { key: "demanda", label: "Demanda sin stock" },
    { key: "quiebres", label: "Quiebres" },
    { key: "caidas", label: "Caídas y crecimiento" },
  ]

  return (
    <div className="min-h-screen" style={{ backgroundColor: "var(--background)" }}>
      <header className="border-b" style={{ borderColor: "var(--border)", backgroundColor: "var(--card)" }}>
        <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
          <h1 className="text-lg font-bold" style={{ color: "var(--foreground)" }}>Dashboard MYM</h1>
          <button onClick={toggleTheme} className="text-sm px-3 py-1.5 rounded-md border cursor-pointer" style={{ borderColor: "var(--border)", color: "var(--foreground)" }}>
            {theme === "light" ? "Oscuro" : "Claro"}
          </button>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-6 space-y-6">
        <Card>
          <CardTitle>Carga de archivos</CardTitle>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-3">
            <div>
              <label className="block text-sm font-medium mb-1" style={{ color: "var(--foreground)" }}>Archivo de ventas</label>
              <input type="file" accept=".xlsx,.xls" onChange={e => setSalesFile(e.target.files?.[0] ?? null)}
                className="block w-full text-sm rounded-md border p-2"
                style={{ borderColor: "var(--border)", backgroundColor: "var(--background)", color: "var(--foreground)" }} />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1" style={{ color: "var(--foreground)" }}>Archivo de stock</label>
              <input type="file" accept=".xlsx,.xls" onChange={e => setStockFile(e.target.files?.[0] ?? null)}
                className="block w-full text-sm rounded-md border p-2"
                style={{ borderColor: "var(--border)", backgroundColor: "var(--background)", color: "var(--foreground)" }} />
            </div>
          </div>
          <div className="mt-4 flex items-center gap-4">
            <Button onClick={handleUpload} disabled={!salesFile || !stockFile || loading} size="lg">
              <Upload className="h-4 w-4 mr-2" />{loading ? "Cargando..." : "Cargar datos"}
            </Button>
            {(!salesFile || !stockFile) && <span className="text-sm" style={{ color: "var(--muted)" }}>Seleccione ambos archivos</span>}
          </div>
        </Card>

        {uploaded && (
          <>
            <Card>
              <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-4">
                <div><span className="text-xs" style={{ color: "var(--muted)" }}>Ventas</span><div className="text-lg font-semibold" style={{ color: "var(--foreground)" }}>{uploaded.diagnostics.sales_rows.toLocaleString()}</div></div>
                <div><span className="text-xs" style={{ color: "var(--muted)" }}>Stock</span><div className="text-lg font-semibold" style={{ color: "var(--foreground)" }}>{uploaded.diagnostics.stock_rows.toLocaleString()}</div></div>
                <div><span className="text-xs" style={{ color: "var(--muted)" }}>SKU vend.</span><div className="text-lg font-semibold" style={{ color: "var(--foreground)" }}>{uploaded.cross_metrics.skus_sold.toLocaleString()}</div></div>
                <div><span className="text-xs" style={{ color: "var(--muted)" }}>SKU stock</span><div className="text-lg font-semibold" style={{ color: "var(--foreground)" }}>{uploaded.cross_metrics.skus_stock.toLocaleString()}</div></div>
                <div><span className="text-xs" style={{ color: "var(--muted)" }}>Período</span><div className="text-sm font-semibold" style={{ color: "var(--foreground)" }}>{uploaded.date_range.min} → {uploaded.date_range.max}</div></div>
                <div><span className="text-xs" style={{ color: "var(--muted)" }}>Stock col.</span><div className="text-sm font-semibold" style={{ color: "var(--foreground)" }}>{uploaded.diagnostics.stock_col_origin}</div></div>
                <div><span className="text-xs" style={{ color: "var(--muted)" }}>Cruce</span><div className="text-sm font-semibold" style={{ color: "var(--foreground)" }}>{uploaded.cross_metrics.skus_crossed.toLocaleString()}</div></div>
              </div>
            </Card>

            <div className="flex flex-wrap gap-2 border-b pb-2" style={{ borderColor: "var(--border)" }}>
              {TABS.map(t => (
                <button key={t.key} onClick={() => switchTab(t.key)}
                  className="px-4 py-2 text-sm font-medium rounded-t-md border-b-2 transition-colors cursor-pointer"
                  style={{ color: tab === t.key ? "var(--accent)" : "var(--muted)", borderBottomColor: tab === t.key ? "var(--accent)" : "transparent" }}>
                  {t.label}
                </button>
              ))}
            </div>
          </>
        )}

        {/* ── RESUME ── */}
        {tab === "resumen" && analysisId && weeklyData.length > 0 && (
          <Card>
            <CardTitle>Evolución semanal de ventas</CardTitle>
            <p className="text-xs mt-1" style={{ color: "var(--muted)" }}>Haga clic en una barra para ver detalle de productos</p>
            <div className="mt-4">
              <ResponsiveContainer width="100%" height={400}>
                <BarChart data={weeklyData} onClick={handleBarClick} margin={{ top: 20, right: 20, left: 20, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={chartGrid} />
                  <XAxis dataKey="label" tick={{ fill: chartText, fontSize: 12 }} />
                  <YAxis tick={{ fill: chartText, fontSize: 12 }} tickFormatter={(v: number) => "$" + (v / 1000000).toFixed(1) + "M"} />
                  <Tooltip contentStyle={{ backgroundColor: isDark ? "#1e293b" : "#fff", border: `1px solid ${chartGrid}`, borderRadius: "6px", color: chartText }}
                    formatter={(value: number) => [fmtMoney(value), "Venta"]} />
                  <Bar dataKey="venta" fill={chartAccent} radius={[4, 4, 0, 0]} cursor="pointer" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>
        )}

        {/* ── HALLAZGOS ── */}
        {tab === "hallazgos" && analysisId && (
          <>
            <FilterPanel>
              <FilterSelect label="Período" value={hPeriod} onChange={v => { setHPeriod(v); setHallazgos(null) }}
                options={[{ value: "Todo el período", label: "Todo el período" }, { value: "Últimas 4 semanas", label: "Últimas 4 semanas" }, { value: "Últimas 8 semanas", label: "Últimas 8 semanas" }, { value: "Últimas 12 semanas", label: "Últimas 12 semanas" }]} />
              <FilterCheckbox label="Excluir conceptos comerciales" checked={hExclude} onChange={v => { setHExclude(v); setHallazgos(null) }} />
              <Button size="sm" onClick={loadHallazgos} disabled={!analysisId}>Aplicar filtros</Button>
            </FilterPanel>
            {hallazgos && (
              <>
                <FiltrosDisplay filtros={hallazgos.filtros} />
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  <HallazgoCard icon={<Package className="h-5 w-5" />} priority="Alta" title="Stock sin ventas"
                    summary={`${hallazgos.stock_sin_ventas.count} productos, ${fmtMoney(hallazgos.stock_sin_ventas.valor_total)} inmovilizados.`}
                    onView={() => setHallazgosModal({ title: "Stock sin ventas", productos: hallazgos.stock_sin_ventas.productos, exportUrl: getHallazgosExportUrl(analysisId, "stock_sin_ventas") })}
                    onExport={() => window.open(getHallazgosExportUrl(analysisId, "stock_sin_ventas"))} />
                  <HallazgoCard icon={<ShoppingCart className="h-5 w-5" />} priority="Alta" title="Demanda sin stock"
                    summary={`${hallazgos.demanda_sin_stock.count} productos, ${fmtMoney(hallazgos.demanda_sin_stock.venta_potencial)} potencial perdido.`}
                    onView={() => setHallazgosModal({ title: "Demanda sin stock", productos: hallazgos.demanda_sin_stock.productos, exportUrl: getHallazgosExportUrl(analysisId, "demanda_sin_stock") })}
                    onExport={() => window.open(getHallazgosExportUrl(analysisId, "demanda_sin_stock"))} />
                  <HallazgoCard icon={<ShieldAlert className="h-5 w-5" />} priority="Alta" title="Quiebre crítico"
                    summary={`${hallazgos.quiebre_critico.count} productos con cobertura <7 días.`}
                    onView={() => setHallazgosModal({ title: "Quiebre crítico", productos: hallazgos.quiebre_critico.productos, exportUrl: getHallazgosExportUrl(analysisId, "quiebre_critico") })}
                    onExport={() => window.open(getHallazgosExportUrl(analysisId, "quiebre_critico"))} />
                  <HallazgoCard icon={<BarChart3 className="h-5 w-5" />} priority="Media" title="Concentración Pareto"
                    summary={`${hallazgos.pareto.sku_80} de ${hallazgos.pareto.total_sku} SKU (${fmtPct(hallazgos.pareto.pct_sku)}) generan 80% de ventas.`}
                    onView={() => setHallazgosModal({ title: "Core Pareto 80%", productos: hallazgos.pareto.productos, exportUrl: getHallazgosExportUrl(analysisId, "pareto") })}
                    onExport={() => window.open(getHallazgosExportUrl(analysisId, "pareto"))} />
                  <HallazgoCard icon={<TrendingDown className="h-5 w-5" />} priority="Media" title="Mayor caída"
                    summary={`${hallazgos.caidas.count} productos. Mayor caída: ${fmtMoney(hallazgos.caidas.mayor_caida)}.`}
                    onView={() => setHallazgosModal({ title: "Caídas", productos: hallazgos.caidas.productos, exportUrl: getHallazgosExportUrl(analysisId, "caidas") })}
                    onExport={() => window.open(getHallazgosExportUrl(analysisId, "caidas"))} />
                  <HallazgoCard icon={<TrendingUp className="h-5 w-5" />} priority="Baja" title="Mayor crecimiento"
                    summary={`${hallazgos.crecimiento.count} productos. Mayor: ${fmtMoney(hallazgos.crecimiento.mayor_crecimiento)}.`}
                    onView={() => setHallazgosModal({ title: "Crecimiento", productos: hallazgos.crecimiento.productos, exportUrl: getHallazgosExportUrl(analysisId, "crecimiento") })}
                    onExport={() => window.open(getHallazgosExportUrl(analysisId, "crecimiento"))} />
                </div>
              </>
            )}
          </>
        )}

        {/* ── PARETO ── */}
        {tab === "pareto" && analysisId && (
          <>
            <FilterPanel>
              <FilterCheckbox label="Excluir conceptos comerciales" checked={pExclude} onChange={v => { setPExclude(v); setPareto(null) }} />
              <Button size="sm" onClick={loadPareto}>Aplicar</Button>
            </FilterPanel>
            {pareto && (
              <div className="space-y-4">
                <Card>
                  <CardTitle>Curva Pareto 80/20</CardTitle>
                  <p className="text-xs mt-1" style={{ color: "var(--muted)" }}>{pareto.sku_80} de {pareto.total_sku} SKU generan 80% de la venta.</p>
                  <FiltrosDisplay filtros={pareto.filtros} />
                  <div className="mt-4">
                    <ResponsiveContainer width="100%" height={400}>
                      <ComposedChart data={pareto.chart} margin={{ top: 20, right: 30, left: 20, bottom: 60 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke={chartGrid} />
                        <XAxis dataKey="sku" tick={{ fill: chartText, fontSize: 10 }} angle={-45} textAnchor="end" />
                        <YAxis yAxisId="left" tick={{ fill: chartText, fontSize: 12 }} tickFormatter={(v: number) => "$" + (v / 1000000).toFixed(1) + "M"} />
                        <YAxis yAxisId="right" orientation="right" tick={{ fill: chartText, fontSize: 12 }} tickFormatter={(v: number) => (v * 100).toFixed(0) + "%"} domain={[0, 1]} />
                        <Tooltip contentStyle={{ backgroundColor: isDark ? "#1e293b" : "#fff", border: `1px solid ${chartGrid}`, borderRadius: "6px", color: chartText }}
                          formatter={(value: number, name: string) => [name === "Venta" ? fmtMoney(value) : (value * 100).toFixed(1) + "%", name]} />
                        <Bar yAxisId="left" dataKey="venta" fill={chartAccent} radius={[4, 4, 0, 0]} cursor="pointer" />
                        <Line yAxisId="right" type="monotone" dataKey="pct_acumulado" stroke="#f59e0b" strokeWidth={2} dot={false} />
                      </ComposedChart>
                    </ResponsiveContainer>
                  </div>
                </Card>
                <Card>
                  <div className="flex items-center justify-between mb-3">
                    <CardTitle>Ranking</CardTitle>
                    <a href={getParetoExportUrl(analysisId)} download><Button variant="secondary" size="sm"><Download className="h-3 w-3 mr-1" />Excel</Button></a>
                  </div>
                  <Table>
                    <THead><TR><TH>#</TH><TH>SKU</TH><TH>Producto</TH><TH className="text-right">Venta</TH><TH className="text-right">Unid.</TH><TH className="text-right">% Acum.</TH><TH className="text-right">Clasif.</TH><TH className="text-right">Stock</TH></TR></THead>
                    <TBody>
                      {pareto.productos.slice(0, 200).map(p => (
                        <TR key={p.ranking}>
                          <TD className="font-medium">{p.ranking}</TD>
                          <TD style={{ color: "var(--muted)", fontSize: "0.8rem" }}>{p.sku}</TD>
                          <TD>{p.producto}</TD>
                          <TD className="text-right">{fmtMoney(p.venta)}</TD>
                          <TD className="text-right">{p.unidades.toLocaleString("es-CL")}</TD>
                          <TD className="text-right">{fmtPct(p.pct_acumulado)}</TD>
                          <TD className="text-right"><span className="text-xs px-2 py-0.5 rounded" style={{ backgroundColor: p.clasificacion.includes("Core") ? "#22c55e30" : "#f59e0b30", color: p.clasificacion.includes("Core") ? "#22c55e" : "#f59e0b" }}>{p.clasificacion}</span></TD>
                          <TD className="text-right">{p.stock_disponible.toLocaleString("es-CL")}</TD>
                        </TR>
                      ))}
                    </TBody>
                  </Table>
                </Card>
              </div>
            )}
          </>
        )}

        {/* ── STOCK SIN VENTAS ── */}
        {tab === "stock" && analysisId && (
          <>
            <FilterPanel>
              <FilterSelect label="Período sin ventas" value={ssPeriod} onChange={v => { setSsPeriod(v); setStockSv(null) }}
                options={[{ value: "30", label: "30 días" }, { value: "60", label: "60 días" }, { value: "90", label: "90 días" }, { value: "180", label: "180 días" }, { value: "Todo", label: "Todo" }]} />
              <FilterCheckbox label="Excluir conceptos comerciales" checked={ssExclude} onChange={v => { setSsExclude(v); setStockSv(null) }} />
              <Button size="sm" onClick={loadStockSv}>Aplicar</Button>
            </FilterPanel>
            {stockSv && (
              <div className="space-y-4">
                <Card>
                  <CardTitle>Productos con stock sin ventas</CardTitle>
                  <FiltrosDisplay filtros={stockSv.filtros} count={stockSv.count} />
                  <p className="text-sm mt-1" style={{ color: "var(--muted)" }}>Valor inmovilizado: {fmtMoney(stockSv.valor_total)}</p>
                  {stockSv.chart.length > 0 && (
                    <div className="mt-4">
                      <ResponsiveContainer width="100%" height={350}>
                        <BarChart data={stockSv.chart} layout="vertical" margin={{ top: 10, right: 30, left: 150, bottom: 10 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke={chartGrid} />
                          <XAxis type="number" tick={{ fill: chartText, fontSize: 12 }} tickFormatter={(v: number) => fmtMoney(v)} />
                          <YAxis type="category" dataKey="producto" tick={{ fill: chartText, fontSize: 11 }} width={140} />
                          <Tooltip contentStyle={{ backgroundColor: isDark ? "#1e293b" : "#fff", border: `1px solid ${chartGrid}`, color: chartText }}
                            formatter={(value: number) => [fmtMoney(value), "Valor inmovilizado"]} />
                          <Bar dataKey="valor_stock" fill="#ef4444" radius={[0, 4, 4, 0]} />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  )}
                </Card>
                <Card>
                  <div className="flex items-center justify-between mb-3">
                    <CardTitle>Productos ({stockSv.count})</CardTitle>
                    <a href={getStockSinVentasExportUrl(analysisId)} download><Button variant="secondary" size="sm"><Download className="h-3 w-3 mr-1" />Excel</Button></a>
                  </div>
                  <ProductTable productos={stockSv.productos} />
                </Card>
              </div>
            )}
          </>
        )}

        {/* ── DEMANDA SIN STOCK ── */}
        {tab === "demanda" && analysisId && (
          <>
            <FilterPanel>
              <FilterSelect label="Período" value={dPeriod} onChange={v => { setDPeriod(v); setDemanda(null) }}
                options={[{ value: "Historial completo", label: "Historial completo" }, { value: "Últimas 12 semanas", label: "Últimas 12 semanas" }, { value: "Últimas 24 semanas", label: "Últimas 24 semanas" }]} />
              <FilterCheckbox label="Excluir conceptos comerciales" checked={dExclude} onChange={v => { setDExclude(v); setDemanda(null) }} />
              <Button size="sm" onClick={loadDemanda}>Aplicar</Button>
            </FilterPanel>
            {demanda && (
              <div className="space-y-4">
                <Card>
                  <CardTitle>Productos con demanda histórica sin stock</CardTitle>
                  <FiltrosDisplay filtros={demanda.filtros} count={demanda.count} />
                  <p className="text-sm" style={{ color: "var(--muted)" }}>Venta potencial no capturada: {fmtMoney(demanda.venta_potencial)}</p>
                  {demanda.chart.length > 0 && (
                    <div className="mt-4">
                      <ResponsiveContainer width="100%" height={350}>
                        <BarChart data={demanda.chart} layout="vertical" margin={{ top: 10, right: 30, left: 150, bottom: 10 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke={chartGrid} />
                          <XAxis type="number" tick={{ fill: chartText, fontSize: 12 }} tickFormatter={(v: number) => fmtMoney(v)} />
                          <YAxis type="category" dataKey="producto" tick={{ fill: chartText, fontSize: 11 }} width={140} />
                          <Tooltip contentStyle={{ backgroundColor: isDark ? "#1e293b" : "#fff", border: `1px solid ${chartGrid}`, color: chartText }}
                            formatter={(value: number) => [fmtMoney(value), "Venta potencial"]} />
                          <Bar dataKey="venta_potencial" fill="#f59e0b" radius={[0, 4, 4, 0]} />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  )}
                </Card>
                <Card>
                  <div className="flex items-center justify-between mb-3">
                    <CardTitle>Productos ({demanda.count})</CardTitle>
                    <a href={getDemandaExportUrl(analysisId)} download><Button variant="secondary" size="sm"><Download className="h-3 w-3 mr-1" />Excel</Button></a>
                  </div>
                  <Table>
                    <THead><TR><TH>#</TH><TH>SKU</TH><TH>Producto</TH><TH className="text-right">Vta histórica</TH><TH className="text-right">Unid.</TH><TH className="text-right">Última venta</TH><TH className="text-right">Días sin vta</TH><TH className="text-right">Vta potencial</TH></TR></THead>
                    <TBody>
                      {demanda.productos.map(p => (
                        <TR key={p.ranking}>
                          <TD className="font-medium">{p.ranking}</TD>
                          <TD style={{ color: "var(--muted)", fontSize: "0.8rem" }}>{p.sku}</TD>
                          <TD>{p.producto}</TD>
                          <TD className="text-right">{fmtMoney(p.venta_historica)}</TD>
                          <TD className="text-right">{p.unidades_historicas.toLocaleString("es-CL")}</TD>
                          <TD className="text-right">{fmtDate(p.fecha_ultima_venta)}</TD>
                          <TD className="text-right">{p.dias_sin_venta}</TD>
                          <TD className="text-right font-medium">{fmtMoney(p.venta_potencial)}</TD>
                        </TR>
                      ))}
                    </TBody>
                  </Table>
                </Card>
              </div>
            )}
          </>
        )}

        {/* ── QUIEBRES ── */}
        {tab === "quiebres" && analysisId && (
          <>
            <FilterPanel>
              <FilterSelect label="Período" value={qPeriod} onChange={v => { setQPeriod(v); setQuiebres(null) }}
                options={[{ value: "Últimas 2 semanas", label: "Últimas 2 semanas" }, { value: "Últimas 4 semanas", label: "Últimas 4 semanas" }, { value: "Últimas 8 semanas", label: "Últimas 8 semanas" }]} />
              <FilterCheckbox label="Excluir conceptos comerciales" checked={qExclude} onChange={v => { setQExclude(v); setQuiebres(null) }} />
              <Button size="sm" onClick={loadQuiebres}>Aplicar</Button>
            </FilterPanel>
            {quiebres && (
              <div className="space-y-4">
                <Card>
                  <CardTitle>Riesgo de quiebre</CardTitle>
                  <FiltrosDisplay filtros={quiebres.filtros} />
                  <p className="text-xs mt-1" style={{ color: "var(--muted)" }}>{quiebres.total_crit} productos en riesgo.</p>
                  {quiebres.chart.length > 0 && (
                    <div className="mt-4">
                      <ResponsiveContainer width="100%" height={350}>
                        <BarChart data={quiebres.chart} layout="vertical" margin={{ top: 10, right: 30, left: 150, bottom: 10 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke={chartGrid} />
                          <XAxis type="number" tick={{ fill: chartText, fontSize: 12 }} />
                          <YAxis type="category" dataKey="producto" tick={{ fill: chartText, fontSize: 11 }} width={140} />
                          <Tooltip contentStyle={{ backgroundColor: isDark ? "#1e293b" : "#fff", border: `1px solid ${chartGrid}`, color: chartText }}
                            formatter={(value: number) => [value.toFixed(1) + " días", "Cobertura"]} />
                          <Bar dataKey="dias_cobertura" fill="#ef4444" radius={[0, 4, 4, 0]} />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  )}
                </Card>
                <Card>
                  <div className="flex items-center justify-between mb-3">
                    <CardTitle>SKUs en riesgo ({quiebres.total_crit})</CardTitle>
                    <a href={getQuiebresExportUrl(analysisId)} download><Button variant="secondary" size="sm"><Download className="h-3 w-3 mr-1" />Excel</Button></a>
                  </div>
                  <Table>
                    <THead><TR><TH>#</TH><TH>SKU</TH><TH>Producto</TH><TH className="text-right">Cobertura</TH><TH className="text-right">Stock</TH><TH className="text-right">Demanda diaria</TH><TH className="text-right">Alerta</TH></TR></THead>
                    <TBody>
                      {quiebres.productos.map(p => (
                        <TR key={p.ranking}>
                          <TD className="font-medium">{p.ranking}</TD>
                          <TD style={{ color: "var(--muted)", fontSize: "0.8rem" }}>{p.sku}</TD>
                          <TD>{p.producto}</TD>
                          <TD className="text-right font-medium" style={{ color: p.dias_cobertura != null && p.dias_cobertura < 7 ? "#ef4444" : "#f59e0b" }}>
                            {p.dias_cobertura != null ? p.dias_cobertura.toFixed(1) + "d" : "-"}</TD>
                          <TD className="text-right">{p.stock_disponible.toLocaleString("es-CL")}</TD>
                          <TD className="text-right">{p.demanda_diaria.toFixed(2)}</TD>
                          <TD className="text-right"><span className="text-xs px-2 py-0.5 rounded" style={{ backgroundColor: p.alerta.includes("Crítico") ? "#ef444430" : "#f59e0b30", color: p.alerta.includes("Crítico") ? "#ef4444" : "#f59e0b" }}>{p.alerta}</span></TD>
                        </TR>
                      ))}
                    </TBody>
                  </Table>
                </Card>
              </div>
            )}
          </>
        )}

        {/* ── CAÍDAS / CRECIMIENTO ── */}
        {tab === "caidas" && analysisId && (
          <>
            <FilterPanel>
              <FilterSelect label="Comparación" value={cPeriod} onChange={v => { setCPeriod(v); setCaidas(null) }}
                options={[{ value: "Comparar últimas 4 semanas vs 4 semanas anteriores", label: "Últimas 4 semanas" },
                  { value: "Comparar últimas 8 semanas vs 8 semanas anteriores", label: "Últimas 8 semanas" },
                  { value: "Comparar últimos 3 meses vs 3 meses anteriores", label: "Últimos 3 meses" }]} />
              <FilterCheckbox label="Excluir conceptos comerciales" checked={cExclude} onChange={v => { setCExclude(v); setCaidas(null) }} />
              <Button size="sm" onClick={loadCaidas}>Aplicar</Button>
            </FilterPanel>
            {caidas && (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <Card>
                  <div className="flex items-center justify-between mb-2">
                    <CardTitle className="text-base" style={{ color: "#ef4444" }}>Caídas</CardTitle>
                    <a href={getCaidasCrecimientoExportUrl(analysisId, "caidas")} download><Button variant="ghost" size="sm"><Download className="h-3 w-3 mr-1" />Excel</Button></a>
                  </div>
                  <p className="text-xs mb-3" style={{ color: "var(--muted)" }}>{caidas.caidas.count} productos, mayor caída: {fmtMoney(caidas.caidas.mayor_caida)}</p>
                  <Table>
                    <THead><TR><TH>#</TH><TH>Producto</TH><TH className="text-right">Actual</TH><TH className="text-right">Anterior</TH><TH className="text-right">Dif.</TH><TH className="text-right">Var %</TH></TR></THead>
                    <TBody>
                      {caidas.caidas.productos.slice(0, 20).map(p => (
                        <TR key={p.ranking}>
                          <TD className="font-medium">{p.ranking}</TD>
                          <TD>{p.producto}</TD>
                          <TD className="text-right">{fmtMoney(p.venta_actual)}</TD>
                          <TD className="text-right">{fmtMoney(p.venta_anterior)}</TD>
                          <TD className="text-right font-medium" style={{ color: "#ef4444" }}>{fmtMoney(p.diferencia)}</TD>
                          <TD className="text-right" style={{ color: "#ef4444" }}>{fmtPct(p.variacion_pct)}</TD>
                        </TR>
                      ))}
                    </TBody>
                  </Table>
                </Card>
                <Card>
                  <div className="flex items-center justify-between mb-2">
                    <CardTitle className="text-base" style={{ color: "#22c55e" }}>Crecimiento</CardTitle>
                    <a href={getCaidasCrecimientoExportUrl(analysisId, "crecimiento")} download><Button variant="ghost" size="sm"><Download className="h-3 w-3 mr-1" />Excel</Button></a>
                  </div>
                  <p className="text-xs mb-3" style={{ color: "var(--muted)" }}>{caidas.crecimiento.count} productos, mayor: {fmtMoney(caidas.crecimiento.mayor_crecimiento)}</p>
                  <Table>
                    <THead><TR><TH>#</TH><TH>Producto</TH><TH className="text-right">Actual</TH><TH className="text-right">Anterior</TH><TH className="text-right">Dif.</TH><TH className="text-right">Var %</TH></TR></THead>
                    <TBody>
                      {caidas.crecimiento.productos.slice(0, 20).map(p => (
                        <TR key={p.ranking}>
                          <TD className="font-medium">{p.ranking}</TD>
                          <TD>{p.producto}</TD>
                          <TD className="text-right">{fmtMoney(p.venta_actual)}</TD>
                          <TD className="text-right">{fmtMoney(p.venta_anterior)}</TD>
                          <TD className="text-right font-medium" style={{ color: "#22c55e" }}>{fmtMoney(p.diferencia)}</TD>
                          <TD className="text-right" style={{ color: "#22c55e" }}>{fmtPct(p.variacion_pct)}</TD>
                        </TR>
                      ))}
                    </TBody>
                  </Table>
                </Card>
              </div>
            )}
          </>
        )}

        {/* ── MODALS ── */}

        <Dialog open={detail !== null} onClose={() => setDetail(null)}
          title={detail ? `Detalle de ventas — ${detail.label}` : undefined}>
          {detailLoading && <p className="text-center py-8" style={{ color: "var(--muted)" }}>Cargando...</p>}
          {detail && (
            <div className="space-y-6">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <Card><CardTitle className="text-sm font-medium" style={{ color: "var(--muted)" }}>Venta total</CardTitle><CardValue>{fmtMoney(detail.kpis.venta_total)}</CardValue></Card>
                <Card><CardTitle className="text-sm font-medium" style={{ color: "var(--muted)" }}>Unidades</CardTitle><CardValue>{detail.kpis.unidades_total.toLocaleString("es-CL")}</CardValue></Card>
                <Card><CardTitle className="text-sm font-medium" style={{ color: "var(--muted)" }}>Margen</CardTitle><CardValue>{fmtMoney(detail.kpis.margen_total)}</CardValue></Card>
                <Card><CardTitle className="text-sm font-medium" style={{ color: "var(--muted)" }}>SKUs</CardTitle><CardValue>{detail.kpis.skus_total.toLocaleString("es-CL")}</CardValue></Card>
              </div>
              <ProductTable productos={detail.productos} />
              <div className="flex justify-end">
                <a href={getWeeklyExportUrl(analysisId!, detail.year, detail.week)} download>
                  <Button variant="secondary"><Download className="h-4 w-4 mr-2" />Exportar Excel</Button>
                </a>
              </div>
            </div>
          )}
        </Dialog>

        <Dialog open={hallazgosModal !== null} onClose={() => setHallazgosModal(null)} title={hallazgosModal?.title}>
          {hallazgosModal && (
            <div className="space-y-4">
              <ProductTable productos={hallazgosModal.productos} />
              <div className="flex justify-end">
                <a href={hallazgosModal.exportUrl} download><Button variant="secondary"><Download className="h-4 w-4 mr-2" />Excel</Button></a>
              </div>
            </div>
          )}
        </Dialog>
      </main>
    </div>
  )
}

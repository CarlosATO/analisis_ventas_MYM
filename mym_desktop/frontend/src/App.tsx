import { useState, useCallback, useRef } from "react"
import { Upload, Download, TrendingDown, TrendingUp, BarChart3, Package, ShoppingCart, ShieldAlert, Filter } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardTitle, CardValue } from "@/components/ui/card"
import { Table, THead, TBody, TR, TH, TD } from "@/components/ui/table"
import { Dialog } from "@/components/ui/dialog"
import { uploadFiles, getWeekly, getWeekDetail, getWeeklyExportUrl, getHallazgos, getHallazgosExportUrl, getPareto, getParetoExportUrl, getStockSinVentas, getStockSinVentasExportUrl, getDemandaSinStock, getDemandaExportUrl, getQuiebres, getQuiebresExportUrl, getCaidasCrecimiento, getCaidasCrecimientoExportUrl, getReposicion, getReposicionFiltros, exportReposicionPlan } from "@/lib/api"
import type { UploadResponse, WeeklyPoint, WeekDetailResponse, HallazgosResponse, ParetoResponse, StockSinVentasResponse, DemandaSinStockResponse, QuiebresResponse, CaidasCrecimientoResponse, ReposicionFiltrosResponse, ReposicionResponse, ProductRow, FiltrosActivos } from "@/types"
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Line, ComposedChart } from "recharts"

const _clp = new Intl.NumberFormat("es-CL", { style: "currency", currency: "CLP", maximumFractionDigits: 0 })
const fmtMoney = (n: number) => _clp.format(n)
const fmtPct = (n: number | null) => n != null ? `${(n * 100).toFixed(1)}%` : "-"
const fmtDate = (d: string) => { try { return d ? new Date(d).toLocaleDateString("es-CL") : "-" } catch { return d } }

type Tab = "resumen" | "hallazgos" | "pareto" | "stock" | "demanda" | "quiebres" | "caidas" | "reposicion"

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
      <FilterBadge label="Proveedor" value={filtros.proveedor && filtros.proveedor !== "Todos" ? filtros.proveedor : undefined} />
      <FilterBadge label="Categoría" value={filtros.categoria && filtros.categoria !== "Todas" ? filtros.categoria : undefined} />
      <FilterBadge label="Marca" value={filtros.marca && filtros.marca !== "Todas" ? filtros.marca : undefined} />
      <FilterBadge label="Semanas" value={filtros.semanas_analisis} />
      <FilterBadge label="Cobertura objetivo" value={filtros.cobertura_objetivo ? `${filtros.cobertura_objetivo} semanas` : undefined} />
      <FilterBadge label="Stock mín" value={filtros.stock_minimo && filtros.stock_minimo > 0 ? filtros.stock_minimo : undefined} />
      <FilterBadge label="Sin stock/sin venta" value={filtros.incluir_sin_stock_sin_venta} />
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

function FilterSelect({ label, value, onChange, options, title }: {
  label: string; value: string; onChange: (v: string) => void; options: { value: string; label: string }[]; title?: string
}) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-xs font-medium" style={{ color: "var(--muted)" }} title={title}>{label}</label>
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
  const [uploaded, setUploaded] = useState<UploadResponse | null>(null)
  const [analysisId, setAnalysisId] = useState<string | null>(null)
  const [tab, setTab] = useState<Tab>("resumen")
  const [theme, setTheme] = useState<"light" | "dark">("light")
  const [weeklyData, setWeeklyData] = useState<WeeklyPoint[]>([])
  const [detail, setDetail] = useState<WeekDetailResponse | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [toastError, setToastError] = useState<string | null>(null)

  // Hallazgos
  const [hallazgos, setHallazgos] = useState<HallazgosResponse | null>(null)
  const [hallazgosModal, setHallazgosModal] = useState<{ title: string; productos: ProductRow[]; exportUrl: string } | null>(null)
  const [hPeriod, setHPeriod] = useState("Todo el período")
  const [hCategoria] = useState("")
  const [hMarca] = useState("")
  const [hExclude, setHExclude] = useState(true)

  // Pareto
  const [pareto, setPareto] = useState<ParetoResponse | null>(null)
  const [pExclude, setPExclude] = useState(true)

  // Stock SV
  const [stockSv, setStockSv] = useState<StockSinVentasResponse | null>(null)
  const [ssPeriod, setSsPeriod] = useState("Todo")
  const [ssExclude, setSsExclude] = useState(true)
  const [ssCategoria] = useState("")
  const [ssMarca] = useState("")
  const [ssStockMin] = useState(0)

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

  // Reposición Inteligente
  const [reposicion, setReposicion] = useState<ReposicionResponse | null>(null)
  const [repoFiltros, setRepoFiltros] = useState<ReposicionFiltrosResponse | null>(null)
  const [rProveedor] = useState("")
  const [rMarca] = useState("")
  const [rCategoria] = useState("")
  const [rSemanas, setRSemanas] = useState(4)
  const [rCobertura, setRCobertura] = useState(2)
  const [rStockMin, setRStockMin] = useState(0)
  const [rExclude, setRExclude] = useState(true)
  const [rIncluirSinStockSinVenta, setRIncluirSinStockSinVenta] = useState(false)
  const [rBusqueda, setRBusqueda] = useState("")
  const [repoProveedorBusqueda, setRepoProveedorBusqueda] = useState("")
  const [repoProveedorFiltro, setRepoProveedorFiltro] = useState("")
  const [repoProveedorOpen, setRepoProveedorOpen] = useState(false)
  const [repoConfirmaciones, setRepoConfirmaciones] = useState<Record<string, { cantidad: number; confirmado: boolean }>>({})
  const [repoAvisoFiltros, setRepoAvisoFiltros] = useState("")
  const [repoFilaActiva, setRepoFilaActiva] = useState("")
  const [repoColActiva, setRepoColActiva] = useState("")
  const [repoSortKey, setRepoSortKey] = useState<string | null>(null)
  const [repoSortDir, setRepoSortDir] = useState<"asc" | "desc">("asc")
  const [repoDrawerSku, setRepoDrawerSku] = useState<string | null>(null)

  const isDark = theme === "dark"
  const chartText = isDark ? "#f8fafc" : "#0f172a"
  const chartGrid = isDark ? "#334155" : "#e2e8f0"
  const chartAccent = isDark ? "#38bdf8" : "#0284c7"

  const toggleTheme = () => {
    const next = theme === "light" ? "dark" : "light"
    setTheme(next)
    document.documentElement.classList.toggle("dark", next === "dark")
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

  const loadReposicionFiltros = useCallback(async () => {
    if (!analysisId) return
    setRepoFiltros(await getReposicionFiltros(analysisId, { exclude_commercial: rExclude }))
  }, [analysisId, rExclude])

  const repoOpts = { semanas_analisis: rSemanas, cobertura_objetivo: rCobertura, proveedor: rProveedor, marca: rMarca, categoria: rCategoria, stock_minimo: rStockMin || undefined, exclude_commercial: rExclude, incluir_sin_stock_sin_venta: rIncluirSinStockSinVenta }

  const markRepoFiltersChanged = () => {
    setReposicion(null)
    setRepoProveedorBusqueda("")
    setRepoProveedorFiltro("")
    setRepoConfirmaciones({})
    setRepoAvisoFiltros("Los filtros cambiaron. Revise nuevamente el sugerido antes de confirmar.")
  }

  const loadReposicion = useCallback(async () => {
    if (!analysisId) return
    const res = await getReposicion(analysisId, repoOpts)
    setReposicion(res)
    setRepoConfirmaciones(prev => {
      const next: Record<string, { cantidad: number; confirmado: boolean }> = {}
      for (const p of res.productos) {
        next[p.sku] = prev[p.sku] ?? { cantidad: p.compra_sugerida, confirmado: false }
      }
      return next
    })
    setRepoAvisoFiltros("")
  }, [analysisId, rSemanas, rCobertura, rProveedor, rMarca, rCategoria, rStockMin, rExclude, rIncluirSinStockSinVenta])

  const setRepoCantidad = (sku: string, value: string) => {
    const cantidad = Math.max(0, Math.floor(Number(value) || 0))
    setRepoConfirmaciones(prev => ({ ...prev, [sku]: { ...(prev[sku] ?? { cantidad: 0, confirmado: false }), cantidad } }))
  }

  const toggleRepoSort = (key: string) => {
    setRepoColActiva(key)
    setRepoSortKey(prev => {
      if (prev === key) {
        setRepoSortDir(d => d === "asc" ? "desc" : "asc")
        return key
      }
      setRepoSortDir("asc")
      return key
    })
  }

  const repoSortArrow = (key: string) => {
    if (repoSortKey !== key) return ""
    return repoSortDir === "asc" ? " ▲" : " ▼"
  }

  const setRepoConfirmado = (sku: string, confirmado: boolean) => {
    setRepoConfirmaciones(prev => ({ ...prev, [sku]: { ...(prev[sku] ?? { cantidad: 0, confirmado: false }), confirmado } }))
  }

  const repoBusquedaNorm = rBusqueda.trim().toLowerCase()
  const repoProveedorNorm = repoProveedorFiltro.trim().toLowerCase()
  const repoProveedoresDisponibles = Array.from(new Set((reposicion?.productos ?? []).map(p => String(p.proveedor ?? "").trim()).filter(Boolean))).sort((a, b) => a.localeCompare(b, "es"))
  const repoProveedorQuery = repoProveedorBusqueda.trim().toLowerCase()
  const repoProveedorSugerencias = repoProveedoresDisponibles.filter(p => !repoProveedorQuery || p.toLowerCase().includes(repoProveedorQuery)).slice(0, 8)
  const repoProductosFiltrados = (reposicion?.productos ?? []).filter(p => {
    if (repoProveedorNorm && String(p.proveedor ?? "").trim().toLowerCase() !== repoProveedorNorm) return false
    if (!repoBusquedaNorm) return true
    return [p.sku, p.producto, p.proveedor, p.marca, p.categoria].some(v => String(v ?? "").toLowerCase().includes(repoBusquedaNorm))
  })
  const repoProductosOrdenados = [...repoProductosFiltrados].sort((a, b) => {
    if (!repoSortKey) return 0
    const dir = repoSortDir === "asc" ? 1 : -1
    if (repoSortKey === "confirmar") {
      const ca = repoConfirmaciones[a.sku]?.confirmado ?? false
      const cb = repoConfirmaciones[b.sku]?.confirmado ?? false
      return (ca === cb ? 0 : ca ? -1 : 1) * dir
    }
    if (repoSortKey === "proveedor" || repoSortKey === "producto" || repoSortKey === "sku" || repoSortKey === "codigo") {
      return (String(a[repoSortKey as keyof typeof a] ?? "").localeCompare(String(b[repoSortKey as keyof typeof b] ?? ""), "es")) * dir
    }
    const va = Number((a as any)[repoSortKey] ?? 0)
    const vb = Number((b as any)[repoSortKey] ?? 0)
    return (va - vb) * dir
  })
  const repoProductosVisibles = repoProductosOrdenados.slice(0, 500)
  const repoProductosConCantidad = repoProductosVisibles.map(p => ({ ...p, cantidad_confirmada: repoConfirmaciones[p.sku]?.cantidad ?? p.compra_sugerida }))
  const repoProductosConfirmados = repoProductosConCantidad.filter(p => repoConfirmaciones[p.sku]?.confirmado)
  const repoProductoDrawer = reposicion?.productos.find(p => p.sku === repoDrawerSku) ?? null
  const repoResumenConfirmado = repoProductosConfirmados.reduce((acc, p) => {
    acc.skus += 1
    acc.unidades += p.cantidad_confirmada
    acc.monto += p.cantidad_confirmada * p.costo_unitario
    if (p.estado_stock === "Crítico") acc.criticos += 1
    if (p.estado_stock === "Reponer") acc.reponer += 1
    return acc
  }, { skus: 0, unidades: 0, monto: 0, criticos: 0, reponer: 0 })

  const downloadRepoPlan = async (format: "excel" | "pdf") => {
    if (!analysisId || !reposicion) return
    if (format === "pdf") {
      if (repoProductosConfirmados.length === 0) {
        alert("Favor seleccione por lo menos 1 artículo antes de emitir.")
        return
      }
    }
    const productos = repoProductosConfirmados.length > 0 ? repoProductosConfirmados : repoProductosConCantidad
    try {
      const blob = await exportReposicionPlan(analysisId, format, { productos, filtros: reposicion.filtros, resumen: reposicion.resumen })
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = format === "excel" ? "sugerido_compras_mym.xlsx" : "sugerido_compras_mym.pdf"
      a.click()
      URL.revokeObjectURL(url)
    } catch (e: any) { setToastError(e.message) }
  }

  const repoCellClass = (col: string, extra = "") => `${extra} ${repoColActiva === col ? "bg-sky-500/15" : ""}`.trim()
  const repoBlockHeader = "repo-block-title px-2 py-1 text-[11px] uppercase tracking-wide border-r border-[var(--border)]"
  const repoTh = (col: string, extra = "") => `${repoCellClass(col, `px-2 py-2 text-xs font-semibold whitespace-nowrap border-r border-[var(--border)] cursor-pointer text-slate-900 dark:text-slate-100 ${extra}`)}`
  const repoTd = (col: string, extra = "") => repoCellClass(col, `px-2 py-1.5 text-xs whitespace-nowrap border-r border-[var(--border)] text-slate-900 dark:text-slate-100 ${extra}`)

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
      else if (t === "reposicion") { await loadReposicionFiltros(); await loadReposicion() }
    } catch (e: any) { setToastError(e.message) }
  }

  const handleBarClick = async (data: any) => {
    if (!data?.activePayload?.[0]?.payload || !analysisId) return
    const p = data.activePayload[0].payload as WeeklyPoint
    setDetailLoading(true)
    try { setDetail(await getWeekDetail(analysisId, p.year, p.week)) }
    catch (e: any) { setToastError(e.message) }
    finally { setDetailLoading(false) }
  }

  const TABS: { key: Tab; label: string }[] = [
    { key: "reposicion", label: "Reposición Inteligente" },
    { key: "resumen", label: "Evolución semanal" },
    { key: "hallazgos", label: "Hallazgos" },
    { key: "pareto", label: "Pareto" },
    { key: "stock", label: "Stock sin ventas" },
    { key: "demanda", label: "Demanda sin stock" },
    { key: "quiebres", label: "Quiebres" },
    { key: "caidas", label: "Caídas y crecimiento" },
  ]

  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [uploadPhase, setUploadPhase] = useState<"idle" | "waiting_sales" | "waiting_stock" | "uploading" | "done">("idle")
  const [uploadError, setUploadError] = useState<string | null>(null)
  const salesInputRef = useRef<HTMLInputElement>(null)
  const stockInputRef = useRef<HTMLInputElement>(null)
  const pendingSalesFile = useRef<File | null>(null)

  const handleSequentialUpload = () => {
    setUploadPhase("waiting_sales")
    salesInputRef.current?.click()
  }

  const onSalesSelected = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) { setUploadPhase("idle"); return }
    pendingSalesFile.current = file
    setUploadPhase("waiting_stock")
    setTimeout(() => stockInputRef.current?.click(), 100)
  }

  const onStockSelected = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) { setUploadPhase("idle"); return }
    const salesFileVal = pendingSalesFile.current
    if (!salesFileVal) { setUploadPhase("idle"); return }
    setUploadError(null)
    setUploadPhase("uploading")
    try {
      const res = await uploadFiles(salesFileVal, file)
      setUploaded(res)
      setAnalysisId(res.analysis_id)
      setReposicion(null)
      setRepoFiltros(null)
      setRepoConfirmaciones({})
      setRepoAvisoFiltros("")
      const weekly = await getWeekly(res.analysis_id)
      setWeeklyData(weekly.weeks.filter(w => w.venta >= 0))
      setUploadPhase("done")
      setTab("reposicion")
    } catch (err: any) { setUploadError(err.message ?? "Error al procesar los archivos. Intente nuevamente."); setUploadPhase("idle") }
  }

  return (
    <div className="h-screen flex overflow-hidden" style={{ backgroundColor: "var(--background)" }}>
      {toastError && (
        <div className="fixed top-4 right-4 z-[9999] max-w-md rounded-lg border border-red-300 bg-red-50 p-4 shadow-xl dark:bg-red-950 dark:border-red-800">
          <div className="flex items-start gap-3">
            <span className="mt-0.5 shrink-0 text-red-600 dark:text-red-400">⚠️</span>
            <p className="text-sm text-red-800 dark:text-red-200 flex-1">{toastError}</p>
            <button onClick={() => setToastError(null)} className="shrink-0 text-red-400 hover:text-red-600 font-bold cursor-pointer">&times;</button>
          </div>
        </div>
      )}
      <aside className={`${sidebarOpen ? "w-64" : "w-16"} transition-all duration-300 border-r flex flex-col shrink-0 h-full overflow-y-auto`} style={{ borderColor: "var(--border)", backgroundColor: "var(--card)" }}>
        <div className="flex items-center justify-between px-3 h-14 border-b" style={{ borderColor: "var(--border)" }}>
          {sidebarOpen && <h1 className="text-sm font-bold tracking-tight truncate" style={{ color: "var(--foreground)" }}>MYM Dashboard</h1>}
          <button onClick={() => setSidebarOpen(!sidebarOpen)} className="text-lg cursor-pointer px-1 hover:opacity-70" style={{ color: "var(--foreground)" }}>{sidebarOpen ? "◀" : "▶"}</button>
        </div>

        <div className="border-b px-3 py-4" style={{ borderColor: "var(--border)" }}>
          <input ref={salesInputRef} type="file" accept=".xlsx,.xls" className="hidden" onChange={onSalesSelected} />
          <input ref={stockInputRef} type="file" accept=".xlsx,.xls" className="hidden" onChange={onStockSelected} />
          {sidebarOpen ? (
            <>
              <Button variant={uploadPhase === "done" ? "secondary" : "primary"} size="sm" className="w-full justify-center" onClick={handleSequentialUpload} disabled={uploadPhase === "uploading"}>
                {uploadPhase === "uploading" ? (
                  <svg className="animate-spin h-4 w-4 mr-2" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                ) : (
                  <Upload className="h-4 w-4 mr-2" />
                )}
                {uploadPhase === "waiting_sales" ? "Seleccione archivo de ventas…" :
                 uploadPhase === "waiting_stock" ? "Ahora cargue archivo de stock…" :
                 uploadPhase === "uploading" ? "Procesando…" :
                 uploadPhase === "done" ? "Archivos cargados ✓" :
                 "Cargar archivos"}
              </Button>
              {uploadPhase === "uploading" && (
                <div className="mt-3 w-full">
                  <div className="h-1.5 w-full rounded-full overflow-hidden" style={{ backgroundColor: "var(--surface-soft)" }}>
                    <div className="h-full rounded-full bg-sky-500 animate-pulse" style={{ width: "60%" }} />
                  </div>
                  <p className="text-xs mt-1.5" style={{ color: "var(--muted)" }}>Procesando archivos…</p>
                </div>
              )}
              {uploadPhase === "done" && <p className="text-xs text-green-600 dark:text-green-400 mt-2 font-medium">✓ Archivos cargados</p>}
              {uploadPhase === "idle" && !uploaded && <p className="text-xs mt-2" style={{ color: "var(--muted)" }}>Cargue ventas + stock para comenzar</p>}
              {uploadPhase === "waiting_stock" && <p className="text-xs mt-2" style={{ color: "var(--accent)" }}>Seleccione el archivo de stock</p>}
              {uploadError && (
                <div className="mt-3 p-2 rounded-md text-xs flex items-start gap-2" style={{ backgroundColor: "#fee2e2", color: "#991b1b" }}>
                  <span className="shrink-0 mt-0.5">⚠️</span>
                  <span className="flex-1">{uploadError}</span>
                  <button onClick={() => setUploadError(null)} className="shrink-0 font-bold hover:opacity-70 cursor-pointer">&times;</button>
                </div>
              )}
            </>
          ) : (
            <>
              <Button variant={uploadPhase === "done" ? "secondary" : "primary"} size="sm" className="w-full justify-center" onClick={handleSequentialUpload} disabled={uploadPhase === "uploading"}
                title={uploadPhase === "waiting_sales" ? "Seleccione archivo de ventas" :
                       uploadPhase === "waiting_stock" ? "Ahora cargue archivo de stock" :
                       uploadPhase === "uploading" ? "Procesando" :
                       uploadPhase === "done" ? "Archivos cargados" : "Cargar archivos"}>
                {uploadPhase === "uploading" ? (
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                ) : (
                  <Upload className="h-4 w-4" />
                )}
              </Button>
              {uploadPhase === "uploading" && (
                <div className="mt-3 flex justify-center">
                  <svg className="animate-spin h-5 w-5" style={{ color: "var(--accent)" }} viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                </div>
              )}
              {uploadError && (
                <div className="mt-2 flex justify-center">
                  <button onClick={() => setUploadError(null)} className="text-xs" style={{ color: "#ef4444" }} title={uploadError}>⚠️</button>
                </div>
              )}
            </>
          )}
        </div>

        <nav className="flex-1 overflow-y-auto px-2 py-3 space-y-1">
          {TABS.map(t => (
            <button key={t.key} onClick={() => switchTab(t.key)}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all cursor-pointer ${tab === t.key ? "font-bold" : ""}`}
              style={{ backgroundColor: tab === t.key ? "var(--surface-strong)" : "transparent", color: tab === t.key ? "var(--accent)" : "var(--foreground)" }}>
              <span className="shrink-0">●</span>
              {sidebarOpen && <span className="truncate">{t.label}</span>}
            </button>
          ))}
        </nav>

        <div className="border-t px-3 py-3" style={{ borderColor: "var(--border)" }}>
          <button onClick={toggleTheme} className="w-full text-sm font-semibold px-3 py-2 rounded-lg border cursor-pointer transition-colors" style={{ borderColor: "var(--border)", color: "var(--foreground)", backgroundColor: "var(--surface-soft)" }}>
            {sidebarOpen ? (theme === "light" ? "🌙 Oscuro" : "☀️ Claro") : theme === "light" ? "🌙" : "☀️"}
          </button>
        </div>
      </aside>

      <main className="flex-1 overflow-y-auto px-6 py-6 space-y-6">

        {!uploaded && (
          <Card>
            <CardTitle>Bienvenido</CardTitle>
            <p className="text-sm mt-2" style={{ color: "var(--muted)" }}>Cargue los archivos de ventas y stock desde el panel lateral para comenzar el análisis.</p>
          </Card>
        )}

        {uploaded && tab !== "reposicion" && (
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
                    formatter={(value: any) => [fmtMoney(Number(value ?? 0)), "Venta"]} />
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
                          formatter={(value: any, name: any) => [name === "Venta" ? fmtMoney(Number(value ?? 0)) : (Number(value ?? 0) * 100).toFixed(1) + "%", name]} />
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
                            formatter={(value: any) => [fmtMoney(Number(value ?? 0)), "Valor inmovilizado"]} />
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
                            formatter={(value: any) => [fmtMoney(Number(value ?? 0)), "Venta potencial"]} />
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
                            formatter={(value: any) => [Number(value ?? 0).toFixed(1) + " días", "Cobertura"]} />
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

        {/* ── REPOSICIÓN INTELIGENTE ── */}
        {tab === "reposicion" && analysisId && (
          <>
            {!reposicion && (
              <Card>
                <div className="flex flex-wrap items-end gap-4">
                  <FilterSelect label="Semanas a analizar" value={String(rSemanas)} onChange={v => { setRSemanas(Number(v)); markRepoFiltersChanged() }}
                    options={[2, 4, 8, 12, 16].map(v => ({ value: String(v), label: `${v} semanas` }))} />
                  <FilterSelect label="Cobertura objetivo" title="La cobertura objetivo indica cuántas semanas se desea cubrir con inventario. Ejemplo: si el producto vende 10 unidades por semana y la cobertura objetivo es 8 semanas, el stock objetivo será 80 unidades." value={String(rCobertura)} onChange={v => { setRCobertura(Number(v)); markRepoFiltersChanged() }}
                    options={[2, 4, 6, 8, 12].map(v => ({ value: String(v), label: `${v} semanas` }))} />
                  <FilterCheckbox label="Incluir sin stock/venta" checked={rIncluirSinStockSinVenta} onChange={v => { setRIncluirSinStockSinVenta(v); markRepoFiltersChanged() }} />
                  <div className="flex flex-col gap-1">
                    <label className="text-xs font-medium" style={{ color: "var(--muted)" }} title="Cantidad mínima de stock que debe tener un producto para ser considerado en el sugerido. Si está en 0 no aplica filtro.">Stock mínimo</label>
                    <input type="number" min={0} value={rStockMin} onChange={e => { setRStockMin(Number(e.target.value) || 0); markRepoFiltersChanged() }}
                      className="text-sm rounded-md border px-2 py-1.5 w-20" style={{ borderColor: "var(--border)", backgroundColor: "var(--background)", color: "var(--foreground)" }} />
                  </div>
                  <FilterCheckbox label="Excluir comerciales" checked={rExclude} onChange={v => { setRExclude(v); setRepoFiltros(null); markRepoFiltersChanged() }} />
                  <Button size="sm" onClick={async () => { await loadReposicionFiltros(); await loadReposicion() }}>Obtener sugerido</Button>
                </div>
              </Card>
            )}
            {repoAvisoFiltros && <div className="rounded-md border px-3 py-2 text-sm" style={{ borderColor: "#2563eb", color: "#1d4ed8", backgroundColor: "#2563eb15" }}>{repoAvisoFiltros}</div>}
            {repoFiltros?.aviso_proveedor && <div className="rounded-md border px-3 py-2 text-sm" style={{ borderColor: "#f59e0b", color: "#92400e", backgroundColor: "#f59e0b20" }}>{repoFiltros.aviso_proveedor}</div>}
            {reposicion && (
              <div className="space-y-3">
                {/* Barra superior: métricas del archivo + proveedor + export */}
                <div className="flex flex-wrap items-center gap-3 rounded-xl border p-3" style={{ borderColor: "var(--border)", backgroundColor: "var(--card)" }}>
                  <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs">
                    <div><span className="font-medium" style={{ color: "var(--muted)" }}>Ventas </span><strong style={{ color: "var(--foreground)" }}>{uploaded!.diagnostics.sales_rows.toLocaleString()}</strong></div>
                    <div><span className="font-medium" style={{ color: "var(--muted)" }}>Stock </span><strong style={{ color: "var(--foreground)" }}>{uploaded!.diagnostics.stock_rows.toLocaleString()}</strong></div>
                    <div><span className="font-medium" style={{ color: "var(--muted)" }}>SKU </span><strong style={{ color: "var(--foreground)" }}>{uploaded!.cross_metrics.skus_sold.toLocaleString()}</strong></div>
                    <div><span className="font-medium" style={{ color: "var(--muted)" }}>Proveedor </span><strong style={{ color: "var(--foreground)" }}>{reposicion.resumen.proveedor_seleccionado}</strong></div>
                    <div><span className="font-medium" style={{ color: "var(--muted)" }}>Semanas </span><strong style={{ color: "var(--foreground)" }}>{reposicion.filtros?.semanas_analisis}</strong></div>
                    <div><span className="font-medium" style={{ color: "var(--muted)" }}>Cobertura obj. </span><strong style={{ color: "var(--foreground)" }}>{reposicion.filtros?.cobertura_objetivo}</strong></div>
                  </div>
                  <div className="flex flex-wrap items-center gap-2 ml-auto">
                    <Button variant="secondary" size="sm" onClick={() => downloadRepoPlan("excel")}><Download className="h-3 w-3 mr-1" />Excel</Button>
                    <Button variant="secondary" size="sm" onClick={() => downloadRepoPlan("pdf")}><Download className="h-3 w-3 mr-1" />PDF</Button>
                  </div>
                </div>

                <div className="flex flex-wrap items-end gap-3 rounded-xl border px-3 py-3" style={{ borderColor: "var(--border)", backgroundColor: "var(--card)" }}>
                  <FilterSelect label="Semanas a analizar" value={String(rSemanas)} onChange={v => { setRSemanas(Number(v)); setRepoAvisoFiltros("Parámetros cambiados. Presione Actualizar sugerido para recalcular.") }}
                    options={[2, 4, 8, 12, 16].map(v => ({ value: String(v), label: `${v} semanas` }))} />
                  <FilterSelect label="Cobertura objetivo" title="La cobertura objetivo indica cuántas semanas se desea cubrir con inventario." value={String(rCobertura)} onChange={v => { setRCobertura(Number(v)); setRepoAvisoFiltros("Parámetros cambiados. Presione Actualizar sugerido para recalcular.") }}
                    options={[2, 4, 6, 8, 12].map(v => ({ value: String(v), label: `${v} semanas` }))} />
                  <FilterCheckbox label="Incluir sin stock/venta" checked={rIncluirSinStockSinVenta} onChange={v => { setRIncluirSinStockSinVenta(v); setRepoAvisoFiltros("Parámetros cambiados. Presione Actualizar sugerido para recalcular.") }} />
                  <Button size="sm" onClick={async () => { await loadReposicion() }}>Actualizar sugerido</Button>
                </div>

                {reposicion.resumen.advertencia_costo && (
                  <div className="rounded-md border px-3 py-2 text-sm" style={{ borderColor: "#f59e0b", color: "#92400e", backgroundColor: "#f59e0b20" }}>
                    {reposicion.resumen.advertencia_costo}
                  </div>
                )}
                {reposicion.aviso_proveedor && (
                  <div className="rounded-md border px-3 py-2 text-sm" style={{ borderColor: "#f59e0b", color: "#92400e", backgroundColor: "#f59e0b20" }}>
                    {reposicion.aviso_proveedor}
                  </div>
                )}

                {/* Mini barra de resumen sugerido */}
                <div className="flex flex-wrap items-center gap-x-5 gap-y-1 rounded-xl border px-3 py-2 text-xs" style={{ borderColor: "var(--border)", backgroundColor: "var(--card)" }}>
                  <span style={{ color: "var(--muted)" }}>Sugerido:</span>
                  <span>Evaluados <strong style={{ color: "var(--foreground)" }}>{reposicion.resumen.sku_evaluados.toLocaleString("es-CL")}</strong></span>
                  <span className="text-red-600 dark:text-red-400">Críticos <strong>{reposicion.resumen.sku_criticos.toLocaleString("es-CL")}</strong></span>
                  <span className="text-amber-600 dark:text-amber-400">Reponer <strong>{reposicion.resumen.sku_reponer.toLocaleString("es-CL")}</strong></span>
                  <span style={{ color: "var(--muted)" }}>Completar <strong>{reposicion.resumen.sku_completar_objetivo.toLocaleString("es-CL")}</strong></span>
                  <span style={{ color: "var(--muted)" }}>Unidades <strong>{reposicion.resumen.unidades_sugeridas.toLocaleString("es-CL")}</strong></span>
                  <span style={{ color: "var(--muted)" }}>Monto <strong>{fmtMoney(reposicion.resumen.monto_estimado_compra)}</strong></span>
                </div>

                <Card>
                  <CardTitle className="text-sm font-bold">Detalle por SKU</CardTitle>
                  <div className="mt-3 grid grid-cols-1 gap-3 xl:grid-cols-[minmax(260px,1fr)_minmax(280px,1fr)_auto] xl:items-end">
                    <div className="w-full sm:max-w-md">
                      <label className="text-xs font-medium" style={{ color: "var(--muted)" }}>Buscar producto o código</label>
                      <input value={rBusqueda} onChange={e => setRBusqueda(e.target.value)} placeholder="ALASKA, 756625, LEONARDO, CHURU..." className="mt-1 w-full rounded-md border px-3 py-2 text-sm" style={{ borderColor: "var(--border)", backgroundColor: "var(--background)", color: "var(--foreground)" }} />
                    </div>
                    <div className="relative w-full sm:max-w-md">
                      <label className="text-xs font-medium" style={{ color: "var(--muted)" }}>Buscar proveedor</label>
                      <div className="mt-1 flex rounded-md border" style={{ borderColor: "var(--border)", backgroundColor: "var(--background)" }}>
                        <input value={repoProveedorBusqueda} onFocus={() => setRepoProveedorOpen(true)} onBlur={() => setTimeout(() => setRepoProveedorOpen(false), 120)} onChange={e => { setRepoProveedorBusqueda(e.target.value); setRepoProveedorFiltro(""); setRepoProveedorOpen(true) }} placeholder="Escriba para filtrar proveedores..." className="w-full rounded-md bg-transparent px-3 py-2 text-sm outline-none" style={{ color: "var(--foreground)" }} />
                        {(repoProveedorBusqueda || repoProveedorFiltro) && <button type="button" onMouseDown={e => e.preventDefault()} onClick={() => { setRepoProveedorBusqueda(""); setRepoProveedorFiltro(""); setRepoProveedorOpen(false) }} className="px-3 text-sm font-bold hover:opacity-70" style={{ color: "var(--muted)" }}>×</button>}
                      </div>
                      {repoProveedorOpen && repoProveedorSugerencias.length > 0 && (
                        <div className="absolute z-40 mt-1 max-h-64 w-full overflow-y-auto rounded-lg border shadow-xl" style={{ borderColor: "var(--border)", backgroundColor: "var(--card)" }}>
                          {repoProveedorSugerencias.map(p => (
                            <button key={p} type="button" onMouseDown={e => e.preventDefault()} onClick={() => { setRepoProveedorBusqueda(p); setRepoProveedorFiltro(p); setRepoProveedorOpen(false) }} className="block w-full px-3 py-2 text-left text-sm hover:bg-sky-500/10" style={{ color: "var(--foreground)" }}>
                              {p}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                    <div className="rounded-xl border px-4 py-2 text-xs shadow-sm" style={{ borderColor: "var(--border)", backgroundColor: "var(--surface-soft)", color: "var(--foreground)" }}>
                      <div className="mb-1 font-semibold" style={{ color: "var(--muted)" }}>Confirmado:</div>
                      <div className="flex flex-wrap gap-x-3 gap-y-1 whitespace-nowrap">
                        <span>SKU <strong>{repoResumenConfirmado.skus.toLocaleString("es-CL")}</strong></span>
                        <span>Unidades <strong>{repoResumenConfirmado.unidades.toLocaleString("es-CL")}</strong></span>
                        <span>Monto <strong>{fmtMoney(repoResumenConfirmado.monto)}</strong></span>
                      </div>
                    </div>
                  </div>
                  <p className="mt-2 text-sm" style={{ color: "var(--muted)" }}>Mostrando {repoProductosFiltrados.length.toLocaleString("es-CL")} de {reposicion.productos.length.toLocaleString("es-CL")} productos{repoProveedorFiltro ? ` · Proveedor: ${repoProveedorFiltro}` : ""}</p>
                  <div className="repo-table-wrap">
                    <Table className="repo-table border-0 rounded-none">
                      <THead>
                        <TR>
                          <TH className={repoBlockHeader} colSpan={3}>Producto</TH>
                          <TH className={repoBlockHeader} colSpan={1}>Stock</TH>
                          <TH className={repoBlockHeader} colSpan={reposicion.semanas_cols.length}>Unidades vendidas por semana</TH>
                          <TH className={repoBlockHeader} colSpan={7}>Cálculo sugerido</TH>
                          <TH className={repoBlockHeader} colSpan={3}>Confirmación de compra</TH>
                          <TH className={repoBlockHeader} colSpan={2}>Gestión</TH>
                        </TR>
                        <TR>
                          <TH onClick={() => toggleRepoSort("codigo")} className={repoTh("codigo", "repo-sticky-th sticky left-0 z-30 cursor-pointer select-none")}>Código<span className="sort-arrow">{repoSortArrow("codigo")}</span></TH>
                          <TH onClick={() => toggleRepoSort("producto")} className={repoTh("descripcion", "repo-sticky-th repo-sticky-edge sticky left-[90px] z-30 min-w-[240px] cursor-pointer select-none")}>Descripción<span className="sort-arrow">{repoSortArrow("producto")}</span></TH>
                          <TH onClick={() => toggleRepoSort("proveedor")} className={repoTh("proveedor", "cursor-pointer select-none")}>Proveedor<span className="sort-arrow">{repoSortArrow("proveedor")}</span></TH>
                          <TH onClick={() => toggleRepoSort("stock_actual")} className={repoTh("stock", "text-right bg-slate-500/5 cursor-pointer select-none")}>Stock actual<span className="sort-arrow">{repoSortArrow("stock_actual")}</span></TH>
                          {reposicion.semanas_cols.map(col => <TH key={col} onClick={() => toggleRepoSort(col)} className={repoTh(col, "text-right bg-cyan-500/5 cursor-pointer select-none")}>{col.replace("Venta por semana ", "")}<span className="sort-arrow">{repoSortArrow(col)}</span></TH>)}
                          <TH onClick={() => toggleRepoSort("total_unidades_vendidas")} className={repoTh("total", "text-right bg-indigo-500/5 cursor-pointer select-none")}>Total unidades<span className="sort-arrow">{repoSortArrow("total_unidades_vendidas")}</span></TH>
                          <TH onClick={() => toggleRepoSort("promedio_semanal")} className={repoTh("promedio", "text-right bg-indigo-500/5 cursor-pointer select-none")}>Prom. semanal<span className="sort-arrow">{repoSortArrow("promedio_semanal")}</span></TH>
                          <TH onClick={() => toggleRepoSort("cobertura_actual")} className={repoTh("cobertura", "text-right bg-indigo-500/5 cursor-pointer select-none")}>Cobertura<span className="sort-arrow">{repoSortArrow("cobertura_actual")}</span></TH>
                          <TH onClick={() => toggleRepoSort("tendencia_pct")} className={repoTh("variacion", "text-right bg-indigo-500/5 cursor-pointer select-none")}><span title="Compara el promedio de unidades vendidas en las semanas más recientes contra el promedio del período inmediatamente anterior. Sirve para detectar si el producto está acelerando, estable o cayendo.">Variación reciente</span><span className="sort-arrow">{repoSortArrow("tendencia_pct")}</span></TH>
                          <TH onClick={() => toggleRepoSort("estado_tendencia")} className={repoTh("estado_tendencia", "text-right bg-indigo-500/5 cursor-pointer select-none")}>Estado tendencia<span className="sort-arrow">{repoSortArrow("estado_tendencia")}</span></TH>
                          <TH onClick={() => toggleRepoSort("stock_objetivo")} className={repoTh("objetivo", "text-right bg-indigo-500/5 cursor-pointer select-none")}><span title="Cantidad ideal de stock para cubrir la cobertura objetivo seleccionada.">Stock objetivo</span><span className="sort-arrow">{repoSortArrow("stock_objetivo")}</span></TH>
                          <TH onClick={() => toggleRepoSort("compra_sugerida")} className={repoTh("sugerida", "text-right bg-indigo-500/5 cursor-pointer select-none")}><span title="Diferencia entre el stock objetivo y el stock actual. Si el stock actual ya cubre el objetivo, la compra sugerida será 0.">Compra sugerida</span><span className="sort-arrow">{repoSortArrow("compra_sugerida")}</span></TH>
                          <TH onClick={() => toggleRepoSort("cantidad")} className={repoTh("cantidad", "text-right bg-emerald-500/5 cursor-pointer select-none")}>Cantidad confirmada<span className="sort-arrow">{repoSortArrow("cantidad")}</span></TH>
                          <TH onClick={() => toggleRepoSort("monto")} className={repoTh("monto", "text-right bg-emerald-500/5 cursor-pointer select-none")}>Monto confirmado<span className="sort-arrow">{repoSortArrow("monto")}</span></TH>
                          <TH onClick={() => toggleRepoSort("confirmar")} className={repoTh("confirmar", "text-right bg-emerald-500/5 cursor-pointer select-none")}>Confirmar<span className="sort-arrow">{repoSortArrow("confirmar")}</span></TH>
                          <TH onClick={() => toggleRepoSort("estado_stock")} className={repoTh("estado_stock", "text-right cursor-pointer select-none")}>Estado stock<span className="sort-arrow">{repoSortArrow("estado_stock")}</span></TH>
                          <TH onClick={() => toggleRepoSort("accion_sugerida")} className={repoTh("accion", "cursor-pointer select-none")}>Acción sugerida<span className="sort-arrow">{repoSortArrow("accion_sugerida")}</span></TH>
                        </TR>
                      </THead>
                      <TBody>
                        {repoProductosVisibles.map(p => (
                          <TR key={p.sku} onClick={() => setRepoFilaActiva(p.sku)} onDoubleClick={() => { setRepoFilaActiva(p.sku); setRepoDrawerSku(p.sku) }} className={repoFilaActiva === p.sku ? "repo-row-active" : repoConfirmaciones[p.sku]?.confirmado ? "repo-row-confirmed" : ""}>
                            <TD className={repoTd("codigo", "repo-sticky sticky left-0 z-10 font-semibold w-[90px]")}>{p.sku}</TD>
                            <TD className={repoTd("descripcion", "repo-sticky repo-sticky-edge sticky left-[90px] z-10 min-w-[240px] max-w-[320px] truncate")}>{p.producto}</TD>
                            <TD className={repoTd("proveedor")}>{p.proveedor}</TD>
                            <TD className={repoTd("stock", "text-right")}>{p.stock_actual.toLocaleString("es-CL")}</TD>
                            {reposicion.semanas_cols.map(col => <TD key={`${p.sku}-${col}`} className={repoTd(col, "repo-week text-right")}>{(p.semanas_data[col] ?? 0).toLocaleString("es-CL")}</TD>)}
                            <TD className={repoTd("total", "repo-calc text-right")}>{p.total_unidades_vendidas.toLocaleString("es-CL")}</TD>
                            <TD className={repoTd("promedio", "repo-calc text-right")}>{p.promedio_semanal.toFixed(2)}</TD>
                            <TD className={repoTd("cobertura", "repo-calc text-right")}>{p.cobertura_actual != null ? `${p.cobertura_actual.toFixed(1)} sem.` : "Sin movimiento"}</TD>
                            <TD className={repoTd("variacion", "repo-calc text-right")}>{fmtPct(p.tendencia_pct)}</TD>
                            <TD className={repoTd("estado_tendencia", "repo-calc text-right")}><span className="text-[11px] px-1.5 py-0.5 rounded" style={{ backgroundColor: p.estado_tendencia === "Creciendo" ? "#22c55e30" : p.estado_tendencia === "Cayendo" ? "#ef444430" : p.estado_tendencia === "Estable" ? "#64748b30" : "#94a3b830", color: p.estado_tendencia === "Creciendo" ? "#166534" : p.estado_tendencia === "Cayendo" ? "#991b1b" : "#334155" }}>{p.estado_tendencia}</span></TD>
                            <TD className={repoTd("objetivo", "repo-calc text-right")}>{p.stock_objetivo.toLocaleString("es-CL")}</TD>
                            <TD className={repoTd("sugerida", "repo-calc text-right font-semibold")}>{p.compra_sugerida.toLocaleString("es-CL")}</TD>
                            <TD className={repoTd("cantidad", "repo-confirm text-right")}><input type="number" min={0} step={1} value={repoConfirmaciones[p.sku]?.cantidad ?? p.compra_sugerida} onChange={e => setRepoCantidad(p.sku, e.target.value)} className="w-20 rounded border px-1.5 py-0.5 text-right text-xs" style={{ borderColor: "var(--border)" }} /></TD>
                            <TD className={repoTd("monto", "repo-confirm text-right font-medium")}>{fmtMoney((repoConfirmaciones[p.sku]?.cantidad ?? p.compra_sugerida) * p.costo_unitario)}</TD>
                            <TD className={repoTd("confirmar", "repo-confirm text-right")}><input type="checkbox" checked={repoConfirmaciones[p.sku]?.confirmado ?? false} onChange={e => setRepoConfirmado(p.sku, e.target.checked)} /></TD>
                            <TD className={repoTd("estado_stock", "text-right")}><span className="text-[11px] px-1.5 py-0.5 rounded" style={{ backgroundColor: p.estado_stock === "Crítico" ? "#ef444430" : p.estado_stock === "Reponer" ? "#f59e0b30" : p.estado_stock === "Completar objetivo" ? "#2563eb30" : p.estado_stock === "Stock sano" ? "#22c55e30" : "#64748b30", color: p.estado_stock === "Crítico" ? "#ef4444" : p.estado_stock === "Reponer" ? "#f59e0b" : p.estado_stock === "Completar objetivo" ? "#2563eb" : p.estado_stock === "Stock sano" ? "#22c55e" : "var(--muted)" }}>{p.estado_stock}</span></TD>
                            <TD className={repoTd("accion", "min-w-[220px]")}>{p.accion_sugerida}</TD>
                          </TR>
                        ))}
                      </TBody>
                    </Table>
                  </div>
                </Card>

                {repoProductoDrawer && (
                  <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/40 backdrop-blur-sm" onClick={() => setRepoDrawerSku(null)}>
                    <aside className="h-full w-full max-w-[760px] overflow-y-auto border-l shadow-2xl" style={{ backgroundColor: "var(--card)", borderColor: "var(--border)" }} onClick={e => e.stopPropagation()}>
                      <div className="sticky top-0 z-10 border-b px-6 py-4 bg-white dark:bg-slate-900" style={{ borderColor: "var(--border)" }}>
                        <div className="flex items-start justify-between gap-4">
                          <div className="min-w-0">
                            <p className="text-xs font-bold uppercase tracking-[0.18em] text-slate-700 dark:text-slate-300">Ficha de reposición</p>
                            <h2 className="mt-1 truncate text-xl font-bold text-slate-950 dark:text-white">{repoProductoDrawer.producto}</h2>
                            <div className="mt-2 flex flex-wrap gap-2 text-xs font-medium text-slate-800 dark:text-slate-100">
                              <span className="rounded-full border bg-slate-50 px-2 py-1 dark:bg-slate-800" style={{ borderColor: "var(--border)" }}>SKU {repoProductoDrawer.sku}</span>
                              <span className="rounded-full border bg-slate-50 px-2 py-1 dark:bg-slate-800" style={{ borderColor: "var(--border)" }}>{repoProductoDrawer.proveedor}</span>
                              <span className="rounded-full border bg-slate-50 px-2 py-1 dark:bg-slate-800" style={{ borderColor: "var(--border)" }}>{repoProductoDrawer.estado_stock}</span>
                            </div>
                          </div>
                          <button className="rounded-full border bg-white px-4 py-2 text-sm font-bold text-slate-900 shadow-sm transition hover:bg-slate-100 dark:bg-slate-800 dark:text-white dark:hover:bg-slate-700" style={{ borderColor: "var(--border)" }} onClick={() => setRepoDrawerSku(null)} aria-label="Cerrar detalle">Cerrar X</button>
                        </div>
                      </div>

                      <div className="space-y-5 p-6 bg-slate-100 dark:bg-slate-950">
                        <section className="rounded-xl border bg-white p-4 shadow-sm dark:bg-[#111827]" style={{ borderColor: "var(--border)" }}>
                          <div className="mb-3 flex items-center justify-between">
                            <h3 className="text-sm font-bold uppercase tracking-wide text-slate-900 dark:text-white">Indicadores del sugerido</h3>
                            <span className="text-xs font-medium text-slate-600 dark:text-slate-300">Valores calculados en unidades</span>
                          </div>
                          <div className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
                            {[
                              ["Stock actual", repoProductoDrawer.stock_actual.toLocaleString("es-CL")],
                              ["Total unidades vendidas", repoProductoDrawer.total_unidades_vendidas.toLocaleString("es-CL")],
                              ["Promedio semanal", repoProductoDrawer.promedio_semanal.toFixed(2)],
                              ["Cobertura actual", repoProductoDrawer.cobertura_actual != null ? `${repoProductoDrawer.cobertura_actual.toFixed(1)} sem.` : "Sin movimiento"],
                              ["Variación reciente", fmtPct(repoProductoDrawer.tendencia_pct)],
                              ["Estado tendencia", repoProductoDrawer.estado_tendencia],
                              ["Stock objetivo", repoProductoDrawer.stock_objetivo.toLocaleString("es-CL")],
                              ["Compra sugerida", repoProductoDrawer.compra_sugerida.toLocaleString("es-CL")],
                            ].map(([label, value]) => (
                              <div key={label} className="flex items-center justify-between border-b border-slate-200 pb-2 dark:border-slate-700">
                                <span className="font-medium text-slate-700 dark:text-slate-200">{label}</span>
                                <strong className="text-right text-slate-950 dark:text-white">{value}</strong>
                              </div>
                            ))}
                          </div>
                        </section>

                        <section className="rounded-xl border bg-white p-4 shadow-sm dark:bg-[#111827]" style={{ borderColor: "var(--border)" }}>
                          <h3 className="text-sm font-bold uppercase tracking-wide text-slate-900 dark:text-white">Unidades vendidas por semana</h3>
                          <div className="mt-3 overflow-hidden rounded-lg border" style={{ borderColor: "var(--border)" }}>
                            <table className="w-full text-sm">
                              <tbody>
                                {reposicion.semanas_cols.map(col => (
                                  <tr key={col} className="border-b bg-slate-50 last:border-0 dark:bg-[#1f2937]" style={{ borderColor: "var(--border)" }}>
                                    <td className="px-3 py-2 font-medium text-slate-800 dark:text-slate-100">{col.replace("Venta por semana ", "")}</td>
                                    <td className="px-3 py-2 text-right font-bold text-slate-950 dark:text-white">{(repoProductoDrawer.semanas_data[col] ?? 0).toLocaleString("es-CL")}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </section>

                        <section className="rounded-xl border bg-white p-4 shadow-sm dark:bg-[#111827]" style={{ borderColor: "var(--border)" }}>
                          <h3 className="text-sm font-bold uppercase tracking-wide text-slate-900 dark:text-white">Confirmación de compra</h3>
                          <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-3">
                            <div className="flex min-h-[96px] flex-col justify-between rounded-xl border bg-slate-50 p-4 dark:bg-[#0f172a]" style={{ borderColor: "var(--border)" }}>
                              <label className="text-xs font-bold text-slate-800 dark:text-slate-100">Cantidad confirmada</label>
                              <input type="number" min={0} step={1} value={repoConfirmaciones[repoProductoDrawer.sku]?.cantidad ?? repoProductoDrawer.compra_sugerida} onChange={e => setRepoCantidad(repoProductoDrawer.sku, e.target.value)} className="mt-2 h-11 w-full rounded-lg border px-3 text-right text-lg font-bold" style={{ borderColor: "var(--border)", backgroundColor: "var(--card)", color: "var(--foreground)" }} />
                            </div>
                            <div className="flex min-h-[96px] flex-col justify-between rounded-xl border bg-slate-50 p-4 dark:bg-[#0f172a]" style={{ borderColor: "var(--border)" }}>
                              <div className="text-xs font-bold text-slate-700 dark:text-slate-200">Monto confirmado</div>
                              <div className="text-xl font-bold text-slate-950 dark:text-white">{fmtMoney((repoConfirmaciones[repoProductoDrawer.sku]?.cantidad ?? repoProductoDrawer.compra_sugerida) * repoProductoDrawer.costo_unitario)}</div>
                            </div>
                            <button className="flex min-h-[96px] items-center justify-center rounded-xl border bg-slate-900 p-4 text-sm font-bold text-white shadow-sm transition hover:bg-slate-800 dark:bg-sky-400 dark:text-slate-950 dark:hover:bg-sky-300" style={{ borderColor: "var(--border)" }} onClick={() => { setRepoConfirmado(repoProductoDrawer.sku, true); setRepoDrawerSku(null) }}>
                              Confirmar compra
                            </button>
                          </div>
                          <p className="mt-3 text-xs font-medium text-slate-700 dark:text-slate-200">{repoProductoDrawer.accion_sugerida}</p>
                        </section>
                      </div>
                    </aside>
                  </div>
                )}
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



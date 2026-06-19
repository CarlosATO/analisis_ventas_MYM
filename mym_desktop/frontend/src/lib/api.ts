import type {
  UploadResponse, WeeklyResponse, WeekDetailResponse,
  HallazgosResponse, ParetoResponse, StockSinVentasResponse,
  DemandaSinStockResponse, QuiebresResponse, CaidasCrecimientoResponse,
} from "@/types"

const API = "http://localhost:8000"

function qs(obj: Record<string, any>): string {
  const parts: string[] = []
  for (const [k, v] of Object.entries(obj)) {
    if (v !== undefined && v !== null && v !== "" && v !== false) {
      parts.push(`${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`)
    }
  }
  return parts.length ? "?" + parts.join("&") : ""
}

export async function uploadFiles(salesFile: File, stockFile: File): Promise<UploadResponse> {
  const form = new FormData()
  form.append("sales_file", salesFile)
  form.append("stock_file", stockFile)
  const res = await fetch(`${API}/api/upload`, { method: "POST", body: form })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || "Error al subir archivos")
  }
  return res.json()
}

export async function getWeekly(analysisId: string): Promise<WeeklyResponse> {
  const res = await fetch(`${API}/api/${analysisId}/weekly`)
  if (!res.ok) throw new Error("Error al obtener datos semanales")
  return res.json()
}

export async function getWeekDetail(analysisId: string, year: number, week: number): Promise<WeekDetailResponse> {
  const res = await fetch(`${API}/api/${analysisId}/weekly/${year}/${week}`)
  if (!res.ok) throw new Error("Error al obtener detalle semanal")
  return res.json()
}

export function getWeeklyExportUrl(analysisId: string, year: number, week: number): string {
  return `${API}/api/${analysisId}/export/weekly/${year}/${week}`
}

export async function getHallazgos(analysisId: string, opts?: {
  period?: string; exclude_commercial?: boolean; categoria?: string; marca?: string
}): Promise<HallazgosResponse> {
  const params = { period: opts?.period, exclude_commercial: opts?.exclude_commercial, categoria: opts?.categoria, marca: opts?.marca }
  const res = await fetch(`${API}/api/${analysisId}/hallazgos${qs(params)}`)
  if (!res.ok) throw new Error("Error al obtener hallazgos")
  return res.json()
}

export function getHallazgosExportUrl(analysisId: string, tipo: string): string {
  return `${API}/api/${analysisId}/export/hallazgos/${tipo}`
}

export async function getPareto(analysisId: string, opts?: {
  period?: string; exclude_commercial?: boolean
}): Promise<ParetoResponse> {
  const params = { period: opts?.period, exclude_commercial: opts?.exclude_commercial }
  const res = await fetch(`${API}/api/${analysisId}/pareto${qs(params)}`)
  if (!res.ok) throw new Error("Error al obtener Pareto")
  return res.json()
}

export function getParetoExportUrl(analysisId: string): string {
  return `${API}/api/${analysisId}/export/pareto`
}

export async function getStockSinVentas(analysisId: string, opts?: {
  period?: string; exclude_commercial?: boolean; categoria?: string; marca?: string; stock_min?: number
}): Promise<StockSinVentasResponse> {
  const params = { period: opts?.period, exclude_commercial: opts?.exclude_commercial, categoria: opts?.categoria, marca: opts?.marca, stock_min: opts?.stock_min }
  const res = await fetch(`${API}/api/${analysisId}/stock-sin-ventas${qs(params)}`)
  if (!res.ok) throw new Error("Error al obtener stock sin ventas")
  return res.json()
}

export function getStockSinVentasExportUrl(analysisId: string): string {
  return `${API}/api/${analysisId}/export/stock-sin-ventas`
}

export async function getDemandaSinStock(analysisId: string, opts?: {
  period?: string; exclude_commercial?: boolean; venta_min?: number; dias_min?: number
}): Promise<DemandaSinStockResponse> {
  const params = { period: opts?.period, exclude_commercial: opts?.exclude_commercial, venta_min: opts?.venta_min, dias_min: opts?.dias_min }
  const res = await fetch(`${API}/api/${analysisId}/demanda-sin-stock${qs(params)}`)
  if (!res.ok) throw new Error("Error al obtener demanda sin stock")
  return res.json()
}

export async function getDemandaHistory(analysisId: string, sku: string): Promise<{ sku: string; weeks: { label: string; venta: number; unidades: number }[] }> {
  const res = await fetch(`${API}/api/${analysisId}/demanda-sin-stock/${encodeURIComponent(sku)}/history`)
  if (!res.ok) throw new Error("Error al obtener historial")
  return res.json()
}

export function getDemandaExportUrl(analysisId: string): string {
  return `${API}/api/${analysisId}/export/demanda-sin-stock`
}

export async function getQuiebres(analysisId: string, opts?: {
  period?: string; exclude_commercial?: boolean
}): Promise<QuiebresResponse> {
  const params = { period: opts?.period, exclude_commercial: opts?.exclude_commercial }
  const res = await fetch(`${API}/api/${analysisId}/quiebres${qs(params)}`)
  if (!res.ok) throw new Error("Error al obtener quiebres")
  return res.json()
}

export function getQuiebresExportUrl(analysisId: string): string {
  return `${API}/api/${analysisId}/export/quiebres`
}

export async function getCaidasCrecimiento(analysisId: string, opts?: {
  period?: string; exclude_commercial?: boolean; umbral_pct?: number
}): Promise<CaidasCrecimientoResponse> {
  const params = { period: opts?.period, exclude_commercial: opts?.exclude_commercial, umbral_pct: opts?.umbral_pct }
  const res = await fetch(`${API}/api/${analysisId}/caidas-crecimiento${qs(params)}`)
  if (!res.ok) throw new Error("Error al obtener caídas/crecimiento")
  return res.json()
}

export function getCaidasCrecimientoExportUrl(analysisId: string, tipo: string): string {
  return `${API}/api/${analysisId}/export/caidas-crecimiento/${tipo}`
}

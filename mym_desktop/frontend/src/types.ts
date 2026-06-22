export interface UploadResponse {
  analysis_id: string
  diagnostics: {
    sales_rows: number
    stock_rows: number
    sales_header_row: number
    stock_header_row: number
    stock_col_origin: string
    stock_col_origin_type: string
  }
  cross_metrics: {
    skus_sold: number
    skus_stock: number
    skus_crossed: number
    skus_sold_no_stock: number
    skus_stock_no_sales: number
  }
  date_range: {
    min: string
    max: string
  }
  status: string
}

export interface WeeklyPoint {
  year: number
  week: number
  label: string
  venta: number
  unidades: number
  venta_formatted: string
}

export interface WeeklyResponse {
  weeks: WeeklyPoint[]
  total_weeks: number
}

export interface WeekDetailProduct {
  ranking: number
  sku: string
  producto: string
  venta: number
  unidades: number
  margen: number
  stock_disponible: number
}

export interface WeekDetailResponse {
  year: number
  week: number
  label: string
  kpis: {
    venta_total: number
    unidades_total: number
    margen_total: number
    skus_total: number
  }
  productos: WeekDetailProduct[]
}

export interface ProductRow {
  ranking: number
  sku: string
  producto: string
  venta: number
  unidades: number
  margen: number
  stock_disponible: number
}

export interface FiltrosActivos {
  periodo?: string
  excluir_conceptos_comerciales?: boolean
  proveedor?: string
  categoria?: string
  marca?: string
  stock_minimo?: number
  incluir_sin_stock_sin_venta?: boolean
  venta_minima?: number
  venta_minima_historica?: number
  dias_minimos_sin_stock?: number
  umbral_minimo_pct?: number
  dias_analisis?: number
  cobertura_objetivo?: number
}

export interface HallazgosResponse {
  filtros?: FiltrosActivos
  stock_sin_ventas: { count: number; valor_total: number; productos: ProductRow[] }
  demanda_sin_stock: { count: number; venta_potencial: number; productos: ProductRow[] }
  quiebre_critico: { count: number; productos: ProductRow[] }
  pareto: { sku_80: number; total_sku: number; pct_sku: number; productos: ProductRow[] }
  caidas: { count: number; mayor_caida: number; productos: ProductRow[] }
  crecimiento: { count: number; mayor_crecimiento: number; productos: ProductRow[] }
}

export interface StockSinVentasResponse {
  filtros?: FiltrosActivos
  count: number
  valor_total: number
  chart: { producto: string; valor_stock: number }[]
  productos: ProductRow[]
}

export interface DemandaSinStockResponse {
  filtros?: FiltrosActivos
  count: number
  venta_potencial: number
  chart: { producto: string; venta_potencial: number }[]
  productos: (ProductRow & {
    venta_historica: number
    unidades_historicas: number
    fecha_ultima_venta: string
    dias_sin_venta: number
    venta_potencial: number
  })[]
}

export interface QuiebresResponse {
  filtros?: FiltrosActivos
  chart: { producto: string; dias_cobertura: number; stock_disponible: number; demanda_diaria: number }[]
  productos: {
    ranking: number
    sku: string
    producto: string
    dias_cobertura: number | null
    stock_disponible: number
    demanda_diaria: number
    alerta: string
  }[]
  total_crit: number
}

export interface CaidasCrecimientoResponse {
  filtros?: FiltrosActivos
  caidas: {
    count: number
    mayor_caida: number
    productos: {
      ranking: number
      sku: string
      producto: string
      venta_actual: number
      venta_anterior: number
      diferencia: number
      variacion_pct: number | null
      stock_disponible: number
    }[]
  }
  crecimiento: {
    count: number
    mayor_crecimiento: number
    productos: {
      ranking: number
      sku: string
      producto: string
      venta_actual: number
      venta_anterior: number
      diferencia: number
      variacion_pct: number | null
      stock_disponible: number
    }[]
  }
}

export interface ReposicionFiltrosResponse {
  proveedores: string[]
  marcas: string[]
  categorias: string[]
  proveedor_disponible: boolean
  aviso_proveedor: string
}

export interface ReposicionProducto {
  ranking: number
  sku: string
  producto: string
  proveedor: string
  marca: string
  categoria: string
  stock_actual: number
  semanas_data: Record<string, number>
  total_unidades_vendidas: number
  promedio_semanal: number
  cobertura_actual: number | null
  stock_objetivo: number
  compra_sugerida: number
  tendencia_pct: number | null
  estado_tendencia: string
  estado_stock: string
  accion_sugerida: string
  prioridad: string
  costo_unitario: number
  monto_estimado: number
}

export interface ReposicionResponse {
  filtros?: FiltrosActivos
  proveedor_disponible: boolean
  aviso_proveedor: string
  resumen: {
    proveedor_seleccionado: string
    sku_evaluados: number
    sku_criticos: number
    sku_reponer: number
    sku_completar_objetivo: number
    unidades_sugeridas: number
    monto_estimado_compra: number
    has_missing_cost: boolean
    advertencia_costo: string
  }
  preparacion_orden_compra: {
    seleccion_productos_habilitada: boolean
    campo_clave: string
    siguiente_fase: string
  }
  semanas_cols: string[]
  productos: ReposicionProducto[]
}

export interface ParetoItem {
  sku: string
  producto: string
  venta: number
  pct_acumulado: number
}

export interface ParetoProduct {
  ranking: number
  sku: string
  producto: string
  venta: number
  unidades: number
  margen: number
  pct_acumulado: number
  clasificacion: string
  stock_disponible: number
}

export interface ParetoResponse {
  filtros?: FiltrosActivos
  chart: ParetoItem[]
  productos: ParetoProduct[]
  total_sku: number
  sku_80: number
}

export interface StockSinVentasResponse {
  count: number
  valor_total: number
  chart: { producto: string; valor_stock: number }[]
  productos: ProductRow[]
}

export interface DemandaSinStockResponse {
  count: number
  venta_potencial: number
  chart: { producto: string; venta_potencial: number }[]
  productos: (ProductRow & {
    venta_historica: number
    unidades_historicas: number
    fecha_ultima_venta: string
    dias_sin_venta: number
    venta_potencial: number
  })[]
}

export interface QuiebresResponse {
  chart: { producto: string; dias_cobertura: number; stock_disponible: number; demanda_diaria: number }[]
  productos: {
    ranking: number
    sku: string
    producto: string
    dias_cobertura: number | null
    stock_disponible: number
    demanda_diaria: number
    alerta: string
  }[]
  total_crit: number
}

export interface CaidasCrecimientoResponse {
  caidas: {
    count: number
    mayor_caida: number
    productos: {
      ranking: number
      sku: string
      producto: string
      venta_actual: number
      venta_anterior: number
      diferencia: number
      variacion_pct: number | null
      stock_disponible: number
    }[]
  }
  crecimiento: {
    count: number
    mayor_crecimiento: number
    productos: {
      ranking: number
      sku: string
      producto: string
      venta_actual: number
      venta_anterior: number
      diferencia: number
      variacion_pct: number | null
      stock_disponible: number
    }[]
  }
}

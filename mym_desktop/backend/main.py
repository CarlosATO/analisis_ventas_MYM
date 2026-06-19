"""
main.py — API FastAPI del Dashboard MYM
Reutiliza data_loader.py, analytics.py y exports.py del proyecto Streamlit.
"""

import io
import uuid
import numpy as np

from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

import pandas as pd

from data_loader import load_files
from analytics import (
    weekly_sales, weekly_sales_by_sku,
    build_sku_summary, classify_skus, pareto_analysis,
    filter_commercial, EXCLUDED_SKUS,
)
from exports import export_to_excel

app = FastAPI(title="Dashboard MYM API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

analyses: dict[str, dict] = {}


def _fmt_money(value) -> str:
    try:
        return f"${value:,.0f}".replace(",", ".")
    except Exception:
        return "$0"


def _get_data(analysis_id: str):
    data = analyses.get(analysis_id)
    if data is None:
        raise HTTPException(404, "Análisis no encontrado")
    return data


def _sku_rows(sku_df: pd.DataFrame, stock: pd.DataFrame, sort_col: str, ascending: bool, top: int = 0):
    df = sku_df.copy()
    if "Cantidad Disponible" not in df.columns:
        stock_map = stock[["SKU", "Cantidad Disponible"]].drop_duplicates("SKU")
        df = df.merge(stock_map, on="SKU", how="left")
    df["Cantidad Disponible"] = pd.to_numeric(df["Cantidad Disponible"], errors="coerce").fillna(0).astype(int)
    df = df.sort_values(sort_col, ascending=ascending).reset_index(drop=True)
    if top > 0:
        df = df.head(top)
    return df


def _product_list(df: pd.DataFrame) -> list[dict]:
    rows = []
    for i, (_, r) in enumerate(df.iterrows(), 1):
        rows.append({
            "ranking": i,
            "sku": str(r.get("SKU", "")),
            "producto": str(r.get("Producto", "")),
            "venta": round(float(r.get("venta_6m", 0)), 0),
            "unidades": int(r.get("unidades_6m", 0)),
            "margen": round(float(r.get("margen_6m", 0)), 0),
            "stock_disponible": int(r.get("Cantidad Disponible", 0)),
        })
    return rows


# ── Upload ──

@app.post("/api/upload")
async def upload_files(
    sales_file: UploadFile = File(...),
    stock_file: UploadFile = File(...),
):
    if not sales_file.filename:
        raise HTTPException(400, "No se recibió archivo de ventas")
    if not stock_file.filename:
        raise HTTPException(400, "No se recibió archivo de stock")

    try:
        sales_bytes = await sales_file.read()
        stock_bytes = await stock_file.read()
    except Exception as e:
        raise HTTPException(400, f"Error al leer archivos: {e}")

    sales_io = io.BytesIO(sales_bytes)
    stock_io = io.BytesIO(stock_bytes)

    try:
        sales_df, stock_df, diagnostics = load_files(sales_io, stock_io)
    except ValueError as e:
        raise HTTPException(400, str(e))

    min_date = sales_df["Fecha"].min()
    max_date = sales_df["Fecha"].max()

    skus_sold = set(sales_df["SKU"].unique())
    skus_stock = set(stock_df["SKU"].unique())

    cross_metrics = {
        "skus_sold": len(skus_sold),
        "skus_stock": len(skus_stock),
        "skus_crossed": len(skus_sold & skus_stock),
        "skus_sold_no_stock": len(skus_sold - skus_stock),
        "skus_stock_no_sales": len(skus_stock - skus_sold),
    }

    analysis_id = str(uuid.uuid4())[:8]

    analyses[analysis_id] = {
        "sales": sales_df,
        "stock": stock_df,
        "diagnostics": diagnostics,
        "cross_metrics": cross_metrics,
        "min_date": min_date,
        "max_date": max_date,
    }

    return {
        "analysis_id": analysis_id,
        "diagnostics": {
            "sales_rows": diagnostics["sales_rows"],
            "stock_rows": diagnostics["stock_rows"],
            "sales_header_row": diagnostics["sales_header_row"],
            "stock_header_row": diagnostics["stock_header_row"],
            "stock_col_origin": diagnostics["stock_col_origin"],
            "stock_col_origin_type": diagnostics["stock_col_origin_type"],
        },
        "cross_metrics": cross_metrics,
        "date_range": {
            "min": min_date.strftime("%d-%m-%Y"),
            "max": max_date.strftime("%d-%m-%Y"),
        },
        "status": "ok",
    }


# ── Weekly ──

@app.get("/api/{analysis_id}/weekly")
def get_weekly(analysis_id: str):
    data = _get_data(analysis_id)
    weekly = weekly_sales(data["sales"])
    result = []
    for _, row in weekly.iterrows():
        anio = int(row["Año"])
        semana = int(row["Semana"])
        venta = float(row["venta"])
        result.append({
            "year": anio,
            "week": semana,
            "label": f"S{semana} ({anio})",
            "venta": round(venta, 0),
            "unidades": float(row["unidades"]),
            "venta_formatted": _fmt_money(venta),
        })
    return {"weeks": result, "total_weeks": len(result)}


@app.get("/api/{analysis_id}/weekly/{year}/{week}")
def get_weekly_detail(analysis_id: str, year: int, week: int):
    data = _get_data(analysis_id)
    det = weekly_sales_by_sku(data["sales"], year, week)
    if det.empty:
        raise HTTPException(404, "No hay ventas en esa semana")

    stock_map = data["stock"][["SKU", "Cantidad Disponible"]].drop_duplicates("SKU")
    det = det.merge(stock_map, on="SKU", how="left")
    det["Cantidad Disponible"] = det["Cantidad Disponible"].fillna(0).astype(int)
    det = det.sort_values("Venta", ascending=False).reset_index(drop=True)

    productos = []
    for i, (_, r) in enumerate(det.iterrows(), 1):
        productos.append({
            "ranking": i,
            "sku": r["SKU"],
            "producto": r["Producto"],
            "venta": round(float(r["Venta"]), 0),
            "unidades": int(r["Unidades"]),
            "margen": round(float(r["Margen"]), 0),
            "stock_disponible": int(r["Cantidad Disponible"]),
        })

    return {
        "year": year,
        "week": week,
        "label": f"S{week} ({year})",
        "kpis": {
            "venta_total": round(float(det["Venta"].sum()), 0),
            "unidades_total": int(det["Unidades"].sum()),
            "margen_total": round(float(det["Margen"].sum()), 0),
            "skus_total": len(det),
        },
        "productos": productos,
    }


@app.get("/api/{analysis_id}/export/weekly/{year}/{week}")
def export_weekly_excel(analysis_id: str, year: int, week: int):
    data = _get_data(analysis_id)
    det = weekly_sales_by_sku(data["sales"], year, week)
    if det.empty:
        raise HTTPException(404, "No hay ventas en esa semana")

    stock_map = data["stock"][["SKU", "Cantidad Disponible"]].drop_duplicates("SKU")
    det = det.merge(stock_map, on="SKU", how="left")
    det["Cantidad Disponible"] = det["Cantidad Disponible"].fillna(0).astype(int)
    det = det.sort_values("Venta", ascending=False).reset_index(drop=True)
    det.insert(0, "Ranking", range(1, len(det) + 1))

    out = det[["Ranking", "SKU", "Producto", "Venta", "Unidades", "Margen", "Cantidad Disponible"]].rename(columns={
        "Venta": "Venta",
        "Margen": "Margen estimado",
        "Cantidad Disponible": "Stock disponible",
    })
    excel_bytes = export_to_excel(out, sheet_name=f"S{week} ({year})")
    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=detalle_semanal_{year}_{week}.xlsx"},
    )


# ── Hallazgos ──

def _build_hallazgos(
    analysis_id: str, period: str,
    exclude_commercial: bool = True,
    categoria: str = "", marca: str = "",
    stock_min: float = 0, venta_min: float = 0,
):
    data = _get_data(analysis_id)
    max_date = data["max_date"]
    min_date = data["min_date"]

    offsets = {
        "Últimas 4 semanas": pd.Timedelta(weeks=4),
        "Últimas 8 semanas": pd.Timedelta(weeks=8),
        "Últimas 12 semanas": pd.Timedelta(weeks=12),
    }
    h_start = max_date - offsets.get(period, pd.Timedelta(0))
    if period in ("Todo el período", "Historial completo"):
        h_start = min_date
    h_start = max(h_start, min_date)

    sku = classify_skus(build_sku_summary(data["sales"], data["stock"], h_start, max_date))
    if exclude_commercial:
        sku = filter_commercial(sku)
    if categoria and categoria != "Todas":
        sku = sku[sku["Categoría"] == categoria]
    if marca and marca != "Todas":
        sku = sku[sku["Marca"] == marca]
    if stock_min > 0:
        sku = sku[sku["Cantidad Disponible"] >= stock_min]
    if venta_min > 0:
        sku = sku[sku["venta_6m"] >= venta_min]

    pareto = pareto_analysis(sku)
    sku_80 = pareto[pareto["pct_acumulado"] <= 0.80]
    pct_sku = round(len(sku_80) / len(pareto), 4) if len(pareto) > 0 else 0

    def _h_list(df, sort_col, asc, top=0):
        df = df.sort_values(sort_col, ascending=asc)
        if top > 0:
            df = df.head(top)
        return _product_list(_sku_rows(df.reset_index(drop=True), data["stock"], sort_col, asc))

    muertos = sku[sku["alerta"] == "Producto muerto con stock"].copy()
    sin_stock = sku[sku["alerta"] == "Demanda histórica sin stock"].copy()
    quiebre = sku[sku["alerta"] == "Quiebre crítico"].copy()

    fall = sku[
        (sku["venta_prev_60d"] > 0) & (sku["diferencia_venta_periodo"] < 0)
    ].sort_values("diferencia_venta_periodo")
    growth = sku[
        (sku["venta_prev_60d"] > 0) & (sku["diferencia_venta_periodo"] > 0)
    ].sort_values("diferencia_venta_periodo", ascending=False)

    return {
        "filtros": {
            "periodo": period,
            "excluir_conceptos_comerciales": exclude_commercial,
            "categoria": categoria or "Todas",
            "marca": marca or "Todas",
            "stock_minimo": stock_min,
            "venta_minima": venta_min,
        },
        "stock_sin_ventas": {
            "count": len(muertos),
            "valor_total": round(float(muertos["valor_stock_disponible"].sum()), 0),
            "productos": _h_list(muertos, "valor_stock_disponible", False),
        },
        "demanda_sin_stock": {
            "count": len(sin_stock),
            "venta_potencial": round(float(
                (sin_stock["venta_promedio_mientras_vendia"] * sin_stock["dias_desde_ultima_venta"]).sum()
            ), 0) if not sin_stock.empty else 0,
            "productos": _h_list(sin_stock, "venta_historica_total", False),
        },
        "quiebre_critico": {
            "count": len(quiebre),
            "productos": _h_list(quiebre, "dias_cobertura", True),
        },
        "pareto": {
            "sku_80": len(sku_80),
            "total_sku": len(pareto),
            "pct_sku": pct_sku,
            "productos": _h_list(sku_80, "venta_6m", False),
        },
        "caidas": {
            "count": len(fall),
            "mayor_caida": round(float(fall["diferencia_venta_periodo"].min()), 0) if not fall.empty else 0,
            "productos": _h_list(fall, "diferencia_venta_periodo", True),
        },
        "crecimiento": {
            "count": len(growth),
            "mayor_crecimiento": round(float(growth["diferencia_venta_periodo"].max()), 0) if not growth.empty else 0,
            "productos": _h_list(growth, "diferencia_venta_periodo", False),
        },
    }


@app.get("/api/{analysis_id}/hallazgos")
def get_hallazgos(
    analysis_id: str,
    period: str = Query("Todo el período"),
    exclude_commercial: bool = Query(True),
    categoria: str = Query("", description="Filtrar por categoría"),
    marca: str = Query("", description="Filtrar por marca"),
):
    return _build_hallazgos(analysis_id, period, exclude_commercial, categoria, marca)


@app.get("/api/{analysis_id}/export/hallazgos/{tipo}")
def export_hallazgos_excel(analysis_id: str, tipo: str):
    data = _get_data(analysis_id)
    hallazgos = _build_hallazgos(analysis_id, "Todo el período")
    h = hallazgos.get(tipo)
    if not h:
        raise HTTPException(404, "Hallazgo no encontrado")

    prods = h.get("productos", [])
    if not prods:
        raise HTTPException(404, "No hay productos para exportar")

    df = pd.DataFrame(prods)
    excel_bytes = export_to_excel(df, sheet_name=tipo.capitalize())
    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=hallazgo_{tipo}.xlsx"},
    )


# ── Pareto ──

@app.get("/api/{analysis_id}/pareto")
def get_pareto(
    analysis_id: str,
    period: str = Query("Todo el período", description="Período de análisis"),
    exclude_commercial: bool = Query(True),
):
    data = _get_data(analysis_id)
    max_date = data["max_date"]
    min_date = data["min_date"]

    offsets = {
        "Últimas 4 semanas": pd.Timedelta(weeks=4),
        "Últimas 8 semanas": pd.Timedelta(weeks=8),
        "Últimos 3 meses": pd.Timedelta(days=90),
    }
    p_start = max_date - offsets.get(period, pd.Timedelta(0))
    if period == "Todo el período":
        p_start = min_date
    p_start = max(p_start, min_date)

    sku = build_sku_summary(data["sales"], data["stock"], p_start, max_date)
    if exclude_commercial:
        sku = filter_commercial(sku)
    pareto = pareto_analysis(sku)

    chart = []
    for _, r in pareto.head(20).iterrows():
        chart.append({
            "sku": str(r["SKU"]),
            "producto": str(r.get("Producto / Servicio", "")),
            "venta": round(float(r["venta_6m"]), 0),
            "pct_acumulado": round(float(r["pct_acumulado"]), 4),
        })

    stock_map = data["stock"][["SKU", "Cantidad Disponible"]].drop_duplicates("SKU")
    full = pareto.merge(stock_map, on="SKU", how="left")
    full["Cantidad Disponible"] = full["Cantidad Disponible"].fillna(0).astype(int)
    full = full.sort_values("venta_6m", ascending=False).reset_index(drop=True)

    productos = []
    for i, (_, r) in enumerate(full.iterrows(), 1):
        productos.append({
            "ranking": i,
            "sku": str(r["SKU"]),
            "producto": str(r.get("Producto / Servicio", "")),
            "venta": round(float(r["venta_6m"]), 0),
            "unidades": int(r.get("unidades_6m", 0)),
            "margen": round(float(r.get("margen_6m", 0)), 0),
            "pct_acumulado": round(float(r["pct_acumulado"]), 4),
            "clasificacion": str(r.get("clasificacion_pareto", "")),
            "stock_disponible": int(r["Cantidad Disponible"]),
        })

    return {
        "filtros": {
            "periodo": period,
            "excluir_conceptos_comerciales": exclude_commercial,
        },
        "chart": chart,
        "productos": productos,
        "total_sku": len(full),
        "sku_80": len(pareto[pareto["pct_acumulado"] <= 0.80]),
    }


@app.get("/api/{analysis_id}/export/pareto")
def export_pareto_excel(analysis_id: str):
    data = _get_data(analysis_id)
    pdata = get_pareto(analysis_id, "Todo el período", True)
    df = pd.DataFrame(pdata["productos"])
    excel_bytes = export_to_excel(df, sheet_name="Pareto")
    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=pareto_80_20.xlsx"},
    )


# ── Stock sin ventas ──

@app.get("/api/{analysis_id}/stock-sin-ventas")
def get_stock_sin_ventas(
    analysis_id: str,
    period: str = Query("Todo", description="Período sin ventas: 30, 60, 90, 180 días o Todo"),
    exclude_commercial: bool = Query(True),
    categoria: str = Query("", description="Filtrar por categoría"),
    marca: str = Query("", description="Filtrar por marca"),
    stock_min: float = Query(0, description="Stock mínimo"),
):
    data = _get_data(analysis_id)
    max_date = data["max_date"]
    min_date = data["min_date"]

    days_map = {"30": 30, "60": 60, "90": 90, "180": 180}
    inact_days = days_map.get(period, 0)
    d_start = max_date - pd.Timedelta(days=inact_days) if period in days_map else min_date
    d_start = max(d_start, min_date)

    sku = classify_skus(build_sku_summary(data["sales"], data["stock"], d_start, max_date))
    if exclude_commercial:
        sku = filter_commercial(sku)
    if categoria and categoria != "Todas":
        sku = sku[sku["Categoría"] == categoria]
    if marca and marca != "Todas":
        sku = sku[sku["Marca"] == marca]
    if stock_min > 0:
        sku = sku[sku["Cantidad Disponible"] >= stock_min]

    if period in days_map:
        cond = (
            (sku["Cantidad Disponible"] > 0)
            & (sku["dias_desde_ultima_venta"].isna() | (sku["dias_desde_ultima_venta"] >= inact_days))
            & ((sku["venta_6m"] == 0) | (sku["venta_6m"].isna()))
        )
        sku.loc[cond, "alerta"] = "Producto muerto con stock"

    muertos = sku[sku["alerta"] == "Producto muerto con stock"].copy()
    muertos = _sku_rows(muertos, data["stock"], "valor_stock_disponible", False)

    chart = []
    for _, r in muertos.head(15).iterrows():
        chart.append({
            "producto": str(r.get("Producto", "")),
            "valor_stock": round(float(r["valor_stock_disponible"]), 0),
        })

    return {
        "filtros": {
            "periodo": f"{period} días" if period in days_map else "Todo",
            "excluir_conceptos_comerciales": exclude_commercial,
            "categoria": categoria or "Todas",
            "marca": marca or "Todas",
            "stock_minimo": stock_min,
        },
        "count": len(muertos),
        "valor_total": round(float(muertos["valor_stock_disponible"].sum()), 0),
        "chart": chart,
        "productos": _product_list(muertos),
    }


@app.get("/api/{analysis_id}/export/stock-sin-ventas")
def export_stock_sin_ventas_excel(analysis_id: str):
    data = _get_data(analysis_id)
    sd = get_stock_sin_ventas(analysis_id, "Todo", True, "", "", 0)
    df = pd.DataFrame(sd["productos"])
    excel_bytes = export_to_excel(df, sheet_name="Stock sin ventas")
    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=stock_sin_ventas.xlsx"},
    )


# ── Demanda sin stock ──

@app.get("/api/{analysis_id}/demanda-sin-stock")
def get_demanda_sin_stock(
    analysis_id: str,
    period: str = Query("Historial completo", description="Periodo de referencia"),
    exclude_commercial: bool = Query(True),
    venta_min: float = Query(0, description="Venta mínima histórica"),
    dias_min: int = Query(0, description="Días mínimos sin stock"),
):
    data = _get_data(analysis_id)
    max_date = data["max_date"]
    min_date = data["min_date"]

    ns_start = max_date - pd.Timedelta(weeks=12) if "12" in period else \
               max_date - pd.Timedelta(weeks=24) if "24" in period else min_date
    ns_start = max(ns_start, min_date)

    sku = classify_skus(build_sku_summary(data["sales"], data["stock"], ns_start, max_date))
    if exclude_commercial:
        sku = filter_commercial(sku)
    if venta_min > 0:
        sku = sku[sku["venta_historica_total"] >= venta_min]
    if dias_min > 0:
        sku = sku[sku["dias_desde_ultima_venta"] >= dias_min]

    dem = sku[sku["alerta"] == "Demanda histórica sin stock"].copy()

    if dem.empty:
        return {"filtros": {"periodo": period, "excluir_conceptos_comerciales": exclude_commercial}, "count": 0, "venta_potencial": 0, "chart": [], "productos": []}

    dem["venta_potencial"] = dem["venta_promedio_mientras_vendia"] * dem["dias_desde_ultima_venta"]
    dem = _sku_rows(dem, data["stock"], "venta_potencial", False)

    chart = []
    for _, r in dem.head(15).iterrows():
        chart.append({
            "producto": str(r.get("Producto", "")),
            "venta_potencial": round(float(r["venta_potencial"]), 0),
        })

    productos = []
    for i, (_, r) in enumerate(dem.iterrows(), 1):
        productos.append({
            "ranking": i,
            "sku": str(r.get("SKU", "")),
            "producto": str(r.get("Producto", "")),
            "venta_historica": round(float(r.get("venta_historica_total", 0)), 0),
            "unidades_historicas": int(r.get("unidades_historicas_total", 0)),
            "fecha_ultima_venta": str(r.get("fecha_ultima_venta", pd.NaT).date()) if pd.notna(r.get("fecha_ultima_venta")) else "",
            "dias_sin_venta": int(r.get("dias_desde_ultima_venta", 0)),
            "venta_potencial": round(float(r["venta_potencial"]), 0),
        })

    return {
        "filtros": {
            "periodo": period,
            "excluir_conceptos_comerciales": exclude_commercial,
            "venta_minima_historica": venta_min,
            "dias_minimos_sin_stock": dias_min,
        },
        "count": len(dem),
        "venta_potencial": round(float(dem["venta_potencial"].sum()), 0),
        "chart": chart,
        "productos": productos,
    }


@app.get("/api/{analysis_id}/demanda-sin-stock/{sku}/history")
def get_demanda_history(analysis_id: str, sku: str):
    data = _get_data(analysis_id)
    hist = data["sales"][data["sales"]["SKU"] == sku].copy()
    if hist.empty:
        raise HTTPException(404, "Sin historial para ese SKU")

    grp = hist.groupby(["Año", "Semana"], as_index=False).agg(
        venta=("Venta Total Bruta", "sum"),
        unidades=("Cantidad", "sum"),
    ).sort_values(["Año", "Semana"])

    weeks = []
    for _, r in grp.iterrows():
        weeks.append({
            "label": f"S{int(r['Semana'])} ({int(r['Año'])})",
            "venta": round(float(r["venta"]), 0),
            "unidades": int(r["unidades"]),
        })

    return {"sku": sku, "weeks": weeks}


@app.get("/api/{analysis_id}/export/demanda-sin-stock")
def export_demanda_sin_stock_excel(analysis_id: str):
    data = _get_data(analysis_id)
    dd = get_demanda_sin_stock(analysis_id, "Historial completo", True, 0, 0)
    df = pd.DataFrame(dd["productos"])
    excel_bytes = export_to_excel(df, sheet_name="Demanda sin stock")
    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=demanda_sin_stock.xlsx"},
    )


# ── Quiebres ──

@app.get("/api/{analysis_id}/quiebres")
def get_quiebres(
    analysis_id: str,
    period: str = Query("Últimas 4 semanas", description="Periodo para demanda diaria"),
    exclude_commercial: bool = Query(True),
):
    data = _get_data(analysis_id)
    max_date = data["max_date"]
    min_date = data["min_date"]

    offsets = {
        "Últimas 2 semanas": pd.Timedelta(weeks=2),
        "Últimas 4 semanas": pd.Timedelta(weeks=4),
        "Últimas 8 semanas": pd.Timedelta(weeks=8),
    }
    qb_start = max_date - offsets.get(period, pd.Timedelta(weeks=4))
    qb_start = max(qb_start, min_date)

    sku = classify_skus(build_sku_summary(data["sales"], data["stock"], qb_start, max_date))
    if exclude_commercial:
        sku = filter_commercial(sku)

    cov = sku[
        (sku["unidades_promedio_diaria_30d"] > 0) & (sku["dias_cobertura"].notna())
    ].sort_values("dias_cobertura")

    chart = []
    for _, r in cov.head(15).iterrows():
        chart.append({
            "producto": str(r.get("Producto", "")),
            "dias_cobertura": round(float(r["dias_cobertura"]), 1),
            "stock_disponible": int(r["Cantidad Disponible"]),
            "demanda_diaria": round(float(r["unidades_promedio_diaria_30d"]), 2),
        })

    crit = sku[sku["alerta"].isin(["Quiebre crítico", "Riesgo de quiebre"])].sort_values("dias_cobertura")
    crit = _sku_rows(crit, data["stock"], "dias_cobertura", True)

    productos = []
    for i, (_, r) in enumerate(crit.iterrows(), 1):
        productos.append({
            "ranking": i,
            "sku": str(r.get("SKU", "")),
            "producto": str(r.get("Producto", "")),
            "dias_cobertura": round(float(r["dias_cobertura"]), 1) if pd.notna(r.get("dias_cobertura")) else None,
            "stock_disponible": int(r.get("Cantidad Disponible", 0)),
            "demanda_diaria": round(float(r.get("unidades_promedio_diaria_30d", 0)), 2),
            "alerta": str(r.get("alerta", "")),
        })

    return {
        "filtros": {
            "periodo": period,
            "excluir_conceptos_comerciales": exclude_commercial,
        },
        "chart": chart,
        "productos": productos,
        "total_crit": len(crit),
    }


@app.get("/api/{analysis_id}/export/quiebres")
def export_quiebres_excel(analysis_id: str):
    data = _get_data(analysis_id)
    qd = get_quiebres(analysis_id, "Últimas 4 semanas")
    df = pd.DataFrame(qd["productos"])
    excel_bytes = export_to_excel(df, sheet_name="Quiebres")
    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=quiebres_stock.xlsx"},
    )


# ── Caídas y crecimiento ──

@app.get("/api/{analysis_id}/caidas-crecimiento")
def get_caidas_crecimiento(
    analysis_id: str,
    period: str = Query("Comparar últimas 8 semanas vs 8 semanas anteriores", description="Periodo comparativo"),
    exclude_commercial: bool = Query(True),
    umbral_pct: float = Query(0, description="Umbral mínimo de variación porcentual"),
):
    data = _get_data(analysis_id)
    max_date = data["max_date"]
    min_date = data["min_date"]

    if "4 semanas" in period:
        ca_start = max_date - pd.Timedelta(days=56)
    elif "8 semanas" in period:
        ca_start = max_date - pd.Timedelta(days=112)
    else:
        ca_start = max_date - pd.Timedelta(days=180)
    ca_start = max(ca_start, min_date)

    sku = classify_skus(build_sku_summary(data["sales"], data["stock"], ca_start, max_date))
    if exclude_commercial:
        sku = filter_commercial(sku)

    fall = sku[
        (sku["venta_prev_60d"] > 0) & (sku["diferencia_venta_periodo"] < 0)
    ].sort_values("diferencia_venta_periodo")

    growth = sku[
        (sku["venta_prev_60d"] > 0) & (sku["diferencia_venta_periodo"] > 0)
    ].sort_values("diferencia_venta_periodo", ascending=False)

    def _build_list(df, sort_col, asc, top=15):
        df = df.sort_values(sort_col, ascending=asc).head(top)
        if "Cantidad Disponible" not in df.columns:
            stock_map = data["stock"][["SKU", "Cantidad Disponible"]].drop_duplicates("SKU")
            df = df.merge(stock_map, on="SKU", how="left")
        df["Cantidad Disponible"] = pd.to_numeric(df["Cantidad Disponible"], errors="coerce").fillna(0).astype(int)
        rows = []
        for i, (_, r) in enumerate(df.iterrows(), 1):
            rows.append({
                "ranking": i,
                "sku": str(r.get("SKU", "")),
                "producto": str(r.get("Producto", "")),
                "venta_actual": round(float(r.get("venta_6m", 0)), 0),
                "venta_anterior": round(float(r.get("venta_prev_60d", 0)), 0),
                "diferencia": round(float(r.get("diferencia_venta_periodo", 0)), 0),
                "variacion_pct": round(float(r.get("variacion_60d_pct", 0)), 4) if pd.notna(r.get("variacion_60d_pct")) else None,
                "stock_disponible": int(r["Cantidad Disponible"]),
            })
        return rows

    if umbral_pct > 0:
        fall = fall[fall["variacion_60d_pct"].abs() >= umbral_pct / 100]
        growth = growth[growth["variacion_60d_pct"].abs() >= umbral_pct / 100]

    return {
        "filtros": {
            "periodo": period,
            "excluir_conceptos_comerciales": exclude_commercial,
            "umbral_minimo_pct": umbral_pct,
        },
        "caidas": {
            "count": len(fall),
            "mayor_caida": round(float(fall["diferencia_venta_periodo"].min()), 0) if not fall.empty else 0,
            "productos": _build_list(fall, "diferencia_venta_periodo", True),
        },
        "crecimiento": {
            "count": len(growth),
            "mayor_crecimiento": round(float(growth["diferencia_venta_periodo"].max()), 0) if not growth.empty else 0,
            "productos": _build_list(growth, "diferencia_venta_periodo", False),
        },
    }


@app.get("/api/{analysis_id}/export/caidas-crecimiento/{tipo}")
def export_caidas_crecimiento_excel(analysis_id: str, tipo: str):
    data = _get_data(analysis_id)
    cc = get_caidas_crecimiento(analysis_id, "Comparar últimas 8 semanas vs 8 semanas anteriores", True, 0)
    section = cc.get(tipo)
    if not section:
        raise HTTPException(404, "Sección no encontrada")
    df = pd.DataFrame(section["productos"])
    excel_bytes = export_to_excel(df, sheet_name=tipo.capitalize())
    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={tipo}_ventas.xlsx"},
    )

"""
main.py — API FastAPI del Dashboard MYM
Reutiliza data_loader.py, analytics.py y exports.py del proyecto Streamlit.
"""

import io
import os
import sys
import uuid
import traceback
import numpy as np
from pathlib import Path
from datetime import datetime
from io import BytesIO
from fpdf import FPDF

BASE_DIR = Path(__file__).resolve().parent.parent.parent

from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Body
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import pandas as pd

from data_loader import load_files
from analytics import (
    weekly_sales, weekly_sales_by_sku,
    build_sku_summary, classify_skus, pareto_analysis,
    filter_commercial, EXCLUDED_SKUS, calculo_reposicion, detect_supplier_column
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
REPOSICION_REPORT_TITLE = "Sugerido de compras Distribuidora MYM"


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

def _parse_dates(data, start_date: str, end_date: str):
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
        
    return h_start, h_end


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
        traceback.print_exc()
        raise HTTPException(400, detail=f"Error al leer archivos: {e}")

    sales_io = io.BytesIO(sales_bytes)
    stock_io = io.BytesIO(stock_bytes)

    try:
        sales_df, stock_df, diagnostics = load_files(sales_io, stock_io)

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
                "min": min_date.strftime("%Y-%m-%d"),
                "max": max_date.strftime("%Y-%m-%d"),
            },
            "status": "ok",
        }
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


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
    analysis_id: str, start_date: str = "", end_date: str = "",
    exclude_commercial: bool = True,
    categoria: str = "", marca: str = "",
    stock_min: float = 0, venta_min: float = 0,
):
    data = _get_data(analysis_id)
    h_start, h_end = _parse_dates(data, start_date, end_date)

    sku = classify_skus(build_sku_summary(data["sales"], data["stock"], h_start, h_end))
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
            "start_date": start_date, "end_date": end_date,
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
    start_date: str = Query(""), end_date: str = Query(""),
    exclude_commercial: bool = Query(True),
    categoria: str = Query("", description="Filtrar por categoría"),
    marca: str = Query("", description="Filtrar por marca"),
):
    return _build_hallazgos(analysis_id, start_date, end_date, exclude_commercial, categoria, marca)


@app.get("/api/{analysis_id}/export/hallazgos/{tipo}")
def export_hallazgos_excel(analysis_id: str, tipo: str, start_date: str = Query(""), end_date: str = Query("")):
    data = _get_data(analysis_id)
    hallazgos = _build_hallazgos(analysis_id, start_date, end_date)
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
    start_date: str = Query(""), end_date: str = Query(""),
    exclude_commercial: bool = Query(True),
):
    data = _get_data(analysis_id)
    p_start, p_end = _parse_dates(data, start_date, end_date)

    sku = build_sku_summary(data["sales"], data["stock"], p_start, p_end)
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
            "start_date": start_date, "end_date": end_date,
            "excluir_conceptos_comerciales": exclude_commercial,
        },
        "chart": chart,
        "productos": productos,
        "total_sku": len(full),
        "sku_80": len(pareto[pareto["pct_acumulado"] <= 0.80]),
    }


@app.get("/api/{analysis_id}/export/pareto")
def export_pareto_excel(analysis_id: str, start_date: str = Query(""), end_date: str = Query("")):
    data = _get_data(analysis_id)
    pdata = get_pareto(analysis_id, start_date, end_date, True)
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
    start_date: str = Query(""), end_date: str = Query(""),
    exclude_commercial: bool = Query(True),
    categoria: str = Query("", description="Filtrar por categoría"),
    marca: str = Query("", description="Filtrar por marca"),
    stock_min: float = Query(0, description="Stock mínimo"),
):
    data = _get_data(analysis_id)
    d_start, h_end = _parse_dates(data, start_date, end_date)

    sku = classify_skus(build_sku_summary(data["sales"], data["stock"], d_start, h_end))
    if exclude_commercial:
        sku = filter_commercial(sku)
    if categoria and categoria != "Todas":
        sku = sku[sku["Categoría"] == categoria]
    if marca and marca != "Todas":
        sku = sku[sku["Marca"] == marca]
    if stock_min > 0:
        sku = sku[sku["Cantidad Disponible"] >= stock_min]

    inact_days = 90  # Días sin venta para considerar producto inactivo
    if True:
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
            "start_date": start_date, "end_date": end_date,
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
def export_stock_sin_ventas_excel(analysis_id: str, start_date: str = Query(""), end_date: str = Query("")):
    data = _get_data(analysis_id)
    sd = get_stock_sin_ventas(analysis_id, start_date, end_date, True, "", "", 0)
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
    start_date: str = Query(""), end_date: str = Query(""),
    exclude_commercial: bool = Query(True),
    venta_min: float = Query(0, description="Venta mínima histórica"),
    dias_min: int = Query(0, description="Días mínimos sin stock"),
):
    data = _get_data(analysis_id)
    ns_start, h_end = _parse_dates(data, start_date, end_date)

    sku = classify_skus(build_sku_summary(data["sales"], data["stock"], ns_start, h_end))
    if exclude_commercial:
        sku = filter_commercial(sku)
    if venta_min > 0:
        sku = sku[sku["venta_historica_total"] >= venta_min]
    if dias_min > 0:
        sku = sku[sku["dias_desde_ultima_venta"] >= dias_min]

    dem = sku[sku["alerta"] == "Demanda histórica sin stock"].copy()

    if dem.empty:
        return {"filtros": {"start_date": start_date, "end_date": end_date, "excluir_conceptos_comerciales": exclude_commercial}, "count": 0, "venta_potencial": 0, "chart": [], "productos": []}

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
            "start_date": start_date, "end_date": end_date,
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
def export_demanda_sin_stock_excel(analysis_id: str, start_date: str = Query(""), end_date: str = Query("")):
    data = _get_data(analysis_id)
    dd = get_demanda_sin_stock(analysis_id, start_date, end_date, True, "", "", 0)
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
    start_date: str = Query(""), end_date: str = Query(""),
    exclude_commercial: bool = Query(True),
    categoria: str = Query("", description="Filtrar por categor\u00eda"),
    marca: str = Query("", description="Filtrar por marca"),
):
    data = _get_data(analysis_id)
    qb_start, h_end = _parse_dates(data, start_date, end_date)

    sku = classify_skus(build_sku_summary(data["sales"], data["stock"], qb_start, h_end))
    if exclude_commercial:
        sku = filter_commercial(sku)
    if categoria and categoria != "Todas":
        sku = sku[sku["Categor\u00eda"] == categoria]
    if marca and marca != "Todas":
        sku = sku[sku["Marca"] == marca]

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

    crit = sku[sku["alerta"].isin(["Quiebre cr\u00edtico", "Riesgo de quiebre"])].sort_values("dias_cobertura")
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
            "start_date": start_date, "end_date": end_date,
            "excluir_conceptos_comerciales": exclude_commercial,
        },
        "chart": chart,
        "productos": productos,
        "total_crit": len(crit),
    }


@app.get("/api/{analysis_id}/export/quiebres")
def export_quiebres_excel(analysis_id: str, start_date: str = Query(""), end_date: str = Query("")):
    data = _get_data(analysis_id)
    qd = get_quiebres(analysis_id, start_date, end_date)
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
    start_date: str = Query(""), end_date: str = Query(""),
    exclude_commercial: bool = Query(True),
    umbral_pct: float = Query(0, description="Umbral mínimo de variación porcentual"),
):
    data = _get_data(analysis_id)
    h_start, h_end = _parse_dates(data, start_date, end_date)

    sku = classify_skus(build_sku_summary(data["sales"], data["stock"], h_start, h_end))
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
            "start_date": start_date, "end_date": end_date,
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
def export_caidas_crecimiento_excel(analysis_id: str, tipo: str, start_date: str = Query(""), end_date: str = Query("")):
    data = _get_data(analysis_id)
    cc = get_caidas_crecimiento(analysis_id, start_date, end_date, True, 0)
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


# ── Reposición Inteligente ──

@app.get("/api/{analysis_id}/reposicion/filtros")
def get_reposicion_filtros(analysis_id: str, exclude_commercial: bool = Query(True)):
    data = _get_data(analysis_id)
    stock = data["stock"].copy()
    sales = data["sales"].copy()
    if exclude_commercial:
        stock = filter_commercial(stock)
        sales = filter_commercial(sales)

    supplier_stock_col = detect_supplier_column(stock)
    supplier_sales_col = detect_supplier_column(sales)
    proveedor_disponible = supplier_stock_col is not None or supplier_sales_col is not None

    if supplier_stock_col is not None and supplier_stock_col != "Proveedor":
        stock = stock.rename(columns={supplier_stock_col: "Proveedor"})
    elif supplier_sales_col is not None:
        supplier_map = sales[["SKU", supplier_sales_col]].dropna(subset=[supplier_sales_col]).drop_duplicates("SKU")
        supplier_map = supplier_map.rename(columns={supplier_sales_col: "Proveedor"})
        stock = stock.merge(supplier_map, on="SKU", how="left")

    if "Proveedor" not in stock.columns:
        if "Tipo de Producto / Servicio" in sales.columns:
            supplier_map = sales[["SKU", "Tipo de Producto / Servicio"]].dropna(subset=["Tipo de Producto / Servicio"]).drop_duplicates("SKU")
            supplier_map = supplier_map.rename(columns={"Tipo de Producto / Servicio": "Proveedor"})
            stock = stock.merge(supplier_map, on="SKU", how="left")
    if "Proveedor" not in stock.columns:
        stock["Proveedor"] = "Sin Proveedor"
    if "Marca" not in stock.columns:
        stock["Marca"] = "Sin Marca"
    if "Categoría" not in stock.columns:
        stock["Categoría"] = stock["Tipo de Producto"] if "Tipo de Producto" in stock.columns else "Sin Categoría"

    def _options(col: str) -> list[str]:
        values = stock[col].fillna(f"Sin {col}").astype(str).str.strip()
        values = values[values != ""]
        return sorted(values.unique().tolist())

    return {
        "proveedores": _options("Proveedor"),
        "marcas": _options("Marca"),
        "categorias": _options("Categoría"),
        "proveedor_disponible": proveedor_disponible,
        "aviso_proveedor": "" if proveedor_disponible else "No se detectó columna de proveedor explícita. Los proveedores se están tomando desde 'Tipo de Producto / Servicio'.",
    }

@app.get("/api/{analysis_id}/reposicion")
def get_reposicion(
    analysis_id: str,
    dias_analisis: int = Query(28, description="Días a analizar (ej. 28, 56, 84, 112, 182, 365)"),
    cobertura_objetivo: int = Query(4, description="Cobertura objetivo en semanas"),
    proveedor: str = Query("", description="Filtrar por proveedor"),
    marca: str = Query("", description="Filtrar por marca"),
    categoria: str = Query("", description="Filtrar por categoría"),
    stock_minimo: float = Query(0, description="Stock mínimo"),
    exclude_commercial: bool = Query(True),
    incluir_sin_stock_sin_venta: bool = Query(False),
):
    data = _get_data(analysis_id)
    rep = calculo_reposicion(
        data["sales"], data["stock"],
        dias_analisis, cobertura_objetivo,
        proveedor, marca, categoria,
        stock_minimo, exclude_commercial, incluir_sin_stock_sin_venta
    )

    productos = []
    df = rep["productos"]
    for i, (_, r) in enumerate(df.iterrows(), 1):
        semanas_data = {col: int(r.get(col, 0)) for col in rep["semanas_cols"]}
        
        productos.append({
            "ranking": i,
            "sku": str(r.get("SKU", "")),
            "producto": str(r.get("Producto", "")),
            "proveedor": str(r.get("Proveedor", "")),
            "marca": str(r.get("Marca", "")),
            "categoria": str(r.get("Categoría", "")),
            "stock_actual": int(r.get("Cantidad Disponible", 0)),
            "semanas_data": semanas_data,
            "total_unidades_vendidas": int(r.get("total_unidades_vendidas", 0)),
            "promedio_semanal": round(float(r.get("promedio_semanal", 0)), 2),
            "cobertura_actual": float(r["cobertura_actual"]) if pd.notna(r.get("cobertura_actual")) else None,
            "stock_objetivo": int(r.get("stock_objetivo", 0)),
            "compra_sugerida": int(r.get("compra_sugerida", 0)),
            "tendencia_pct": float(r["tendencia_pct"]) if pd.notna(r.get("tendencia_pct")) else None,
            "estado_tendencia": str(r.get("estado_tendencia", "Sin comparación")),
            "estado_stock": str(r.get("estado_stock", "")),
            "accion_sugerida": str(r.get("accion_sugerida", "")),
            "prioridad": str(r.get("prioridad", "")),
            "costo_unitario": float(r.get("Costo Neto Prom. Unitario", 0)),
            "monto_estimado": float(r.get("monto_estimado_compra", 0))
        })
    
    return {
        "filtros": rep["filtros"],
        "proveedor_disponible": rep["proveedor_disponible"],
        "aviso_proveedor": rep["aviso_proveedor"],
        "resumen": rep["resumen"],
        "preparacion_orden_compra": rep["preparacion_orden_compra"],
        "semanas_cols": rep["semanas_cols"],
        "productos": productos
    }


def _reposicion_payload_df(payload: dict) -> tuple[pd.DataFrame, dict, dict]:
    productos = payload.get("productos", []) or []
    filtros = payload.get("filtros", {}) or {}
    resumen = payload.get("resumen", {}) or {}
    rows = []
    for p in productos:
        cantidad = max(0, int(p.get("cantidad_confirmada", p.get("compra_sugerida", 0)) or 0))
        costo = float(p.get("costo_unitario", 0) or 0)
        rows.append({
            "Código": str(p.get("sku", "")),
            "Descripción": str(p.get("producto", "")),
            "Proveedor": str(p.get("proveedor", "")),
            "Stock actual": int(p.get("stock_actual", 0) or 0),
            **{str(k): int(v or 0) for k, v in (p.get("semanas_data", {}) or {}).items()},
            "Promedio semanal": float(p.get("promedio_semanal", 0) or 0),
            "Cobertura actual": p.get("cobertura_actual", ""),
            "Variación reciente": p.get("tendencia_pct", ""),
            "Estado tendencia": str(p.get("estado_tendencia", "")),
            "Stock objetivo": int(p.get("stock_objetivo", 0) or 0),
            "Compra sugerida": int(p.get("compra_sugerida", 0) or 0),
            "Cantidad confirmada": cantidad,
            "Costo unitario estimado": costo,
            "Monto confirmado": cantidad * costo,
            "Estado de stock": str(p.get("estado_stock", "")),
            "Acción sugerida": str(p.get("accion_sugerida", "")),
        })
    df = pd.DataFrame(rows)
    if not df.empty:
        df["Cobertura actual"] = df["Cobertura actual"].apply(lambda x: "Sin movimiento" if x in (None, "") or pd.isna(x) else x)
        df["Variación reciente"] = df["Variación reciente"].apply(lambda x: f"{float(x) * 100:.1f}%" if x not in (None, "") and pd.notna(x) else "")
    return df, filtros, resumen


def _reposicion_excel_report(df: pd.DataFrame, filtros: dict, resumen: dict) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        sheet_name = "Sugerido de compras"
        start_row = 12
        df.to_excel(writer, index=False, sheet_name=sheet_name, startrow=start_row)
        wb = writer.book
        ws = writer.sheets[sheet_name]
        title_fmt = wb.add_format({"bold": True, "font_size": 16, "font_color": "#1E3A5F"})
        label_fmt = wb.add_format({"bold": True, "font_color": "#334155"})
        header_fmt = wb.add_format({"bold": True, "bg_color": "#1E3A5F", "font_color": "#FFFFFF", "border": 1})
        money_fmt = wb.add_format({"num_format": "$#,##0", "align": "right"})
        int_fmt = wb.add_format({"num_format": "#,##0", "align": "right"})
        num_fmt = wb.add_format({"num_format": "#,##0.0", "align": "right"})
        ws.write(0, 0, REPOSICION_REPORT_TITLE, title_fmt)
        ws.write(1, 0, "Fecha de generación", label_fmt)
        ws.write(1, 1, datetime.now().strftime("%d-%m-%Y %H:%M"))
        meta = [
            ("Proveedor seleccionado", filtros.get("proveedor", "Todos")),
            ("Período a analizar", f'{filtros.get("dias_analisis", "")} días'),
            ("Cobertura objetivo", filtros.get("cobertura_objetivo", "")),
            ("Marca", filtros.get("marca", "Todas")),
            ("Categoría", filtros.get("categoria", "Todas")),
            ("Stock mínimo", filtros.get("stock_minimo", 0)),
        ]
        for i, (label, value) in enumerate(meta, 2):
            ws.write(i, 0, label, label_fmt)
            ws.write(i, 1, value)
        resumen_items = [
            ("SKU evaluados", resumen.get("sku_evaluados", len(df))),
            ("SKU críticos", resumen.get("sku_criticos", 0)),
            ("SKU a reponer", resumen.get("sku_reponer", 0)),
            ("Unidades del reporte", int(df["Cantidad confirmada"].sum()) if "Cantidad confirmada" in df else 0),
            ("Monto del reporte", float(df["Monto confirmado"].sum()) if "Monto confirmado" in df else 0),
        ]
        for i, (label, value) in enumerate(resumen_items, 2):
            ws.write(i, 3, label, label_fmt)
            ws.write(i, 4, value, money_fmt if "Monto" in label else int_fmt)
        for col_num, col_name in enumerate(df.columns):
            ws.write(start_row, col_num, str(col_name), header_fmt)
            try:
                max_len = max(df.iloc[:, col_num].fillna("").astype(str).map(len).max(), len(str(col_name)))
            except Exception:
                max_len = len(str(col_name))
            width = min(max(max_len + 2, 12), 38)
            fmt = money_fmt if col_name in ("Costo unitario estimado", "Monto confirmado") else int_fmt if col_name in ("Stock actual", "Stock objetivo", "Compra sugerida", "Cantidad confirmada") or (" a " in str(col_name)) else num_fmt if col_name in ("Promedio semanal", "Cobertura actual") else None
            ws.set_column(col_num, col_num, width, fmt)
        ws.autofilter(start_row, 0, start_row, max(len(df.columns) - 1, 0))
        ws.freeze_panes(start_row + 1, 2)
    return output.getvalue()


def _pdf_escape(text: str) -> str:
    return str(text).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


class ReposicionPDF(FPDF):
    def header(self):
        logo_path = BASE_DIR / "Imagen" / "logo.png"
        if logo_path.exists():
            self.image(str(logo_path), x=15, y=8, w=35)
        self.set_xy(120, 10)
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(30, 58, 95)
        self.cell(75, 8, "SUGERIDO DE COMPRAS", align="R")
        self.set_xy(120, 19)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(100, 116, 139)
        self.cell(75, 4, f"Emision: {datetime.now().strftime('%d-%m-%Y %H:%M')}", align="R")
        self.ln(30)
        self.set_draw_color(30, 58, 95)
        self.set_line_width(0.6)
        self.line(15, self.get_y(), 195, self.get_y())
        self.ln(5)

    def footer(self):
        self.set_y(-18)
        self.set_draw_color(200, 200, 200)
        self.line(15, self.get_y(), 195, self.get_y())
        self.ln(2)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(148, 163, 184)
        self.cell(0, 10, f"Pagina {self.page_no()}/{{nb}}  |  Sugerido de compras Distribuidora MYM", align="C")


def _reposicion_pdf_report(df: pd.DataFrame, filtros: dict, resumen: dict) -> bytes:
    total_neto = float(df['Monto confirmado'].sum()) if 'Monto confirmado' in df else 0
    total_unidades = int(df['Cantidad confirmada'].sum()) if 'Cantidad confirmada' in df else 0

    pdf = ReposicionPDF(orientation="P", format="A4")
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=25)
    pdf.add_page()

    # ── Proveedor / info box ──────────────────────────
    box_y = pdf.get_y()
    pdf.set_draw_color(200, 200, 200)
    pdf.set_fill_color(248, 250, 252)
    pdf.rect(15, box_y, 180, 29, style="DF")
    # Fila 1: PROVEEDOR (izquierda) + COBERTURA OBJ. (derecha)
    pdf.set_xy(20, box_y + 3)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(18, 5, "PROVEEDOR:")
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(15, 23, 42)
    proveedor_txt = str(filtros.get("proveedor", "Todos"))
    pdf.cell(70, 5, proveedor_txt[:40])
    pdf.set_xy(125, box_y + 3)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(24, 5, "COBERTURA OBJ.:")
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(22, 5, str(filtros.get("cobertura_objetivo", "")) + " sem.")
    # Fila 2: MARCA (izquierda) + CATEGORIA (derecha)
    pdf.set_xy(20, box_y + 10)
    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(18, 5, "MARCA:")
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(70, 5, str(filtros.get("marca", "Todas"))[:40])
    pdf.set_xy(125, box_y + 10)
    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(24, 5, "CATEGORIA:")
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(22, 5, str(filtros.get("categoria", "Todas"))[:40])
    # Fila 3: PERIODO (izquierda)
    pdf.set_xy(20, box_y + 17)
    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(35, 5, "RANGO ANALIZADO:")
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(70, 5, f'{filtros.get("dias_analisis", "")} días')

    pdf.set_y(box_y + 33)

    # ── Table ─────────────────────────────────────────
    cols = ["#", "Codigo", "Descripcion", "Cant.", "Precio Unit.", "Monto Total"]
    col_w = [8, 22, 82, 20, 26, 28]
    fill_header = (30, 58, 95)
    fill_alt = (245, 247, 250)

    pdf.set_font("Helvetica", "B", 7)
    pdf.set_fill_color(*fill_header)
    pdf.set_text_color(255, 255, 255)
    pdf.set_draw_color(30, 58, 95)
    for c, w in zip(cols, col_w):
        pdf.cell(w, 7, c, border=1, fill=True, align="C")
    pdf.ln()

    pdf.set_draw_color(200, 200, 200)
    pdf.set_font("Helvetica", "", 8)
    for idx, (_, r) in enumerate(df.iterrows()):
        need_break = pdf.get_y() > 248
        if need_break:
            pdf.add_page()
            pdf.set_font("Helvetica", "B", 7)
            pdf.set_fill_color(*fill_header)
            pdf.set_text_color(255, 255, 255)
            pdf.set_draw_color(30, 58, 95)
            for c, w in zip(cols, col_w):
                pdf.cell(w, 7, c, border=1, fill=True, align="C")
            pdf.ln()
            pdf.set_font("Helvetica", "", 8)
            pdf.set_draw_color(200, 200, 200)

        if idx % 2 == 1:
            pdf.set_fill_color(*fill_alt)
        else:
            pdf.set_fill_color(255, 255, 255)

        cod = str(r.get("Código", ""))[:10]
        desc = str(r.get("Descripción", ""))[:42]
        cant = f"{int(r.get('Cantidad confirmada', 0) or 0):,}".replace(",", ".")
        costo = _fmt_money(float(r.get("Costo unitario estimado", 0) or 0))
        monto = _fmt_money(float(r.get("Monto confirmado", 0) or 0))

        pdf.set_text_color(15, 23, 42)
        pdf.cell(col_w[0], 6, str(idx + 1), border=1, fill=True, align="C")
        pdf.cell(col_w[1], 6, cod, border=1, fill=True)
        pdf.cell(col_w[2], 6, desc, border=1, fill=True)
        pdf.cell(col_w[3], 6, cant, border=1, fill=True, align="R")
        pdf.cell(col_w[4], 6, costo, border=1, fill=True, align="R")
        pdf.cell(col_w[5], 6, monto, border=1, fill=True, align="R")
        pdf.ln()

    # ── Totals ────────────────────────────────────────
    pdf.ln(2)
    col_total_w = col_w[0] + col_w[1] + col_w[2] + col_w[3]
    pdf.set_draw_color(30, 58, 95)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(30, 58, 95)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(col_total_w, 7, "TOTAL NETO", border=1, fill=True, align="R")
    pdf.cell(col_w[4], 7, "", border=1, fill=True, align="R")
    pdf.cell(col_w[5], 7, _fmt_money(total_neto), border=1, fill=True, align="R")
    pdf.ln(10)

    # ── Summary line ──────────────────────────────────
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(71, 85, 105)
    total_unidades_fmt = f"{total_unidades:,}".replace(",", ".")
    pdf.cell(0, 5, f"Total de productos: {len(df)}  |  Total unidades: {total_unidades_fmt}  |  Monto total: {_fmt_money(total_neto)}", align="L")

    return bytes(pdf.output())

@app.get("/api/{analysis_id}/export/reposicion")
def export_reposicion_excel(
    analysis_id: str,
    dias_analisis: int = Query(28),
    cobertura_objetivo: int = Query(4),
    proveedor: str = Query(""),
    marca: str = Query(""),
    categoria: str = Query(""),
    stock_minimo: float = Query(0),
    exclude_commercial: bool = Query(True),
    incluir_sin_stock_sin_venta: bool = Query(False),
):
    data = _get_data(analysis_id)
    rep = calculo_reposicion(
        data["sales"], data["stock"],
        dias_analisis, cobertura_objetivo,
        proveedor, marca, categoria,
        stock_minimo, exclude_commercial, incluir_sin_stock_sin_venta
    )
    df = rep["productos"].copy()
    
    cols_to_export = [
        "SKU", "Producto", "Proveedor", "Cantidad Disponible",
        *rep["semanas_cols"], "total_unidades_vendidas", "promedio_semanal",
        "cobertura_actual", "stock_objetivo", "compra_sugerida", "tendencia_pct",
        "estado_tendencia", "estado_stock", "accion_sugerida", "Costo Neto Prom. Unitario", "monto_estimado_compra"
    ]
    df_export = df[[c for c in cols_to_export if c in df.columns]].rename(columns={
        "Cantidad Disponible": "Stock actual",
        "total_unidades_vendidas": "Total unidades vendidas",
        "promedio_semanal": "Promedio semanal",
        "cobertura_actual": "Cobertura actual",
        "stock_objetivo": "Stock objetivo",
        "compra_sugerida": "Compra sugerida",
        "tendencia_pct": "Variación reciente",
        "estado_tendencia": "Estado tendencia",
        "estado_stock": "Estado de stock",
        "accion_sugerida": "Acción sugerida",
        "Costo Neto Prom. Unitario": "Costo unitario estimado",
        "monto_estimado_compra": "Monto estimado de compra"
    })
    
    # Manejo de "Sin rotación" si es null para la vista de excel
    df_export["Cobertura actual"] = df_export["Cobertura actual"].fillna("Sin rotación")
    df_export["Variación reciente"] = df_export["Variación reciente"].apply(lambda x: f"{x*100:.1f}%" if pd.notna(x) else "")
    
    excel_bytes = _reposicion_excel_report(df_export, rep["filtros"], rep["resumen"])
    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=reposicion_inteligente.xlsx"},
    )


@app.post("/api/{analysis_id}/export/reposicion/confirmados")
def export_reposicion_confirmados_excel(analysis_id: str, productos: list[dict] = Body(...)):
    _get_data(analysis_id)
    if not productos:
        raise HTTPException(400, "No hay productos confirmados para exportar")

    rows = []
    for p in productos:
        cantidad = max(0, int(p.get("cantidad_confirmada", 0) or 0))
        costo = float(p.get("costo_unitario", 0) or 0)
        rows.append({
            "Código": str(p.get("sku", "")),
            "Descripción": str(p.get("producto", "")),
            "Proveedor": str(p.get("proveedor", "")),
            "Stock actual": int(p.get("stock_actual", 0) or 0),
            "Promedio semanal": float(p.get("promedio_semanal", 0) or 0),
            "Cobertura actual": p.get("cobertura_actual", ""),
            "Stock objetivo": int(p.get("stock_objetivo", 0) or 0),
            "Compra sugerida": int(p.get("compra_sugerida", 0) or 0),
            "Cantidad confirmada": cantidad,
            "Costo unitario estimado": costo,
            "Monto confirmado": cantidad * costo,
            "Estado de stock": str(p.get("estado_stock", "")),
            "Acción sugerida": str(p.get("accion_sugerida", "")),
        })

    df = pd.DataFrame(rows)
    excel_bytes = export_to_excel(df, sheet_name="Confirmados")
    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=reposicion_confirmados.xlsx"},
    )


@app.post("/api/{analysis_id}/export/reposicion/plan/excel")
def export_reposicion_plan_excel(analysis_id: str, payload: dict = Body(...)):
    _get_data(analysis_id)
    df, filtros, resumen = _reposicion_payload_df(payload)
    if df.empty:
        raise HTTPException(400, "No hay productos para exportar")
    excel_bytes = _reposicion_excel_report(df, filtros, resumen)
    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=sugerido_compras_mym.xlsx"},
    )


@app.post("/api/{analysis_id}/export/reposicion/plan/pdf")
def export_reposicion_plan_pdf(analysis_id: str, payload: dict = Body(...)):
    _get_data(analysis_id)
    df, filtros, resumen = _reposicion_payload_df(payload)
    if df.empty:
        raise HTTPException(400, "No hay productos para exportar")
    pdf_bytes = _reposicion_pdf_report(df, filtros, resumen)
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=sugerido_compras_mym.pdf"},
    )


# ── Frontend estático (monolito) ────────────────────
frontend_dist = os.path.abspath(os.path.join(os.path.dirname(__file__), "../frontend/dist"))

if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")

    @app.get("/{catchall:path}")
    def serve_react_app(catchall: str):
        file_path = os.path.join(frontend_dist, catchall)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(frontend_dist, "index.html"))


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)

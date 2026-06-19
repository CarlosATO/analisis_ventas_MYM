"""
exports.py — Exportación a Excel reutilizada del proyecto Streamlit.
"""

import io
import pandas as pd


def export_to_excel(df: pd.DataFrame, sheet_name: str = "Datos") -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
        wb = writer.book
        ws = writer.sheets[sheet_name]

        header_fmt = wb.add_format({
            "bold": True,
            "bg_color": "#1E3A5F",
            "font_color": "#FFFFFF",
            "border": 1,
            "text_wrap": True,
            "valign": "vcenter",
        })
        for col_num, col_name in enumerate(df.columns):
            ws.write(0, col_num, str(col_name), header_fmt)
            try:
                col_series = df.iloc[:, col_num].fillna("").astype(str)
                max_data_len = col_series.map(len).max() if len(df) > 0 else 10
                header_len = len(str(col_name))
                col_width = min(max(header_len, max_data_len) + 2, 40)
                ws.set_column(col_num, col_num, col_width)
            except Exception:
                ws.set_column(col_num, col_num, 15)

        ws.autofilter(0, 0, 0, len(df.columns) - 1)
        ws.freeze_panes(1, 0)

    return output.getvalue()

# Dashboard Comercial MYM

Aplicación de análisis comercial para MYM basada en archivos exportados desde Bsale. Permite cruzar ventas históricas con stock disponible para detectar oportunidades comerciales, riesgos de quiebre y productos inmovilizados.

## Tecnologías

### Frontend

- React
- TypeScript
- Vite
- Tailwind CSS
- shadcn/ui
- Recharts

### Backend

- FastAPI
- pandas
- openpyxl
- xlsxwriter

### Arquitectura prevista

- React + FastAPI + Tauri (próxima fase)

---

## Estructura del proyecto

```
mym_desktop/
├── backend/
│   ├── main.py            # API FastAPI con endpoints de análisis
│   ├── data_loader.py     # Carga y validación de archivos Excel
│   ├── analytics.py       # Lógica de negocio y cálculos
│   ├── exports.py         # Exportación a Excel con formato
│   └── requirements.txt   # Dependencias Python
├── frontend/
│   ├── src/
│   │   ├── App.tsx        # Componente principal
│   │   ├── types.ts       # Tipos TypeScript
│   │   ├── lib/
│   │   │   ├── api.ts     # Cliente HTTP para FastAPI
│   │   │   └── utils.ts   # Utilidades (cn)
│   │   ├── components/
│   │   │   └── ui/        # Componentes UI (Button, Dialog, Table, Card)
│   │   └── index.css      # Estilos globales y tema
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
└── README.md
```

### Propósito de cada carpeta

- **backend/** — API REST que procesa archivos Excel, ejecuta la lógica analítica y expone endpoints para el frontend.
- **frontend/** — Aplicación React con interfaz de usuario moderna, gráficos interactivos y modales.

---

## Requisitos

### Backend

- Python 3.12 o superior

### Frontend

- Node.js LTS (18.x o 20.x)

---

## Instalación Backend

```bash
cd mym_desktop/backend
python -m venv .venv
```

Activar el entorno virtual:

**macOS / Linux:**
```bash
source .venv/bin/activate
```

**Windows:**
```bat
.venv\Scripts\activate
```

Instalar dependencias:

```bash
pip install -r requirements.txt
```

---

## Ejecutar Backend

```bash
cd mym_desktop/backend
source .venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Verificar que la API responde:

```
http://localhost:8000/docs
```

---

## Instalación Frontend

```bash
cd mym_desktop/frontend
npm install
```

---

## Ejecutar Frontend

```bash
cd mym_desktop/frontend
npm run dev
```

Abrir en el navegador:

```
http://localhost:5173
```

---

## Flujo de uso

1. Cargar archivo de ventas (`.xlsx` o `.xls`).
2. Cargar archivo de stock (`.xlsx` o `.xls`).
3. Presionar **Cargar datos**.
4. Revisar el estado del análisis (filas, SKU, período).
5. Consultar la evolución semanal en el gráfico interactivo.
6. Hacer clic en una barra para abrir el detalle semanal.
7. Exportar el detalle a Excel desde el modal.

---

## Funcionalidades actuales (MVP)

- Carga de archivos de ventas y stock.
- Validación automática de columnas requeridas.
- Detección dinámica de encabezados (filas variables según exportación de Bsale).
- Normalización de SKU y tipos de datos.
- Estado del análisis con métricas clave.
- Gráfico de evolución semanal con barras cliqueables.
- Modal de detalle semanal con KPIs y tabla de productos.
- Exportación del detalle semanal a Excel con formato profesional.
- Tema claro / oscuro.

---

## Próximas fases

| Fase | Funcionalidad |
|------|---------------|
| Fase 3 | Hallazgos ejecutivos interactivos |
| Fase 4 | Análisis Pareto 80/20 interactivo |
| Fase 5 | Riesgo de quiebre, stock sin ventas, demanda histórica sin stock |
| Fase 6 | Motor de recomendaciones prescriptivas basado en reglas de negocio |
| Fase 7 | Empaquetado como aplicación de escritorio con Tauri |

---

## Notas importantes

- Los archivos son cargados manualmente por el usuario. No se utilizan archivos internos fijos.
- El stock se obtiene exclusivamente desde el archivo de stock cargado en cada sesión.
- Las fechas, semanas y períodos se generan automáticamente desde los datos cargados.
- El sistema funciona completamente offline una vez iniciado (sin dependencia de Google Fonts ni CDN externos).

---

## Historial técnico

La primera versión de este proyecto fue desarrollada como prototipo en **Streamlit** para validar la lógica analítica y el modelo de datos. Debido a requerimientos de interacción avanzada (clics en gráficos, modales reales, experiencia de escritorio), la capa de interfaz fue migrada a **React + FastAPI + Tauri**. La lógica de negocio en Python (carga de datos, cálculos, exportación Excel) se mantiene intacta y reutilizada directamente desde la versión original.

---

## Columnas requeridas en los archivos de entrada

### Archivo de ventas

| Columna | Descripción |
|---------|-------------|
| SKU | Identificador único del producto |
| Producto / Servicio | Nombre del producto |
| Fecha y Hora Venta | Fecha y hora de la transacción |
| Venta Total Bruta | Monto total de la venta |
| Cantidad | Unidades vendidas |

### Archivo de stock

| Columna | Descripción |
|---------|-------------|
| SKU | Identificador único del producto |
| Disponible o Stock | Cantidad disponible actual |

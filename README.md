# Análisis de Ventas e Inventario MYM

Proyecto Python/Streamlit para analizar las ventas de los últimos 6 meses cruzadas con el stock disponible actual, adaptado para uso en escritorio en Windows.

## Estructura del Proyecto

```text
mym_analisis_ventas/
├── app.py                   # Interfaz de usuario (Streamlit)
├── analytics.py             # Lógica y cálculos de negocio
├── data_loader.py           # Cargador y validador de datos
├── launch_app.py            # Lanzador estilo escritorio (puerto libre dinámico + navegador automático)
├── build_desktop.py         # Script de configuración de PyInstaller
├── requirements.txt         # Dependencias del proyecto
├── run_windows.bat          # Legacy launcher
├── build_windows.bat        # Automatizador de empaquetado PyInstaller (.exe)
├── run_desktop.bat          # Acceso directo para iniciar en escritorio
└── README.md                # Este manual
```

---

## Carga de Archivos de Entrada

La aplicación procesa de forma cruzada dos archivos Excel separados (compatibles con `.xlsx` y `.xls`):

### 1. Archivo de Ventas
Contiene el histórico de ventas. La aplicación leerá por defecto la **primera hoja** del archivo. Debe incluir las siguientes columnas obligatorias:
* `SKU`
* `Producto / Servicio`
* `Fecha y Hora Venta`
* `Venta Total Bruta`
* `Cantidad`

### 2. Archivo de Stock
Contiene el stock e inventario actual. La aplicación leerá por defecto la **primera hoja** del archivo. Debe incluir las siguientes columnas obligatorias:
* `SKU`
* `Cantidad Disponible`

> [!NOTE]
> Si subes los archivos de forma cruzada o vacíos, la aplicación lo detectará e indicará un error detallando cuáles columnas se esperaban y cuáles se encontraron en realidad.

---

## Formas de Ejecución

### 1. Modo Escritorio (Recomendado para Usuarios)
Permite arrancar el dashboard sin necesidad de abrir una consola o terminal manualmente.
* Simplemente haz doble clic en el archivo **`run_desktop.bat`**.
* Esto iniciará el servidor en un puerto libre de forma automática y abrirá tu navegador por defecto.

Si deseas ejecutarlo desde consola/terminal:
```bash
source .venv/bin/activate && python launch_app.py
```

### 2. Modo Desarrollo
Si necesitas hacer cambios en el código y contar con la recarga en tiempo real de Streamlit:
```bash
streamlit run app.py
```

### 3. Modo Empaquetado (Generación de .exe)
Para generar un binario ejecutable único de Windows (`dist/MYM_Analisis_Ventas.exe`) que funcione de forma autónoma:
* Ejecuta el script **`build_windows.bat`**.
* *Nota: Asegúrate de probar primero los modos Escritorio y Desarrollo para garantizar estabilidad antes de compilar.*

---

## Análisis y Hallazgos Disponibles
* **Alertas Críticas:** Productos muertos con stock inmovilizado, alertas de quiebre crítico y riesgos de quiebre en base a rotación.
* **Pareto 80/20:** Visualización del 80% de la facturación.
* **Crecimiento/Caída:** Compara la rotación de los últimos 60 días contra el periodo anterior.
* **Exportación Comercial:** Descarga de reportes limpios listos para gerencia.

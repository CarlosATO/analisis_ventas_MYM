# Etapa 1: Construcción del frontend en React
FROM node:20-alpine AS frontend-build
WORKDIR /app/mym_desktop/frontend
COPY mym_desktop/frontend/package.json mym_desktop/frontend/package-lock.json* ./
RUN npm install
COPY mym_desktop/frontend/ ./
RUN npm run build

# Etapa 2: Backend en Python con el frontend ya compilado
FROM python:3.13-slim
WORKDIR /app

# Instalar dependencias de Python
COPY mym_desktop/backend/requirements.txt /app/mym_desktop/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/mym_desktop/backend/requirements.txt

# Copiar el código fuente del backend
COPY mym_desktop/backend/ /app/mym_desktop/backend/

# Copiar los archivos estáticos generados en la Etapa 1
COPY --from=frontend-build /app/mym_desktop/frontend/dist /app/mym_desktop/frontend/dist

WORKDIR /app/mym_desktop/backend
EXPOSE 8000
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]

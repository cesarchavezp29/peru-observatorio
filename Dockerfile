# ---- stage 1: build the React frontend ----
FROM node:20-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# ---- stage 2: python runtime that serves API + built frontend ----
FROM python:3.12-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# data (CSVs + catalog + builder) and backend code
COPY data/ ./data/
COPY backend/ ./backend/
# built frontend from stage 1
COPY --from=web /web/dist ./frontend/dist

# build the DuckDB from the committed CSVs (no ENAHO_ANALYSIS tree needed)
RUN cd data && python build_db.py

EXPOSE 8000
ENV PORT=8000
CMD ["sh", "-c", "cd backend && uvicorn main:app --host 0.0.0.0 --port ${PORT}"]

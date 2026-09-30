FROM python:3.12-slim
RUN pip install --no-cache-dir uv==0.11.0
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY backend ./backend
COPY worker ./worker
ENV PATH="/app/.venv/bin:$PATH" PYTHONPATH="/app/backend" PYTHONUNBUFFERED=1
RUN useradd --uid 10001 --create-home weather && mkdir -p /app/data && chown weather:weather /app/data
USER weather
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Compatibility entrypoint; production Compose shares the backend image.
FROM python:3.12-slim
RUN pip install --no-cache-dir uv==0.11.0
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY backend ./backend
COPY worker ./worker
ENV PATH="/app/.venv/bin:$PATH" PYTHONPATH="/app/backend" PYTHONUNBUFFERED=1
RUN useradd --uid 10001 --create-home weather
USER weather
CMD ["python", "-m", "worker.app.worker"]

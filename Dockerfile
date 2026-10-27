FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DATA_DIR=/app/data PORT=8080
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN useradd --create-home --uid 1000 portfolio && mkdir -p /app/data && chown -R portfolio:portfolio /app
USER portfolio
EXPOSE 8080
CMD ["sh", "-c", "gunicorn --workers 1 --threads 32 --timeout 60 --bind 0.0.0.0:${PORT:-8080} app:app"]

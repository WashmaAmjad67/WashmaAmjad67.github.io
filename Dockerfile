FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY assistant_app assistant_app
ENV ASSISTANT_DATA_DIR=/app/data
VOLUME /app/data
CMD ["python", "-m", "uvicorn", "assistant_app.main:app", "--host", "0.0.0.0", "--port", "8000"]

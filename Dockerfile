FROM python:3.12-slim
WORKDIR /app
COPY server.py /app/server.py
COPY static/ /app/static/
ENV PYTHONUNBUFFERED=1 KH_PUBLIC_DEMO=1 KH_HOST=0.0.0.0 KH_DB_PATH=/app/data/demo.db
RUN mkdir -p /app/data && useradd -r -u 10001 appuser && chown -R appuser:appuser /app
USER appuser
EXPOSE 8080
CMD ["python", "server.py"]

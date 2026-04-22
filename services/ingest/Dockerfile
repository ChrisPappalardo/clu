FROM python:3.12-slim

WORKDIR /app

COPY services/ingest/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY python /app/python
COPY services/ingest /app/services/ingest

ENV PYTHONPATH=/app/python:/app/services/ingest

CMD ["python", "-m", "app.main"]


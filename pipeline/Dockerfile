FROM python:3.11-slim

WORKDIR /app

COPY shared/requirements.txt ./shared-requirements.txt
COPY pipeline/requirements.txt ./
RUN pip install --no-cache-dir -r shared-requirements.txt -r requirements.txt

COPY shared/ ./shared/
COPY db/ ./db/
COPY pipeline/ ./pipeline/

ENV PYTHONPATH=/app

# Placeholder: replace with actual worker entrypoint (e.g. pipeline.workers.consumer)
CMD ["python", "-c", "import time; time.sleep(86400)"]

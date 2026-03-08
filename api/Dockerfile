FROM python:3.11-slim

WORKDIR /app

COPY shared/requirements.txt ./shared-requirements.txt
COPY api/requirements.txt ./
RUN pip install --no-cache-dir -r shared-requirements.txt -r requirements.txt

COPY shared/ ./shared/
COPY db/ ./db/
COPY api/ ./api/

ENV PYTHONPATH=/app
EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM python:3.12-slim

WORKDIR /app

# psycopg[binary] ships its own libpq; no system build deps required.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

# Run as a non-root citizen.
RUN useradd --uid 10001 --no-create-home committee
USER 10001

EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]

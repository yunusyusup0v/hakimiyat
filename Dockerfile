FROM python:3.12-slim

WORKDIR /hakimiyat_backend

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    libcairo2-dev \
    gcc \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

EXPOSE 8008 5432

CMD ["uvicorn", "backend.core:app", "--host", "0.0.0.0", "--port", "8008"]
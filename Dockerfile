FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

RUN mkdir -p assets/images

EXPOSE 5000

CMD ["gunicorn", "--preload", "--bind", "0.0.0.0:5000", "--workers", "3", "--timeout", "120", "main:app"]

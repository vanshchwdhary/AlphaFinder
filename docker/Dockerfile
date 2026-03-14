FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md /app/
COPY src /app/src
COPY data /app/data

RUN pip install -U pip && pip install -e ".[ai,dashboard]"

CMD ["stock-scout", "--help"]


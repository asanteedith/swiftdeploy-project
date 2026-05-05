FROM python:3.10-slim

RUN useradd -m appuser

WORKDIR /app

COPY . .

RUN pip install flask

USER appuser

ENV MODE=stable

ENV APP_VERSION=v1

ENV APP_PORT=3000

CMD ["python", "main.py"]
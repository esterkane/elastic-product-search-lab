FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

WORKDIR /app

COPY apps/api/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY apps/api/app ./app
COPY apps/api/alembic.ini ./alembic.ini
COPY apps/api/pytest.ini ./pytest.ini
COPY apps/api/migrations ./migrations
COPY apps/api/tests ./tests

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]

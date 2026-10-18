FROM python:3.11.11-slim-bookworm

WORKDIR /app
COPY . /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

RUN python -m compileall -q src

CMD ["python", "-m", "unittest", "discover", "-s", "tests", "-v"]

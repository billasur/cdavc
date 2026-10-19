FROM python:3.11.11-slim-bookworm@sha256:081075da77b2b55c23c088251026fb69a7b2bf92471e491ff5fd75c192fd38e5

RUN apt-get update && \
    apt-get install -y --no-install-recommends git && \
    rm -rf /var/lib/apt/lists/* && \
    git config --system --add safe.directory "*" && \
    git config --system init.defaultBranch main && \
    git config --system user.email "test@example.invalid" && \
    git config --system user.name "CD-AVC tests"

WORKDIR /app
COPY . /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

RUN python -m compileall -q src

CMD ["python", "-m", "unittest", "discover", "-s", "tests", "-v"]

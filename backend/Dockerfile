FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=7860

WORKDIR /app

RUN apt-get update \
    && apt-get install --no-install-recommends -y ffmpeg fontconfig fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY app ./app
COPY docker ./docker

RUN pip install --no-cache-dir .

EXPOSE 7860

CMD ["sh", "docker/start.sh"]

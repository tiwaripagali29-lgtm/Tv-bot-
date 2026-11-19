FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip uninstall -y pyrogram pyrofork hydrogram || true

RUN pip install --no-cache-dir kurigram py-tgcalls==2.3.3 aiohttp tgcrypto

COPY . .

CMD ["python", "main.py"]

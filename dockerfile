FROM python:3.13-slim
RUN apt-get update && apt-get install -y --no-install-recommends tini && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PYTHONPATH=/app
ENTRYPOINT ["/usr/bin/tini","--"]
CMD ["uvicorn","src.app:app","--host","0.0.0.0","--port","8000"]
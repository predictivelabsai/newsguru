FROM python:3.13-slim

WORKDIR /app

# Copy all source first (setuptools needs package dirs to resolve)
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -e .

EXPOSE 5020

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:5020/')"

CMD ["python", "main.py"]

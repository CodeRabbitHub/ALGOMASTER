FROM python:3.12-slim

WORKDIR /app

# No network access at runtime; install deps at build time
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY executor.py .

# Non-root user for extra isolation
RUN useradd -m runner
USER runner

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "15", "executor:app"]

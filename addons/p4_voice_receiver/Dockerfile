FROM python:3.13-alpine
WORKDIR /app
COPY server.py /app/server.py
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
CMD ["python", "/app/server.py"]

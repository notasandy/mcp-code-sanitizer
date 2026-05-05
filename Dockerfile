FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV GROQ_API_KEY=""
ENV GROQ_MODEL="llama-3.3-70b-versatile"
ENV CACHE_TTL="3600"
ENV CACHE_MAX="200"

CMD ["python", "server.py"]

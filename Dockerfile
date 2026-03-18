FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DATA_DIR=/data

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot.py config.py ./
COPY lastperson07 ./lastperson07

RUN mkdir -p /app/downloads
RUN mkdir -p /data

VOLUME ["/data"]

CMD ["python", "bot.py"]

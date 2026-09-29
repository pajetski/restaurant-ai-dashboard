FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 APP_ENV=production DATA_DIR=/data
WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN useradd -m app && mkdir -p /data && chown app /data
USER app
VOLUME /data
EXPOSE 8501
HEALTHCHECK CMD python -c "import urllib.request as u; u.urlopen('http://localhost:8501/_stcore/health')"

CMD ["sh", "-c", "streamlit run dashboard.py --server.port=${PORT:-8501} --server.address=0.0.0.0"]

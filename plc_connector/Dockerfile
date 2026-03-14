FROM python:3.11-slim

# python-snap7 1.3+ ships a bundled snap7 shared library for linux-x86_64,
# so no additional system packages are needed.

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY plc_connector.py .
COPY tag_config.json .

CMD ["python", "plc_connector.py"]

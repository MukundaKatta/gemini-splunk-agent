FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install git so pip can pull the geminilens dep straight from GitHub.
RUN apt-get update && apt-get install -y --no-install-recommends git \
 && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY src ./src
COPY app ./app
COPY README.md LICENSE ./

RUN pip install .

EXPOSE 8080

# Cloud Run sets PORT; Streamlit needs --server.port to match.
CMD streamlit run app/dashboard.py \
    --server.port "${PORT:-8080}" \
    --server.address 0.0.0.0 \
    --server.headless true \
    --browser.gatherUsageStats false

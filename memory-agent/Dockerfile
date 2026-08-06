FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/app/.cache/huggingface \
    SENTENCE_TRANSFORMERS_HOME=/app/.cache/sentence_transformers \
    TRANSFORMERS_CACHE=/app/.cache/huggingface/transformers \
    MEMORY_DB_PATH=/app/chroma_data \
    EMBEDDING_MODEL=all-MiniLM-L6-v2 \
    DEDUP_THRESHOLD=0.85

ARG INSTALL_CPU_TORCH=true
ARG HF_ENDPOINT=https://huggingface.co
ENV HF_ENDPOINT=${HF_ENDPOINT}

WORKDIR /app

COPY requirements.txt .
RUN if [ "$INSTALL_CPU_TORCH" = "true" ]; then \
        pip install --no-cache-dir torch==2.5.1+cpu --extra-index-url https://download.pytorch.org/whl/cpu; \
    fi \
    && pip install --no-cache-dir -r requirements.txt \
    && python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

ENV HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1

COPY . .
RUN mkdir -p /app/chroma_data

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

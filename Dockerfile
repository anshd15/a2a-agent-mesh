FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir uv
COPY pyproject.toml ./
COPY mesh ./mesh
COPY scripts ./scripts
RUN uv pip install --system --no-cache ".[tracing]"
ENV HOST=0.0.0.0 PYTHONUNBUFFERED=1
# Each compose service overrides this with the agent it runs.
CMD ["adk", "web", "--host", "0.0.0.0", "--port", "8000", "mesh"]

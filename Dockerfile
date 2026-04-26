FROM ghcr.io/astral-sh/uv:python3.13-bookworm AS dependencies
WORKDIR /app
COPY pyproject.toml README.md ./
RUN uv sync --group dev

FROM python:3.13-bookworm
ENV PYTHONPATH=.
WORKDIR /app
COPY --from=dependencies /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"
COPY ./ /app/

ENTRYPOINT [ "sh", "entrypoint.sh" ]
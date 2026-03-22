FROM ghcr.io/astral-sh/uv:python3.13-bookworm AS base
ENV PYTHONPATH=.
WORKDIR /app
COPY ./ /app/

FROM base AS dependencies
RUN uv sync --group testing

FROM base AS final
COPY --from=dependencies /app/.venv /app/.venv

ENTRYPOINT [ "sh", "entrypoint.sh" ]
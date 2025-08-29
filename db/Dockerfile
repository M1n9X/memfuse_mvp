FROM postgres:17

RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-17-pgvector \
    && rm -rf /var/lib/apt/lists/*

# The extension will be enabled by init SQL in /docker-entrypoint-initdb.d

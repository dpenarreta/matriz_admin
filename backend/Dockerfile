# Imagen de producción del backend Django. No es multi-stage: no hay un
# paso de build/compilación previo y `collectstatic`/`migrate` deben correr
# en el arranque del contenedor, con las variables de entorno reales — nunca
# en tiempo de build, ver entrypoint.sh.
# Fijada a bookworm (Debian 12): el repositorio de Microsoft que instala el
# driver ODBC de abajo es el de Debian 12; la etiqueta "3.12-slim" a secas ya
# apunta a Debian 13 y el build fallaba.
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.production \
    ACCEPT_EULA=Y

WORKDIR /app

# Driver ODBC 18 de Microsoft para SQL Server: no se distribuye en los
# repositorios de Debian, hay que sumar el repositorio oficial de Microsoft
# (ver https://learn.microsoft.com/sql/connect/odbc/linux-mac/installing-the-microsoft-odbc-driver-for-sql-server).
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl gnupg unixodbc-dev gcc g++ \
    && curl -sSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && curl -sSL https://packages.microsoft.com/config/debian/12/prod.list -o /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends msodbcsql18 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 appuser

COPY requirements/ requirements/
RUN pip install --no-cache-dir -r requirements/prod.txt

COPY . .
# /app/media: evidencias PDF (volumen en docker-compose.prod.yml).
RUN chmod +x entrypoint.sh && mkdir -p /app/media && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]

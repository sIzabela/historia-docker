FROM mcr.microsoft.com/playwright/python:focal

WORKDIR /app

# Instalacja podstawowych narzędzi, bibliotek oraz konfiguracja repozytorium Microsoft
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    rclone \
    curl \
    libcurl4-openssl-dev \
    gcc \
    g++ \
    libc6-dev \
    unixodbc-dev \
    gnupg \
    libicu66 \
    libharfbuzz-icu0 \
    libjpeg-turbo8 \
    libwebp6 \
    libffi7 \
    libx264-155 && \
    # Instalacja sterownika MS ODBC, narzędzi MSSQL i unixODBC dev
    version=$(grep VERSION_ID /etc/os-release | cut -d '"' -f 2) && \
    if ! echo "18.04 20.04 22.04 24.04" | grep -wq "$version"; then \
        echo "Ubuntu $version is not currently supported." && exit 1; \
    fi && \
    # Pobranie pakietu konfiguracyjnego repozytorium Microsoft
    curl -sSL -O https://packages.microsoft.com/config/ubuntu/${version}/packages-microsoft-prod.deb && \
    dpkg -i packages-microsoft-prod.deb && \
    rm packages-microsoft-prod.deb && \
    apt-get update && \
    # Instalacja sterownika, narzędzi MSSQL oraz nagłówków unixODBC
    ACCEPT_EULA=Y apt-get install -y msodbcsql18 mssql-tools18 unixodbc-dev && \
    rm -rf /var/lib/apt/lists/*

# Ustawienie PATH dla narzędzi MSSQL
ENV PATH="/opt/mssql-tools18/bin:${PATH}"

# Kopiowanie plików aplikacji do obrazu
COPY . .

# Kopiowanie pliku konfiguracyjnego dla rclone
COPY rclone.conf /root/.config/rclone/rclone.conf

# Aktualizacja pip, instalacja zależności
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    python -m playwright install

# Komenda uruchamiająca aplikację
CMD ["python", "-u", "main.py"]
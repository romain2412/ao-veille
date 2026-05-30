FROM python:3.12-slim

# Installer git + dépendances système pour Playwright/Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl \
    # Dépendances Chromium (Playwright)
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
    libgbm1 libasound2 libpango-1.0-0 libcairo2 libx11-6 libxext6 \
    libxrender1 fonts-liberation wget ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Pré-installer les dépendances Python (layer cachée)
# On copie juste le requirements pour bénéficier du cache Docker
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Installer le navigateur Chromium pour Playwright (layer cachée)
RUN playwright install chromium

# Copier uniquement l'entrypoint dans l'image
# Le code applicatif sera cloné depuis GitHub au démarrage
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENV GIT_BRANCH=main

CMD ["/docker-entrypoint.sh"]

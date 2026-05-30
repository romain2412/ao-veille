FROM python:3.12-slim

# Installer git (nécessaire pour cloner le code au démarrage)
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copier uniquement l'entrypoint dans l'image
# Le code applicatif sera cloné depuis GitHub au démarrage
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Variable d'environnement pour la branche Git (modifiable sans rebuild)
ENV GIT_BRANCH=main

CMD ["/docker-entrypoint.sh"]

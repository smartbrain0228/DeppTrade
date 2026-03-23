# Deployment Demo Runbook

Ce document decrit une mise en ligne minimale du projet pour faire tourner le bot en mode demo automatique dans un environnement plus stable que le local.

## Objectif

Valider:

- l'analyse continue des strategies
- l'ouverture automatique de trades demo
- la gestion automatique des trades ouverts
- le rendu web en conditions reelles
- les notifications Telegram

Sans engager de capital reel.

## Mode recommande

Pour la premiere mise en ligne:

- `APP_ENV=development` ou `production`
- `ENABLE_WORKER=true`
- `ENABLE_DEMO_ENGINE=true`
- `MARKET_DATA_MODE=live`

Si tu veux un environnement en ligne sans dependance exchange au debut:

- `MARKET_DATA_MODE=mock`

## Prerequis

- repository GitHub prive deja en place
- serveur Linux ou Windows accessible
- Docker et Docker Compose disponibles
- PostgreSQL
- variables d'environnement preparees

## Variables minimales

```env
APP_ENV=production
ENABLE_WORKER=true
ENABLE_DEMO_ENGINE=true
MARKET_DATA_MODE=live

DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/trading_bot
REDIS_URL=redis://redis:6379/0

JWT_SECRET_KEY=replace-me
ADMIN_PASSWORD=replace-me
ADMIN_SESSION_SECRET=replace-me

TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

## Sequence recommandee

### 1. Recuperer le projet

```bash
git clone <repo-url>
cd trade-execution-engine
```

### 2. Creer `.env`

Utiliser `.env.example` comme base puis remplacer les secrets.

### 3. Demarrer la base

```bash
docker compose up -d postgres redis
```

### 4. Appliquer les migrations

```bash
alembic upgrade head
```

### 5. Creer l'admin

```bash
python create_admin.py
```

### 6. Initialiser les assignments

```bash
python setup_multi_strategy.py
```

### 7. Build frontend

```bash
cd frontend
npm install
npm run build
cd ..
```

### 8. Lancer l'application

```bash
uvicorn trading_bot_backend.app.main:app --host 0.0.0.0 --port 8000
```

## Verification apres demarrage

Attendus:

- le backend repond sur `/`
- le frontend est servi
- les logs montrent `Trade worker started`
- les logs montrent `Demo engine started`
- l'overview web affiche:
  - environnement
  - mode marche
  - worker `ON`
  - demo engine `ON`

## Ce qu'il faut observer

### Web

- separation claire des strategies `Intraday` et `Scalping`
- cartes `Wins`, `Fails`, `Skipped`
- activite des trades
- runtime visible dans l'overview

### Telegram

- trade ouvert
- trade ferme
- trade skipped
- strategie pausee si le cycle atteint la limite

## Risques connus

- `MARKET_DATA_MODE=live` depend des exchanges
- Telegram depend du reseau sortant du serveur
- si l'observabilite reste trop legere, ajouter ensuite:
  - logs persistants
  - reverse proxy
  - supervision process
  - sauvegardes DB

## Prochaine evolution recommande

Apres cette premiere mise en ligne demo:

1. ajouter une vraie supervision process
2. ajouter une route de health/runtime detaillee
3. ajouter des logs structures
4. ajouter un runbook de rollback

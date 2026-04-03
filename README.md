# Market Operations Console

Market Operations Console est une console web de supervision, d'analyse et d'execution de strategies de trading crypto.

Le projet combine:

- analyse de strategies multi-timeframes
- scan de signaux
- execution et suivi de trades
- dashboard web operateur
- notifications Telegram
- mode demo automatique pour valider rapidement une strategie sans engager de capital

## Stack

### Backend

- FastAPI
- SQLAlchemy async
- Alembic
- PostgreSQL
- Redis optionnel

### Frontend

- React
- TypeScript
- Vite
- Zustand
- lightweight-charts

## Etat actuel

Le projet est deja a un stade MVP fonctionnel en local avec:

- authentification
- administration et assignments utilisateur / symbole / strategie
- scan et execution de signaux
- overlays et historique de signaux
- suivi de trades
- notifications Telegram
- worker de gestion des trades
- demo engine automatique
- mode `mock` / `local` pour valider le moteur sans dependre des exchanges

## Installation locale

### 1. Cloner et installer le backend

```powershell
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Installation reproductible:

```powershell
.\venv\Scripts\Activate.ps1
pip install -r requirements.lock.txt
```

### 2. Configurer l'environnement

```powershell
Copy-Item .env.example .env
```

### 3. Demarrer PostgreSQL et Redis

```powershell
docker compose up -d
```

### 4. Appliquer les migrations

```powershell
.\venv\Scripts\Activate.ps1
alembic upgrade head
```

### 5. Creer l'admin local

```powershell
.\venv\Scripts\python.exe create_admin.py
```

### 6. Initialiser les strategies locales

```powershell
.\venv\Scripts\python.exe setup_multi_strategy.py
```

## Lancement local

### Backend standard

```powershell
.\venv\Scripts\python.exe -m uvicorn trading_bot_backend.app.main:app --reload
```

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

### Frontend build via backend

```powershell
cd frontend
npm run build
```

Une fois le frontend build, le backend peut servir l'interface directement.

## Modes d'execution

Le backend pilote deux axes:

- activation des boucles de fond
- source des donnees marche

Par defaut:

- `APP_ENV=development` ou `test` n'active pas automatiquement le worker ni le demo engine
- `MARKET_DATA_MODE=live` reste le mode par defaut

Variables utiles:

- `ENABLE_WORKER=true`
- `ENABLE_DEMO_ENGINE=true`
- `MARKET_DATA_MODE=mock`
- `MARKET_DATA_MODE=local`
- `MARKET_DATA_MODE=live`

## Scripts utiles

### Demo auto locale sur donnees mock

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\start_auto_demo_local.ps1
```

URL:

- `http://127.0.0.1:8002/`

### Demo auto locale sur donnees live

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\start_auto_demo_live.ps1
```

URL:

- `http://127.0.0.1:8003/`

### Arret des instances auto-demo

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\stop_auto_demo.ps1
```

## Validation

### Backend

```powershell
.\venv\Scripts\pytest.exe -q
```

### Frontend

```powershell
cd frontend
npm run build
```

## Documentation utile

- [Etat courant](docs/CURRENT_STATE.md)
- [Tache courante](docs/CURRENT_TASK.md)
- [Contexte IA](docs/AI_CONTEXT.md)
- [Architecture](docs/PROJECT_ARCHITECTURE.md)
- [Resume de reprise](docs/RESUME_FOR_NEXT_CHAT.md)

## Deploiement demo

Le prochain objectif recommande pour une validation plus stable est un deploiement en ligne en mode demo automatique.

Voir:

- [Runbook de deploiement demo](docs/DEPLOYMENT_DEMO.md)

## Securite

- ne jamais versionner `.env`
- ne jamais pousser de cles API ou secrets Telegram
- utiliser `.env.example` comme modele public

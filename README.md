# Bot Trading Copilot

## Dépendances

Ce projet utilise deux fichiers :

- `requirements.txt` : la liste logique des dépendances à installer en dev.
- `requirements.lock.txt` : un lockfile avec les versions figées pour des environnements reproductibles (prod/CI).

### Installation (dev)

```powershell
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Configuration locale

```powershell
Copy-Item .env.example .env
```

### Services locaux (PostgreSQL + Redis)

```powershell
docker compose up -d
```

### Installation (reproductible)

```powershell
.\venv\Scripts\Activate.ps1
pip install -r requirements.lock.txt
```

### Mise à jour du lockfile

```powershell
.\venv\Scripts\Activate.ps1
pip freeze > requirements.lock.txt
```

### Migrations DB (Alembic)

```powershell
.\venv\Scripts\Activate.ps1
alembic upgrade head
```

### Bootstrap API (admin + seed)

Use the request sequence in `docs/mvp_bootstrap.http`.

## Modes d'execution

Le backend a maintenant deux axes de mode:

- demarrage des boucles de fond
- source des donnees marche

Par defaut:

- `APP_ENV=development` ou `test` ne lance pas le worker ni le demo engine
- `MARKET_DATA_MODE=live` reste le comportement par defaut

Variables utiles:

- `ENABLE_WORKER=true` pour lancer explicitement le worker en local
- `ENABLE_DEMO_ENGINE=true` pour lancer explicitement le demo engine en local
- `MARKET_DATA_MODE=mock` ou `MARKET_DATA_MODE=local` pour utiliser des candles deterministes sans appel exchange

Exemples de demarrage:

### Mode local silencieux

```powershell
$env:APP_ENV="development"
Remove-Item Env:ENABLE_WORKER -ErrorAction SilentlyContinue
Remove-Item Env:ENABLE_DEMO_ENGINE -ErrorAction SilentlyContinue
Remove-Item Env:MARKET_DATA_MODE -ErrorAction SilentlyContinue
.\venv\Scripts\python.exe -m uvicorn trading_bot_backend.app.main:app --reload
```

### Mode local silencieux avec marche mock

```powershell
$env:APP_ENV="development"
$env:MARKET_DATA_MODE="mock"
.\venv\Scripts\python.exe -m uvicorn trading_bot_backend.app.main:app --reload
```

### Mode local avec worker

```powershell
$env:APP_ENV="development"
$env:ENABLE_WORKER="true"
$env:MARKET_DATA_MODE="mock"
.\venv\Scripts\python.exe -m uvicorn trading_bot_backend.app.main:app --reload
```

### Mode local avec demo engine

```powershell
$env:APP_ENV="development"
$env:ENABLE_DEMO_ENGINE="true"
$env:MARKET_DATA_MODE="mock"
.\venv\Scripts\python.exe -m uvicorn trading_bot_backend.app.main:app --reload
```

### Mode production-like

```powershell
$env:APP_ENV="production"
$env:MARKET_DATA_MODE="live"
$env:ENABLE_WORKER="true"
$env:ENABLE_DEMO_ENGINE="true"
.\venv\Scripts\python.exe -m uvicorn trading_bot_backend.app.main:app
```

Notes:

- `mock` est pratique pour valider `scan`, `execute`, le worker et le demo engine sans connectivite exchange.
- `live` est le mode a conserver pour une validation proche de la production.
- le frontend consomme les memes routes; le switch se fait cote backend uniquement.

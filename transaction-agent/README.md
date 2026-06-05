# Transaction Intelligence AI Agent

An OpenAI function-calling agent that builds a unified transaction intelligence report for a Bungee transaction hash or user address by querying:

- Metabase backed by Postgres
- Loki transaction API
- Mixpanel analytics export/profile APIs

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Fill `.env` with your real credentials. No credentials are hardcoded in this project.

## Run

```bash
python main.py 0xTRANSACTION_HASH
```

You can also pass a wallet address:

```bash
python main.py 0xUSER_ADDRESS
```

The agent uses OpenAI tool calling to decide which data sources to query and how to merge the results into a coherent report.

## Run the API and Frontend

Start the backend:

```bash
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

Start the frontend:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The frontend calls `POST http://localhost:8000/api/intelligence`.

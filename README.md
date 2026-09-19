# mini-rag

This is a minimal implementation of the RAG model for question answering.

## The Course

This is an educational project where all of the codes where explained (step by step) via a set of `Arabic` youtube videos. at [mini-RAG | From notebooks to the PRODUCTION](https://www.youtube.com/playlist?list=PLvLvlVqNQGHCUR2p0b8a0QpVjDUg50wQj):

## Requirements

- Python 3.13.14

### Install Dependencies

```bash
sudo apt update
sudo apt install libpq-dev gcc python3-dev
```

#### Install Python using uv

1) [Download and install uv](https://docs.astral.sh/uv/getting-started/installation/)
2) Create a new environment using the following command:

```bash
uv init
uv python install 3.13.14
```

### (Optional) Setup you command line interface for better readability

```bash
export PS1="\[\033[01;32m\]\u@\h:\w\n\[\033[00m\]\$ "
```

### (Optional) Run Ollama Local LLM Server using Colab + Ngrok

- Check the [notebook](https://colab.research.google.com/drive/1KNi3-9KtP-k-93T3wRcmRe37mRmGhL9p?usp=sharing) + [Video](https://youtu.be/-epZ1hAAtrs)

## Installation

### Install the required packages

```bash
uv sync
```

### Setup the environment variables

```bash
cp .env.example .env
```

### Run fastapi using uvicorn

```bash
cd src
```

```bash
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Run Alembic Migration

```bash
alembic upgrade head
```

Set your environment variables in the `.env` file. Like `OPENAI_API_KEY` value.

## Run Docker Compose Services

```bash
cd docker
cp .env.example .env
```

- update `.env` with your credentials

```bash
cd docker
sudo docker compose up -d
```

## Access Services

- **FastAPI**: <http://localhost:8000>
- **Flower Dashboard**: <http://localhost:5555> (admin/password from env)
- **Grafana**: <http://localhost:3000>
- **Prometheus**: <http://localhost:9090>

## Run the FastAPI server (Development Mode)

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 5000
```

## Celery (Development Mode)

For development, you can run Celery services manually instead of using Docker:

To Run the **Celery worker**, you need to run the following command in a separate terminal:

```bash
python -m celery -A celery_app worker --queues=default,file_processing,data_indexing --loglevel=info
```

To run the **Beat scheduler**, you can run the following command in a separate terminal:

```bash
python -m celery -A celery_app beat --loglevel=info
```

To Run **Flower Dashboard**, you can run the following command in a separate terminal:

```bash
python -m celery -A celery_app flower --conf=flowerconfig.py
```

open your browser and go to `http://localhost:5555` to see the dashboard.

## POSTMAN Collection

Download the POSTMAN collection from [/assets/mini-rag-app.postman_collection.json](/assets/mini-rag-app.postman_collection.json)

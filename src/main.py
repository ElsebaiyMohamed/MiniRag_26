from fastapi import FastAPI
from dotenv import load_dotenv

load_dotenv(".env")

from src.routes import base

app = FastAPI(title="MiniRag_26", version="0.1", description="Question Answering System")

app.include_router(base.base_router)



from fastapi import FastAPI

from routes import base

app = FastAPI(title="MiniRag_26", version="0.1", description="Question Answering System")

app.include_router(base.base_router)



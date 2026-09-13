from fastapi import FastAPI

from routes import base, data

app = FastAPI(title="MiniRag_26", version="0.1", description="Question Answering System")

app.include_router(base.base_router)
app.include_router(data.data_router)



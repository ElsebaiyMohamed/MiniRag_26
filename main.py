from fastapi import FastAPI

app = FastAPI(title="MiniRag_26", version="0.1", description="Question Answering System")

@app.get("/welcome")
def welcome():
    return {"message": "Welcome to MiniRag_26!"}



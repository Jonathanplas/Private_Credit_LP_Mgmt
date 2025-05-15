# filepath: backend/main.py
from fastapi import FastAPI
from .db import engine, Base
from .routes import lp_routes

app = FastAPI()

# Initialize database
Base.metadata.create_all(bind=engine)

# Include routes
app.include_router(lp_routes.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the i80 Developer Case Study API"}
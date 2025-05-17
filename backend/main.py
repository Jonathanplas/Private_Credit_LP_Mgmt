from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.db import engine, Base
from backend.routes import lp_routes

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
Base.metadata.create_all(bind=engine)

# Include routes
app.include_router(lp_routes.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the i80 Developer Case Study API"}
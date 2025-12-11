import sys
from pathlib import Path

# Add parent directory to Python path to access agents, optimizers, etc.
backend_dir = Path(__file__).resolve().parent
parent_dir = backend_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.auth import router as auth_router
from app.database import engine
from app import models
from app.routes.main_router import router as stock_router
# Create tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="ByteBank API",
    description="Secure authentication API with PostgreSQL",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(stock_router,prefix="/api/stocks", tags=["Stocks"])

@app.get("/")
def root():
    return {"message": "Welcome to ByteBank API"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}

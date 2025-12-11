from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine
from app import models
from app.routes.main_router import router as main_router

# Create tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="ByteBank API",
    description="Secure authentication API",
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
app.include_router(main_router, tags=["screener"])

@app.get("/")
def root():
    return {"message": "Welcome to ByteBank API"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

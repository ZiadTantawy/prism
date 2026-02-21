"""Main API router configuration."""

from fastapi import APIRouter

router = APIRouter()
from routes import (auth)

router.include_router(auth.router, prefix="/auth", tags=["auth"])
"""API router: mount versioned route modules."""

from fastapi import APIRouter

router = APIRouter()
from routes import auth

router.include_router(auth.router, prefix="/auth", tags=["auth"])
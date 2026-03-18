from fastapi import APIRouter, Depends

from app.api.v1.accounts import router as accounts_router
from app.api.v1.categories import router as categories_router
from app.api.v1.profile import router as profile_router
from app.api.v1.transactions import router as transactions_router
from app.core.security import AuthenticatedUser, get_current_user

api_router = APIRouter()
api_router.include_router(profile_router)
api_router.include_router(accounts_router)
api_router.include_router(categories_router)
api_router.include_router(transactions_router)

@api_router.get("/ping")
async def ping():
    return {"pong": True}


@api_router.get("/me")
async def read_current_user(current_user: AuthenticatedUser = Depends(get_current_user)):
    return {
        "user_id": current_user.user_id,
        "email": current_user.email,
        "role": current_user.role,
    }
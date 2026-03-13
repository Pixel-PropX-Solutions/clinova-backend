from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from app.auth.jwt import decode_access_token
from app.auth.models import TokenData
from app.database import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)

async def get_current_user(request: Request, token: str | None = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Browser download flows may not include Authorization header;
    # fallback to auth cookie for compatibility.
    if not token:
        cookie_token = request.cookies.get("access_token")
        if cookie_token:
            token = cookie_token.removeprefix("Bearer ").strip()

    if not token:
        raise credentials_exception

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
        
    email: str = payload.get("sub")
    role: str = payload.get("role")
    clinic_id: str = payload.get("clinic_id")
    
    if email is None:
        raise credentials_exception
        
    token_data = TokenData(email=email, role=role, clinic_id=clinic_id)
    return token_data

    
async def get_current_active_user(current_user: TokenData = Depends(get_current_user)):
    return current_user

async def get_current_admin(current_user: TokenData = Depends(get_current_active_user)):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )
    return current_user

async def get_current_clinic_user(current_user: TokenData = Depends(get_current_active_user)):
    if current_user.role != "clinic_user" and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )
    return current_user

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Response, Request
from fastapi.security import OAuth2PasswordRequestForm
from app.auth.models import Token, UserInDB
from app.auth.pass_utils import verify_password, get_password_hash
from app.auth.jwt import create_access_token, decode_access_token
from datetime import timedelta
from app.database import get_db
from pydantic import BaseModel, EmailStr
from typing import Optional
from app.utils.email import send_email
import random
import string
router = APIRouter(prefix="/auth", tags=["Authentication"])

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: str = "admin"

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class ForgotPassword(BaseModel):
    email: EmailStr

@router.post("/token", response_model=Token)
async def login_for_access_token(response: Response, form_data: OAuth2PasswordRequestForm = Depends()):
    db = get_db()
    # OAuth2 specifies 'email' but we are using it to accept email
    user = await db.users.find_one({"email": form_data.email})
    
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token_data = {"sub": user["email"], "role": user.get("role", "clinic_user"), "clinic_id": str(user.get("clinic_id"))}
    access_token = create_access_token(data=token_data)
    refresh_token = create_access_token(data=token_data, expires_delta=timedelta(days=7))
    
    response.set_cookie(key="access_token", value=access_token, httponly=True, max_age=1800)
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, max_age=604800)

    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer", "role": user.get("role", "clinic_user")}

@router.post("/login", response_model=Token)
async def login(response: Response, login_data: UserLogin):
    db = get_db()
    user = await db.users.find_one({"email": login_data.email})
    
    if not user or not verify_password(login_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token_data = {"sub": user["email"], "role": user.get("role", "clinic_user"), "clinic_id": str(user.get("clinic_id"))}
    access_token = create_access_token(data=token_data)
    refresh_token = create_access_token(data=token_data, expires_delta=timedelta(days=7))
    
    response.set_cookie(key="access_token", value=access_token, httponly=True, max_age=1800, samesite="lax")
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, max_age=604800, samesite="lax")

    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer", "role": user.get("role", "clinic_user")}

class RefreshRequest(BaseModel):
    refresh_token: str | None = None

@router.post("/refresh", response_model=Token)
async def refresh_token(request: Request, response: Response, body: RefreshRequest = None):
    # Try getting token from body, then cookies
    token = None
    if body and body.refresh_token:
        token = body.refresh_token
    if not token and "refresh_token" in request.cookies:
        token = request.cookies.get("refresh_token")
        
    if not token:
        raise HTTPException(status_code=401, detail="Refresh token missing")
        
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
        
    email = payload.get("sub")
    role = payload.get("role")
    clinic_id = payload.get("clinic_id")
    
    token_data = {"sub": email, "role": role, "clinic_id": clinic_id}
    access_token = create_access_token(data=token_data)
    
    response.set_cookie(key="access_token", value=access_token, httponly=True, max_age=1800, samesite="lax")
    
    return {"access_token": access_token, "refresh_token": token, "token_type": "bearer", "role": role or "clinic_user"}

@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return {"message": "Successfully logged out."}

@router.post("/create-admin", status_code=status.HTTP_201_CREATED)
async def create_admin(user: UserCreate):
    db = get_db()
    
    existing_user = await db.users.find_one({"email": user.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
        
    hashed_password = get_password_hash(user.password)
    new_user = {
        "email": user.email,
        "username": user.email,
        "role": user.role,
        "hashed_password": hashed_password,
        "is_active": True
    }
    
    await db.users.insert_one(new_user)
    return {"message": "Admin user created successfully"}

@router.post("/forgot-password")
async def forgot_password(data: ForgotPassword, background_tasks: BackgroundTasks):
    db = get_db()
    
    user = await db.users.find_one({"email": data.email})
    if not user:
        # Don't leak whether user exists or not
        return {"message": "If this email is registered, you will receive your new password shortly."}
        
    new_password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    hashed_password = get_password_hash(new_password)
    
    await db.users.update_one(
        {"email": data.email},
        {"$set": {"hashed_password": hashed_password}}
    )
    
    email_subject = "Password Reset Request"
    email_body = f"Hello,\n\nYour password has been successfully reset. Here is your temporary password: {new_password}\n\nPlease login and change your password.\n\nBest Regards,\nThe Team"
    
    background_tasks.add_task(send_email, data.email, email_subject, email_body)
    
    return {"message": "If this email is registered, you will receive your new password shortly."}

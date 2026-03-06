from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from app.auth.models import Token, UserInDB
from app.auth.pass_utils import verify_password, get_password_hash
from app.auth.jwt import create_access_token
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
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    db = get_db()
    # OAuth2 specifies 'email' but we are using it to accept email
    user = await db.users.find_one({"email": form_data.email})
    
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(
        data={"sub": user["email"], "role": user.get("role", "clinic_user"), "clinic_id": user.get("clinic_id")}
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/login", response_model=Token)
async def login(login_data: UserLogin):
    db = get_db()
    user = await db.users.find_one({"email": login_data.email})
    
    if not user or not verify_password(login_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(
        data={"sub": user["email"], "role": user.get("role", "clinic_user"), "clinic_id": user.get("clinic_id")}
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/logout")
async def logout():
    # As we are using JWT, we just notify the client to discard the token.
    # In a more advanced setup, you could blacklist the token in Redis/DB.
    return {"message": "Successfully logged out. Please remove the token on the client side."}

@router.post("/create-admin", status_code=status.HTTP_201_CREATED)
async def create_admin(user: UserCreate):
    db = get_db()
    
    existing_user = await db.users.find_one({"email": user.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
        
    hashed_password = get_password_hash(user.password)
    new_user = {
        "email": user.email,
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

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from app.auth.dependencies import get_current_clinic_user
from app.auth.models import TokenData
from app.auth.pass_utils import verify_password, get_password_hash
from app.clinics.models import ClinicSettingsUpdate
from app.database import get_db
from app.config import settings
from bson import ObjectId
from pydantic import BaseModel
from typing import Optional
import cloudinary
import cloudinary.uploader

# Configure Cloudinary
cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
)

router = APIRouter(prefix="/settings", tags=["Settings"])


# --- Get Clinic Profile ---
@router.get("/profile")
async def get_profile(current_user: TokenData = Depends(get_current_clinic_user)):
    db = get_db()
    clinic = await db.clinics.find_one({"_id": ObjectId(current_user.clinic_id)})
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")

    clinic["_id"] = str(clinic["_id"])
    return clinic


# --- Update Clinic Profile (name, phone, logo_url, default_template_id) ---
@router.patch("/profile")
async def update_profile(
    update_data: ClinicSettingsUpdate,
    current_user: TokenData = Depends(get_current_clinic_user),
):
    db = get_db()
    data = {k: v for k, v in update_data.model_dump().items() if v is not None}

    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")

    result = await db.clinics.update_one(
        {"_id": ObjectId(current_user.clinic_id)}, {"$set": data}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Clinic not found")

    updated = await db.clinics.find_one({"_id": ObjectId(current_user.clinic_id)})
    updated["_id"] = str(updated["_id"])
    return updated


# --- Upload Logo to Cloudinary ---
@router.post("/upload-logo")
async def upload_logo(
    file: UploadFile = File(...),
    current_user: TokenData = Depends(get_current_clinic_user),
):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    # Max 2MB
    contents = await file.read()
    if len(contents) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size must be less than 2MB")

    try:
        result = cloudinary.uploader.upload(
            contents,
            folder="clinic_logos",
            public_id=f"clinic_{current_user.clinic_id}",
            overwrite=True,
            resource_type="image",
        )
        logo_url = result["secure_url"]
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to upload image: {str(e)}"
        )

    # Save to clinic doc
    db = get_db()
    await db.clinics.update_one(
        {"_id": ObjectId(current_user.clinic_id)}, {"$set": {"logo_url": logo_url}}
    )

    return {"logo_url": logo_url}


# --- Change Password ---
class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@router.post("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    current_user: TokenData = Depends(get_current_clinic_user),
):
    db = get_db()
    user = await db.users.find_one({"email": current_user.email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not verify_password(body.current_password, user["hashed_password"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    new_hashed = get_password_hash(body.new_password)
    await db.users.update_one(
        {"email": current_user.email}, {"$set": {"hashed_password": new_hashed}}
    )

    return {"message": "Password changed successfully"}


# --- Set Default Template ---
class SetDefaultTemplateRequest(BaseModel):
    template_id: str


@router.post("/default-template")
async def set_default_template(
    body: SetDefaultTemplateRequest,
    current_user: TokenData = Depends(get_current_clinic_user),
):
    db = get_db()

    # Verify template exists and is accessible by clinic
    template = await db.templates.find_one({"_id": ObjectId(body.template_id)})
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Template must be global or belong to the clinic
    if not template.get("is_global") and template.get("clinic_id") != current_user.clinic_id:
        raise HTTPException(status_code=403, detail="Template not accessible")

    await db.clinics.update_one(
        {"_id": ObjectId(current_user.clinic_id)},
        {"$set": {"default_template_id": body.template_id}},
    )

    return {"message": "Default template updated", "template_id": body.template_id}

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, UploadFile, File
from app.clinics.models import ClinicCreate, ClinicInDB, ClinicUpdate
from app.auth.dependencies import get_current_admin
from app.database import get_db
from bson import ObjectId
from app.auth.pass_utils import get_password_hash
from app.utils.email import send_email
from app.config import settings
from datetime import datetime, timedelta, time
from collections import defaultdict
import random
import string
import cloudinary
import cloudinary.uploader

# Configure Cloudinary
cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
)
router = APIRouter(prefix="/clinics", tags=["Clinics"])

@router.post("/", response_model=ClinicInDB, status_code=status.HTTP_201_CREATED)
async def create_clinic(clinic: ClinicCreate, background_tasks: BackgroundTasks, current_user = Depends(get_current_admin)):
    db = get_db()
    
    # Check if a user with this email already exists
    if clinic.email:
        existing_user = await db.users.find_one({"email": clinic.email})
        if existing_user:
            raise HTTPException(status_code=400, detail="User with this email already exists")

    clinic_dict = clinic.model_dump()
    clinic_db = ClinicInDB(**clinic_dict)
    
    result = await db.clinics.insert_one(clinic_db.model_dump(by_alias=True, exclude=["id"]))
    created_clinic = await db.clinics.find_one({"_id": result.inserted_id})
    
    if clinic.email:
        # Generate a random password if email is provided
        default_password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        hashed_password = get_password_hash(default_password)
        
        new_user = {
            "email": clinic.email,
            "username": clinic.email, # To satisfy any existing legacy index on username
            "role": "clinic_user",
            "clinic_id": str(result.inserted_id),
            "hashed_password": hashed_password,
            "is_active": True
        }
        await db.users.insert_one(new_user)
        
        email_subject = "Welcome to Medical Dashboard"
        email_body = f"Hello {clinic.name},\n\nYour account has been created successfully.\nYour login credentials are:\nEmail: {clinic.email}\nPassword: {default_password}\n\nPlease login and change your password.\n\nBest Regards,\nThe Team"
        
        background_tasks.add_task(send_email, clinic.email, email_subject, email_body)

    return created_clinic

@router.get("/")
async def list_clinics(current_user = Depends(get_current_admin)):
    db = get_db()
    clinics = await db.clinics.find().to_list(100)
    for clinic in clinics:
        clinic["_id"] = str(clinic["_id"])
    return clinics

@router.patch("/{clinic_id}", response_model=ClinicInDB)
async def update_clinic(clinic_id: str, clinic_update: ClinicUpdate, current_user = Depends(get_current_admin)):
    db = get_db()
    update_data = {k: v for k, v in clinic_update.model_dump().items() if v is not None}
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
        
    result = await db.clinics.update_one(
        {"_id": ObjectId(clinic_id)},
        {"$set": update_data}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Clinic not found or no changes made")
        
    updated = await db.clinics.find_one({"_id": ObjectId(clinic_id)})
    return updated

@router.get("/{clinic_id}/stats")
async def get_clinic_stats(clinic_id: str, current_user = Depends(get_current_admin)):
    db = get_db()
    
    # Check if clinic exists
    clinic = await db.clinics.find_one({"_id": ObjectId(clinic_id)})
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")

    # Time ranges
    now = datetime.utcnow()
    last_30_days = now - timedelta(days=30)
    
    # 1. Basic Stats
    total_patients = await db.patients.count_documents({"clinic_id": clinic_id})
    total_visits = await db.visits.count_documents({"clinic_id": clinic_id})
    
    # 2. Last Activity (Latest Visit)
    last_visit = await db.visits.find_one(
        {"clinic_id": clinic_id},
        sort=[("created_at", -1)]
    )
    last_use = last_visit["created_at"] if last_visit else clinic.get("created_at")
    
    # 3. Monthly Revenue Trend (Adapted from dashboard/routes.py)
    six_months_ago = now.replace(day=1) - timedelta(days=150)
    monthly_visits = await db.visits.find({
        "clinic_id": clinic_id,
        "created_at": {"$gte": six_months_ago}
    }).to_list(length=None)
    
    monthly_stats = defaultdict(float)
    for v in monthly_visits:
        month_key = v["created_at"].strftime("%Y-%m")
        monthly_stats[month_key] += v.get("fees", 0)
    
    monthly_revenue_list = [
        {"month": k, "revenue": v} 
        for k, v in sorted(monthly_stats.items())
    ]

    # 4. Patient Growth (Last 6 months)
    monthly_patients = defaultdict(int)
    patients = await db.patients.find({
        "clinic_id": clinic_id,
        "created_at": {"$gte": six_months_ago}
    }).to_list(length=None)
    
    for p in patients:
        month_key = p["created_at"].strftime("%Y-%m")
        monthly_patients[month_key] += 1
        
    monthly_patient_list = [
        {"month": k, "count": v}
        for k, v in sorted(monthly_patients.items())
    ]

    return {
        "summary": {
            "total_patients": total_patients,
            "total_visits": total_visits,
            "last_use": last_use,
            "is_active": clinic.get("is_active", True)
        },
        "charts": {
            "revenue": monthly_revenue_list,
            "patients": monthly_patient_list
        }
    }

@router.post("/{clinic_id}/upload-logo")
async def upload_clinic_logo(
    clinic_id: str,
    file: UploadFile = File(...),
    current_user = Depends(get_current_admin),
):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    contents = await file.read()
    try:
        result = cloudinary.uploader.upload(
            contents,
            folder="clinic_logos",
            public_id=f"clinic_{clinic_id}",
            overwrite=True,
            resource_type="image",
        )
        logo_url = result["secure_url"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload image: {str(e)}")

    db = get_db()
    await db.clinics.update_one(
        {"_id": ObjectId(clinic_id)}, 
        {"$set": {"logo_url": logo_url}}
    )

    return {"logo_url": logo_url}

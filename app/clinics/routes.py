from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from app.clinics.models import ClinicCreate, ClinicInDB, ClinicUpdate
from app.auth.dependencies import get_current_admin
from app.database import get_db
from bson import ObjectId
from app.auth.pass_utils import get_password_hash
from app.utils.email import send_email
import random
import string
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

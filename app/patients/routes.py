from fastapi import APIRouter, Depends, HTTPException, status, Query
from app.patients.models import PatientCreate, PatientInDB
from app.auth.dependencies import get_current_clinic_user
from app.auth.models import TokenData
from app.database import get_db
from app.utils.query_params import CommonQueryParams
from app.utils.pagination import paginate
from bson import ObjectId

router = APIRouter(prefix="/patients", tags=["Patients"])

@router.post("/", response_model=PatientInDB, status_code=status.HTTP_201_CREATED)
async def create_patient(patient: PatientCreate, current_user: TokenData = Depends(get_current_clinic_user)):
    db = get_db()
    # Check if patient exists
    existing = await db.patients.find_one({
        "phone": patient.phone, 
        "clinic_id": current_user.clinic_id
    })
    if existing:
        raise HTTPException(status_code=400, detail="Patient with this phone already exists")

    patient_dict = patient.model_dump()
    patient_db = PatientInDB(**patient_dict, clinic_id=current_user.clinic_id)
    
    result = await db.patients.insert_one(patient_db.model_dump(by_alias=True, exclude=["id"]))
    created_patient = await db.patients.find_one({"_id": result.inserted_id})
    created_patient["_id"] = str(created_patient["_id"])
    return created_patient

@router.get("/")
async def list_patients(
    params: CommonQueryParams = Depends(),
    current_user: TokenData = Depends(get_current_clinic_user)
):
    db = get_db()
    query = {"clinic_id": current_user.clinic_id}
    
    total = await db.patients.count_documents(query)
    
    cursor = db.patients.find(query).skip(params.skip).limit(params.limit)
    if params.sort_by:
        sort_order = -1 if params.sort_desc else 1
        cursor = cursor.sort(params.sort_by, sort_order)
        
    items = await cursor.to_list(length=params.limit)
    for item in items:
        item["_id"] = str(item["_id"])
        
    return paginate(items, total, params.page, params.limit)

@router.get("/search")
async def search_patients(
    phone: str = Query(..., min_length=3),
    current_user: TokenData = Depends(get_current_clinic_user)
):
    db = get_db()
    # Basic regex search
    query = {
        "clinic_id": current_user.clinic_id,
        "phone": {"$regex": phone, "$options": "i"}
    }
    items = await db.patients.find(query).to_list(length=20)
    for item in items:
        item["_id"] = str(item["_id"])
    return items

@router.get("/{id}")
async def get_patient(id: str, current_user: TokenData = Depends(get_current_clinic_user)):
    db = get_db()
    item = await db.patients.find_one({"_id": ObjectId(id), "clinic_id": current_user.clinic_id})
    if not item:
        raise HTTPException(status_code=404, detail="Patient not found")
    item["_id"] = str(item["_id"])
    return item

@router.get("/{id}/profile")
async def get_patient_profile(id: str, current_user: TokenData = Depends(get_current_clinic_user)):
    db = get_db()
    patient = await db.patients.find_one({"_id": ObjectId(id), "clinic_id": current_user.clinic_id})
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    patient["_id"] = str(patient["_id"])
    
    # Use embedded visits from patient document if available
    embedded_visits = patient.get("visits", [])
    
    if embedded_visits:
        # Reverse to get newest first
        visits = list(reversed(embedded_visits))
    else:
        # Fallback: fetch from visits collection for older patients that don't have embedded visits
        visits = await db.visits.find({
            "patient_id": id,
            "clinic_id": current_user.clinic_id
        }).sort("created_at", -1).to_list(500)
        for v in visits:
            v["_id"] = str(v["_id"])
    
    # Calculate total fees
    total_fees = sum(v.get("fees", 0) for v in visits)
    
    return {
        "patient": patient,
        "visits": visits,
        "total_fees": total_fees,
        "total_visits": len(visits),
    }


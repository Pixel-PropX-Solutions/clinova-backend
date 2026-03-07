from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from app.auth.models import PyObjectId

class ServiceItem(BaseModel):
    service_id: str
    service_name: str
    price: float

class VisitBase(BaseModel):
    patient_id: str
    doctor_notes: Optional[str] = None
    diagnosis: Optional[str] = None
    fees: float = 0.0
    dr_name: Optional[str] = None
    disease: Optional[str] = None
    specialization: Optional[str] = None
    payment_method: str = "Cash"
    visited_at: datetime = Field(default_factory=datetime.utcnow)
    medicines: Optional[List[str]] = []
    services_used: Optional[List[ServiceItem]] = []

class VisitCreate(VisitBase):
    pass

class VisitInDB(VisitBase):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    clinic_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

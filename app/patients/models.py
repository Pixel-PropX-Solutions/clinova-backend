from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from app.auth.models import PyObjectId

class VisitSummary(BaseModel):
    visit_id: str
    fees: float = 0.0
    dr_name: Optional[str] = None
    disease: Optional[str] = None
    specialization: Optional[str] = None
    payment_method: str = "Cash"
    visited_at: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class PatientBase(BaseModel):
    name: str
    phone: str
    gender: str
    age: int
    address: Optional[str] = None
    notes: Optional[str] = None

class PatientCreate(PatientBase):
    pass

class PatientInDB(PatientBase):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    clinic_id: str
    first_visit_date: datetime = Field(default_factory=datetime.utcnow)
    last_visit_date: datetime = Field(default_factory=datetime.utcnow)
    visit_count: int = 0
    visits: List[VisitSummary] = []

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

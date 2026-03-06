from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from app.auth.models import PyObjectId

class BillServiceItem(BaseModel):
    service_id: str
    service_name: str
    price: float
    quantity: int = 1

class BillBase(BaseModel):
    patient_id: str
    visit_id: str
    services: List[BillServiceItem]
    payment_mode: str = "cash"

class BillCreate(BillBase):
    pass

class BillInDB(BillBase):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    clinic_id: str
    total_amount: float
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

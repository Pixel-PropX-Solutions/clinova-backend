from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
from app.auth.models import PyObjectId


class ClinicBase(BaseModel):
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    plan: str = "basic"
    logo_url: Optional[str] = None
    default_template_id: Optional[str] = None
    default_doctor_name: Optional[str] = None
    default_doctor_fee: Optional[int] = 0


class ClinicCreate(ClinicBase):
    pass


class ClinicUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    is_active: Optional[bool] = None
    logo_url: Optional[str] = None
    default_template_id: Optional[str] = None
    default_doctor_name: Optional[str] = None
    default_doctor_fee: Optional[int] = 0



class ClinicSettingsUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    logo_url: Optional[str] = None
    default_template_id: Optional[str] = None
    default_doctor_name: Optional[str] = None
    default_doctor_fee: Optional[int] = 0


class ClinicInDB(ClinicBase):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

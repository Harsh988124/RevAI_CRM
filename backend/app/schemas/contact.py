from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

class ContactBase(BaseModel):
    first_name: str = Field(min_length=1,max_length=100)
    last_name: str = Field(min_length=1,max_length=100)
    email: EmailStr | None = None
    phone: str | None=Field(default=None,max_length=30)
    title: str | None=Field(default=None,max_length=150)
    company_id: int | None = Field(default=None,gt=0)

class ContactCreate(ContactBase):
    pass

class ContactUpdate(BaseModel):
    first_name: str | None = Field(default=None,min_length=1,max_length=100)
    last_name: str | None = Field(default=None,min_length=1,max_length=100)
    email: EmailStr | None=None
    phone: str|None=Field(default=None, max_length=30)
    title: str|None=Field(default=None, max_length=150)
    company_id: int | None=Field(default=None,gt=0)

class ContactResponse(ContactBase):
    id:int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ContactListResponse(BaseModel):
    items: list[ContactResponse]
    total: int
    limit: int
    offset: int



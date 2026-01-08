# app/schemas/error.py
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class ErrorPayload(BaseModel):
    source: Optional[str] = Field(None)
    function: Optional[str] = Field(None)
    message: Optional[str] = Field(None)
    messageCourt: Optional[str] = Field(None)
    referenceId: Optional[str] = Field(None)
    stackTrace: Optional[str] = Field(None)
    logCode: Optional[str] = Field(None)
    createdDate: Optional[datetime] = Field(None)

    # allow arbitrary fields if Salesforce adds more
    class Config:
        extra = "allow"
        orm_mode = True

# app/models/error_event.py
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from DataIngestion.app.models.base import Base

class ErrorEvent(Base):
    __tablename__ = "error_events"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(200), nullable=True)
    function = Column(String(200), nullable=True)
    message = Column(Text, nullable=True)
    message_court = Column(String(255), nullable=True)
    reference_id = Column(String(200), nullable=True)
    stack_trace = Column(Text, nullable=True)
    log_code = Column(String(100), nullable=True)
    created_date = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(50), nullable=False, server_default="processing")
    #raw_payload = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())



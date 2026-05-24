"""Good model: every JSONB column has a paired Pydantic schema + __schemas__ mapping."""
from datetime import datetime
from pydantic import BaseModel, Field
from sqlalchemy import Column, Text
from sqlalchemy.dialects.postgresql import JSONB

from app.db import Base


class TriageDataSchema(BaseModel):
    urgency: str = Field(pattern=r"^(EMERGENT|URGENT|ROUTINE|SELF-CARE)$")
    rationale: str
    captured_at: datetime
    chief_complaints: list[str]


class EncounterMetadataSchema(BaseModel):
    source_system: str
    ingested_at: datetime
    integration_version: str


class Encounter(Base):
    __tablename__ = "encounter"

    id = Column(Text, primary_key=True)
    patient_id = Column(Text, nullable=False)
    triage_data = Column(JSONB, nullable=False)
    encounter_metadata = Column(JSONB)

    __schemas__ = {
        "triage_data": TriageDataSchema,
        "encounter_metadata": EncounterMetadataSchema,
    }

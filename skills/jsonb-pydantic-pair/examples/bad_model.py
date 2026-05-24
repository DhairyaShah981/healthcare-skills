"""Bad model: JSONB columns with no Pydantic schemas. The linter should flag these."""
from sqlalchemy import Column, Text
from sqlalchemy.dialects.postgresql import JSONB

from app.db import Base


class Encounter(Base):
    __tablename__ = "encounter"

    id = Column(Text, primary_key=True)
    patient_id = Column(Text, nullable=False)
    triage_data = Column(JSONB, nullable=False)      # ← naked
    encounter_metadata = Column(JSONB)                # ← naked

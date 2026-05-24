"""Bad: queries against tenant-scoped tables with no client_id predicate."""

def list_observations(patient_id, db):
    # RLS-001: no client_id filter
    return db.query(Observation).filter_by(patient_id=patient_id).all()


def get_appointment(appointment_id, db):
    # RLS-001: session.get bypasses any filter
    return db.get(Appointment, appointment_id)


def search_patients(query_str, db):
    # RLS-001: filter on name only, no tenant
    return db.query(Patient).filter(Patient.last_name.ilike(f"%{query_str}%")).all()

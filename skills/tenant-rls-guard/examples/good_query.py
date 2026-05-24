"""Good: every multi-tenant query has an explicit client_id predicate."""

def list_observations(patient_id, client_id, db):
    return (
        db.query(Observation)
        .filter(Observation.client_id == client_id,
                Observation.patient_id == patient_id)
        .all()
    )


def get_appointment(appointment_id, client_id, db):
    return (
        db.query(Appointment)
        .filter(Appointment.client_id == client_id,
                Appointment.id == appointment_id)
        .one_or_none()
    )


def search_patients(query_str, client_id, db):
    return (
        db.query(Patient)
        .filter(Patient.client_id == client_id,
                Patient.last_name.ilike(f"%{query_str}%"))
        .all()
    )


def analytics_rollup(db):
    # tenant-rls-guard: bypass=analytics
    # Cross-tenant aggregate for org-wide dashboard; reviewed quarterly.
    return db.query(Patient.client_id, func.count(Patient.id)).group_by(Patient.client_id).all()

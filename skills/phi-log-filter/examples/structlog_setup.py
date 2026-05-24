"""Example structlog wiring with phi-log-filter installed."""
import structlog

from phi_log_filter import phi_processor

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        phi_processor(allowlist={
            "event", "level", "timestamp", "logger",
            "patient_id", "trace_id", "tenant_id", "request_id",
            "user_id", "encounter_id", "appointment_id",
        }),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
)

log = structlog.get_logger()

if __name__ == "__main__":
    # These calls will have their PHI scrubbed before hitting stdout:
    log.info(
        "patient_loaded",
        patient_id="P9981",
        patient_name="Maria Hernandez",
        dob="1962-04-11",
        phone="415-555-0173",
    )
    log.info(
        "intake_received",
        note="Patient John O'Connor (DOB 1978-11-30) reports headache",
    )

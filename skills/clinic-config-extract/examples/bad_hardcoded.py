"""Demonstrates each of CCE-001, CCE-002, CCE-003."""
import pytz


def get_timezone(clinic_id):
    # CCE-002: branch on a slug literal
    if clinic_id == "redding":
        return pytz.timezone("America/Los_Angeles")
    return pytz.UTC


def resolve_clinic(clinic_id):
    # CCE-003: default to a specific clinic
    return clinic_id or "redding"


# CCE-001: bare slug literal
FAX_NUMBERS = {"ent_sd": "+1-619-555-0142"}

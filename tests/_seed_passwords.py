"""Test-only seed passwords (R-05). Not used outside the test suite.

conftest.py exports these as AEGIS_SEED_PASSWORD_<USER> before the database is seeded,
so tests can log in without any password being hard-coded in application source.
"""
SEED_PASSWORDS = {
    "admin": "test-only-admin-pw-7c1e",
    "responder": "test-only-responder-pw-4b2a",
    "analyst": "test-only-analyst-pw-9d3f",
    "viewer": "test-only-viewer-pw-2e8c",
}

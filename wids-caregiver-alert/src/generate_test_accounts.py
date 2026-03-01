"""
generate_test_accounts.py
──────────────────────────
Run this ONCE locally to get the SQL INSERT statements for your three test accounts.
Then paste the output into Supabase → SQL Editor and execute.

Usage:
    python generate_test_accounts.py
"""

import hashlib, os

TEST_ACCOUNTS = [
    ("caregiver_test",  "caregiver_test@wids.test",  "WiDS@2025!", "Caregiver/Evacuee"),
    ("dispatcher_test", "dispatcher_test@wids.test", "WiDS@2025!", "Emergency Worker"),
    ("analyst_test",    "analyst_test@wids.test",    "WiDS@2025!", "Data Analyst"),
]

def hash_pw(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode(), bytes.fromhex(salt), 260_000
    ).hex()

print("-- Paste into Supabase SQL Editor:\n")
print("INSERT INTO public.users")
print("  (username, email, full_name, password_hash, password_salt, role)")
print("VALUES")

rows = []
for username, email, pw, role in TEST_ACCOUNTS:
    salt = os.urandom(32).hex()
    hsh  = hash_pw(pw, salt)
    full = username.replace("_", " ").title()
    rows.append(
        f"  ('{username}', '{email}', '{full}', '{hsh}', '{salt}', '{role}')"
    )

print(",\n".join(rows) + "\nON CONFLICT (username) DO NOTHING;\n")

print("-- Access codes reminder:")
print("--   dispatcher_test → DISPATCH-2025")
print("--   analyst_test    → ANALYST-WiDS9")
print("--   caregiver_test  → no code needed (or use EVAC-DEMO2025 to verify)")
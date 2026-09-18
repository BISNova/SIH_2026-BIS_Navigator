"""
Secure one-time admin account seeding.

This script creates an admin account using server-side environment
variables. It is intentionally NOT exposed as a public API endpoint.

Required environment variables:
    ADMIN_EMAIL
    ADMIN_PASSWORD

Optional:
    ADMIN_NAME

The script is safe to run repeatedly:
- If the admin email already belongs to an admin, no changes are made.
- If the email belongs to a non-admin user, the script refuses to
  change that user's role.
- If the email does not exist, a new active admin is created.
"""

import os

from dotenv import load_dotenv

from backend.database import supabase
from backend.auth.security import hash_password


load_dotenv()


def seed_admin() -> None:
    admin_email = os.getenv("ADMIN_EMAIL")
    admin_password = os.getenv("ADMIN_PASSWORD")
    admin_name = os.getenv("ADMIN_NAME", "BISNova Admin")

    if not admin_email:
        raise RuntimeError("ADMIN_EMAIL is not set")

    if not admin_password:
        raise RuntimeError("ADMIN_PASSWORD is not set")

    if len(admin_password) < 8:
        raise RuntimeError(
            "ADMIN_PASSWORD must be at least 8 characters long"
        )

    # Check whether this email already exists.
    existing = (
        supabase
        .table("users")
        .select("id,name,email,role,status")
        .eq("email", admin_email)
        .limit(1)
        .execute()
    )

    if existing.data:
        user = existing.data[0]

        if user["role"] == "admin":
            print(
                f"Admin account already exists for {user['email']}. "
                "No changes made."
            )
            return

        raise RuntimeError(
            f"User with email {admin_email} already exists with role "
            f"'{user['role']}'. Refusing to change the existing user's role."
        )

    # Hash the password before storing it.
    password_hash = hash_password(admin_password)

    result = (
        supabase
        .table("users")
        .insert(
            {
                "name": admin_name,
                "email": admin_email,
                "password_hash": password_hash,
                "role": "admin",
                "status": "active",
            }
        )
        .execute()
    )

    if not result.data:
        raise RuntimeError("Failed to create admin account")

    user = result.data[0]

    print("Admin account created successfully.")
    print(f"ID: {user['id']}")
    print(f"Email: {user['email']}")
    print(f"Role: {user['role']}")
    print(f"Status: {user['status']}")


if __name__ == "__main__":
    seed_admin()
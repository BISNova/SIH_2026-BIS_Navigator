from fastapi import APIRouter, HTTPException, status

from backend.database import supabase
from backend.auth.schemas import (
    RegisterRequest,
    RegisterResponse,
    LoginRequest,
    LoginResponse,
)
from backend.auth.security import (
    hash_password,
    verify_password,
    create_access_token,
)


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_user(request: RegisterRequest):
    # Admin registration is not allowed through public API
    if request.role not in {"general", "msme", "lab"}:
        raise HTTPException(
            status_code=400,
            detail="Invalid role. Allowed roles: general, msme, lab",
        )

    # Check whether email already exists
    existing = (
        supabase
        .table("users")
        .select("id")
        .eq("email", request.email)
        .limit(1)
        .execute()
    )

    if existing.data:
        raise HTTPException(
            status_code=409,
            detail="Email already registered",
        )

    # Lab accounts require admin approval
    user_status = "pending" if request.role == "lab" else "active"

    # Hash password before storing
    password_hash = hash_password(request.password)

    # Insert user
    result = (
        supabase
        .table("users")
        .insert(
            {
                "name": request.name,
                "email": request.email,
                "password_hash": password_hash,
                "role": request.role,
                "status": user_status,
            }
        )
        .execute()
    )

    if not result.data:
        raise HTTPException(
            status_code=500,
            detail="Failed to create user",
        )

    user = result.data[0]

    return RegisterResponse(
        id=str(user["id"]),
        name=user["name"],
        email=user["email"],
        role=user["role"],
        status=user["status"],
    )

@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
)
def login_user(request: LoginRequest):
    # Find user by email
    result = (
        supabase
        .table("users")
        .select(
            "id,name,email,password_hash,role,status"
        )
        .eq("email", request.email)
        .limit(1)
        .execute()
    )

    # Do not reveal whether the email exists
    if not result.data:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )

    user = result.data[0]

    # Verify password
    if not verify_password(
        request.password,
        user["password_hash"],
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )

    # Only active users can login
    if user["status"] != "active":
        raise HTTPException(
            status_code=403,
            detail=f"Account is {user['status']}",
        )

    # Create JWT
    access_token = create_access_token(
        user_id=str(user["id"]),
        role=user["role"],
    )

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=RegisterResponse(
            id=str(user["id"]),
            name=user["name"],
            email=user["email"],
            role=user["role"],
            status=user["status"],
        ),
    )
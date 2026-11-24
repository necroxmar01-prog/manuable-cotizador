import os
import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials


http_basic = HTTPBasic()


def require_admin(
    credentials: HTTPBasicCredentials = Depends(http_basic),
) -> str:
    """Valida las credenciales de acceso administrativo."""

    expected_username = os.getenv("ADMIN_USERNAME")
    expected_password = os.getenv("ADMIN_PASSWORD")

    if not expected_username or not expected_password:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="La autenticación administrativa no está configurada.",
        )

    username_is_valid = secrets.compare_digest(
        credentials.username.encode("utf-8"),
        expected_username.encode("utf-8"),
    )
    password_is_valid = secrets.compare_digest(
        credentials.password.encode("utf-8"),
        expected_password.encode("utf-8"),
    )

    if not (username_is_valid and password_is_valid):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales administrativas incorrectas.",
            headers={"WWW-Authenticate": "Basic"},
        )

    return credentials.username


import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from backend.dependencies.database import get_db
from backend.core.config import settings
from database.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )

        subject = payload.get("sub")
        if not isinstance(subject, str):
            raise credentials_error

        user_id = int(subject)
    except (jwt.InvalidTokenError, ValueError, TypeError):
        raise credentials_error from None

    user = db.get(User, user_id)

    if user is None or not user.is_active:
        raise credentials_error

    return user

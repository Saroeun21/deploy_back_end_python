import logging

import jwt
from fastapi import HTTPException

from app.core.config import settings

logger = logging.getLogger(__name__)

FIREBASE_SIGNING_KEYS_URL = (
    "https://www.googleapis.com/service_accounts/v1/jwk/"
    "securetoken@system.gserviceaccount.com"
)
FIREBASE_TOKEN_CLOCK_SKEW_SECONDS = 60


def verify_firebase_id_token(id_token: str) -> dict:
    project_id = settings.FIREBASE_PROJECT_ID
    if not project_id:
        raise HTTPException(
            status_code=503,
            detail="Google sign-in is not configured on the API server.",
        )

    try:
        signing_key = jwt.PyJWKClient(
            FIREBASE_SIGNING_KEYS_URL,
            timeout=5,
        ).get_signing_key_from_jwt(id_token)
        claims = jwt.decode(
            id_token,
            signing_key.key,
            algorithms=["RS256"],
            audience=project_id,
            issuer=f"https://securetoken.google.com/{project_id}",
            options={"require": ["exp", "iat", "sub", "aud", "iss"]},
            leeway=FIREBASE_TOKEN_CLOCK_SKEW_SECONDS,
        )
    except jwt.PyJWKClientConnectionError as error:
        raise HTTPException(
            status_code=502,
            detail="Could not reach Firebase to verify Google sign-in.",
        ) from error
    except jwt.PyJWTError as error:
        logger.warning(
            "Firebase ID token verification rejected (%s)",
            type(error).__name__,
        )
        if isinstance(error, jwt.ExpiredSignatureError):
            detail = "Google sign-in expired. Please try Google sign-in again."
        elif isinstance(error, jwt.ImmatureSignatureError):
            detail = (
                "Google sign-in token is not valid yet. Check that the API server "
                "clock is synchronized, then try again."
            )
        elif isinstance(error, jwt.DecodeError):
            detail = (
                "Expected a valid Firebase ID token. Please try Google sign-in again."
            )
        elif isinstance(error, jwt.InvalidAudienceError):
            detail = "Google sign-in project does not match the API configuration."
        elif isinstance(error, jwt.InvalidIssuerError):
            detail = "Google sign-in issuer does not match the API configuration."
        elif isinstance(error, jwt.InvalidSignatureError):
            detail = "Google sign-in token signature could not be verified."
        else:
            detail = "The Firebase sign-in token is invalid. Please try again."
        raise HTTPException(
            status_code=401,
            detail=detail,
        ) from error

    if claims.get("email_verified") is not True:
        raise HTTPException(
            status_code=401,
            detail="Google sign-in requires a verified email address.",
        )
    if not isinstance(claims.get("email"), str) or not claims["email"].strip():
        raise HTTPException(
            status_code=401,
            detail="The Firebase sign-in token does not include an email address.",
        )

    return claims

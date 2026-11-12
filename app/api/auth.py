import base64
import httpx
import secrets
import jwt
from jwt import PyJWKClient
from urllib.parse import urlencode
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse
from app.core.config import settings   # add cognito URI from Terraform to settings object
from app.core.database import get_db
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
from app import models
from app.schemas.invite_schema import InvitationCreate

router = APIRouter()

# ───────── HELPERS (plain functions, called by routes) ─────────
# The issuer — note this is the cognito-idp domain, NOT your hosted-UI domain
ISSUER   = f"https://cognito-idp.{settings.cognito_region}.amazonaws.com/{settings.cognito_user_pool_id}"
JWKS_URL = f"{ISSUER}/.well-known/jwks.json"

# Created once; it fetches and caches Cognito's public keys internally
jwks_client = PyJWKClient(JWKS_URL)
def get_token_claims(request: Request) -> dict:
    # 1. Get the token the browser is carrying (the httpOnly cookie)
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # 2. + 3. Fetch the right public key (by the token's kid) and verify the signature
    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=ISSUER,
            options={"verify_aud": False},   # Cognito access tokens carry no 'aud'
        )
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

    # 4. The claims the library can't know your rules for
    if claims.get("token_use") != "access":
        raise HTTPException(status_code=401, detail="Wrong token type")
    if claims.get("client_id") != settings.cognito_client_id:
        raise HTTPException(status_code=401, detail="Wrong client")

    return claims

def get_current_user(
    claims: dict = Depends(get_token_claims),
    db: Session = Depends(get_db),
) -> models.User:
    user = db.query(models.User).filter_by(cognito_sub=claims["sub"]).first()
    if user is None:
        raise HTTPException(403, "User not onboarded")
    return user

def require_role(*allowed_roles: str):
    def checker(user: models.User = Depends(get_current_user)) -> models.User:
        if user.role not in allowed_roles:
            raise HTTPException(403, "Insufficient permissions")
        return user
    return checker

def onboard_user(db, sub, email, request) -> models.User:
    token = request.cookies.get("invite_token")
    if not token:
        raise HTTPException(403, "No invitation — contact your administrator")

    invite = db.query(models.Invitation).filter_by(token=token).first()
    if invite is None or invite.status != "pending":
        raise HTTPException(403, "Invitation invalid or already used")
    if invite.expires_at < datetime.now(timezone.utc):
        raise HTTPException(403, "Invitation expired")
    if invite.email.lower() != email.lower():
        raise HTTPException(403, "This invitation is for a different email")

    user = models.User(cognito_sub=sub, email=email,
                       tenant_id=invite.tenant_id, role=invite.role)
    db.add(user)
    invite.status = "accepted"
    invite.accepted_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)
    return user


#  ───────── ROUTES (the URLs) ─────────

@router.get("/auth/login")
def login():
    state = secrets.token_urlsafe(32)

    params = {
        "client_id":     settings.cognito_client_id,
        "response_type": "code",
        "scope":         "openid email profile",
        "redirect_uri":  settings.cognito_redirect_uri,   # http://localhost:8000/auth/callback
        "state":         state,
    }

    authorize_url = (
        f"https://{settings.cognito_domain}.auth.us-east-1.amazoncognito.com"
        f"/oauth2/authorize?{urlencode(params)}"
    )
    print(authorize_url)
    response = RedirectResponse(authorize_url, status_code=307)
    response.set_cookie("oauth_state", state, httponly=True, max_age=300, samesite="lax")
    return response

@router.get("/auth/callback")
def callback(request: Request, code: str, state: str, db: Session = Depends(get_db)):
    # 1. CSRF check — the state in the URL must match the cookie set at /auth/login
    expected = request.cookies.get("oauth_state")
    if not expected or state != expected:
        raise HTTPException(status_code=400, detail="Invalid state")

    # 2. Trade the code for tokens (backend -> Cognito, no browser)
    token_url = (
        f"https://{settings.cognito_domain}.auth.{settings.cognito_region}"
        f".amazoncognito.com/oauth2/token"
    )

    basic = base64.b64encode(
        f"{settings.cognito_client_id}:{settings.cognito_client_secret}".encode()
    ).decode()

    resp = httpx.post(
        token_url,
        data={
            "grant_type":   "authorization_code",
            "client_id":    settings.cognito_client_id,
            "code":         code,
            "redirect_uri": settings.cognito_redirect_uri,
        },
        headers={
            "Content-Type":  "application/x-www-form-urlencoded",
            "Authorization": f"Basic {basic}",
        },
    )
    if resp.status_code != 200:
        raise HTTPException(status_code=400, detail=f"Token exchange failed: {resp.text}")

    tokens = resp.json()   

    # These tokens came straight from Cognito over TLS, so reading them is safe here.
    claims = jwt.decode(tokens["id_token"], options={"verify_signature": False})
    sub, email = claims["sub"], claims["email"]
    print("LOGIN SUB:", sub)
    user = db.query(models.User).filter_by(cognito_sub=sub).first()
    if user is None:
        user = onboard_user(db, sub, email, request)

    response = RedirectResponse("/", status_code=307)
    response.set_cookie("access_token",  tokens["access_token"],
                        httponly=True, secure=False, samesite="lax", max_age=tokens["expires_in"])
    response.set_cookie("id_token",      tokens["id_token"],
                        httponly=True, secure=False, samesite="lax", max_age=tokens["expires_in"])
    response.set_cookie("refresh_token", tokens["refresh_token"],
                        httponly=True, secure=False, samesite="lax", max_age=30*24*3600)
    response.delete_cookie("oauth_state")
    response.delete_cookie("invite_token")
    return response


@router.get("/auth/me")
def me(claims: dict = Depends(get_token_claims)):
    return {"sub": claims["sub"], "username": claims.get("username"), "scope": claims.get("scope")}

# catch the invite link and stash the token
@router.get("/auth/invite")
def invite(token: str):
    response = RedirectResponse("/auth/login", status_code=307)
    response.set_cookie("invite_token", token, httponly=True, max_age=600, samesite="lax")
    return response

@router.post("/invitations")
def create_invitation(
    body: InvitationCreate,
    admin: models.User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    if body.role not in ("admin", "member"):
        raise HTTPException(400, "Invalid role")

    invite = models.Invitation(
        token=secrets.token_urlsafe(32),
        email=body.email,
        tenant_id=admin.tenant_id,        # ← THE line. Forced to the admin's own tenant.
        role=body.role,
        status="pending",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        created_by=admin.id,
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)
    return {"invite_link": f"http://localhost:8000/auth/invite?token={invite.token}"}
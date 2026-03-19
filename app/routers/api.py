import hashlib
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session

from ..models import SP500Constituent, SP500Meta, APIToken
from ..utils.db import get_db

router = APIRouter()


def hash_token(token: str) -> str:
    """Hash token for comparison."""
    return hashlib.sha256(token.encode()).hexdigest()


def verify_api_token(token: str, db: Session) -> Optional[APIToken]:
    """Verify API token and return the token record if valid."""
    if not token:
        return None
    
    # Remove "Bearer " prefix if present
    if token.startswith("Bearer "):
        token = token[7:]
    
    token_hash = hash_token(token)
    
    api_token = db.query(APIToken).filter(
        APIToken.token_hash == token_hash,
        APIToken.revoked == False
    ).first()
    
    return api_token


def check_user_subscription(user_id: int, db: Session) -> bool:
    """Check if user has an active subscription."""
    from ..models import User
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False
    return user.subscription_status == "active"


@router.get("/sp500/{target_date}")
def get_sp500_constituents(
    target_date: date,
    db: Session = Depends(get_db),
    authorization: str = Header(None)
):
    """Get S&P 500 constituents for a specific date.
    
    Requires valid API token in Authorization header.
    Format: Authorization: Bearer <your-api-token>
    """
    # Validate token
    if not authorization:
        raise HTTPException(status_code=401, detail="未提供认证令牌", headers={"WWW-Authenticate": "Bearer"})
    
    api_token = verify_api_token(authorization, db)
    if not api_token:
        raise HTTPException(status_code=401, detail="无效的API令牌", headers={"WWW-Authenticate": "Bearer"})
    
    # Check subscription status
    if not check_user_subscription(api_token.user_id, db):
        raise HTTPException(
            status_code=403, 
            detail="订阅已过期，请续订后继续使用",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Query constituents for the specified date
    constituents = db.query(SP500Constituent).filter(
        SP500Constituent.effective_from <= target_date,
        (SP500Constituent.effective_to.is_(None)) | (SP500Constituent.effective_to > target_date)
    ).all()
    
    # Query meta info
    meta_info = db.query(SP500Meta).all()
    meta_dict = {item.key: item.value for item in meta_info}
    
    # Format response
    result = {
        "date": target_date.isoformat(),
        "constituents": [
            {
                "code": c.code,
                "company_name": c.company_name,
                "sector": c.sector,
                "industry": c.industry
            }
            for c in constituents
        ],
        "meta": meta_dict
    }
    
    return result


@router.get("/meta")
def get_meta_info(db: Session = Depends(get_db)):
    """Get metadata (no auth required)."""
    meta_info = db.query(SP500Meta).all()
    return {item.key: item.value for item in meta_info}

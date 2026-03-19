import secrets
import hashlib
from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from ..models import User, APIToken
from ..utils.db import get_db
from .auth import require_current_user

router = APIRouter()


def hash_token(token: str) -> str:
    """Hash token for storage."""
    return hashlib.sha256(token.encode()).hexdigest()


@router.get("", response_class=HTMLResponse)
def tokens_page(request: Request, user: User = Depends(require_current_user), db: Session = Depends(get_db)):
    """Display user's API tokens."""
    tokens = db.query(APIToken).filter(
        APIToken.user_id == user.id,
        APIToken.revoked == False
    ).all()
    
    templates = request.app.state.templates
    return templates.TemplateResponse(
        "tokens.html", 
        {
            "request": request,
            "tokens": tokens,
            "user": user
        }
    )


@router.post("/create")
def create_token(
    name: str = Form(...),
    user: User = Depends(require_current_user),
    db: Session = Depends(get_db)
):
    """Create a new API token."""
    token_plain = APIToken.generate_token_plain()
    token_hash = hash_token(token_plain)
    
    token = APIToken(
        user_id=user.id,
        name=name,
        token_hash=token_hash
    )
    db.add(token)
    db.commit()
    
    return {"token": token_plain, "name": name}


@router.post("/delete")
def delete_token(
    token_id: int = Form(...),
    user: User = Depends(require_current_user),
    db: Session = Depends(get_db)
):
    """Revoke (delete) an API token."""
    token = db.query(APIToken).filter(
        APIToken.id == token_id,
        APIToken.user_id == user.id
    ).first()
    
    if not token:
        raise HTTPException(status_code=404, detail="令牌不存在")
    
    token.revoked = True
    db.commit()
    
    return {"message": "令牌已删除"}


@router.post("/copy")
def copy_token(
    token_id: int = Form(...),
    new_name: str = Form(...),
    user: User = Depends(require_current_user),
    db: Session = Depends(get_db)
):
    """Duplicate an existing API token."""
    original_token = db.query(APIToken).filter(
        APIToken.id == token_id,
        APIToken.user_id == user.id,
        APIToken.revoked == False
    ).first()
    
    if not original_token:
        raise HTTPException(status_code=404, detail="令牌不存在")
    
    token_plain = APIToken.generate_token_plain()
    token_hash = hash_token(token_plain)
    
    new_token = APIToken(
        user_id=user.id,
        name=new_name,
        token_hash=token_hash
    )
    db.add(new_token)
    db.commit()
    
    return {"token": token_plain, "name": new_name}
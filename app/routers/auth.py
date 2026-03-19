import os
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from datetime import datetime, timedelta
import secrets
from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional
from collections import defaultdict
import time

from ..models import User, EmailLoginCode
from ..utils.db import get_db

router = APIRouter()

# Email configuration
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", "noreply@example.com")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

SECRET_KEY = os.getenv("SECRET_KEY", "")
if not SECRET_KEY:
    SECRET_KEY = "dev-secret-key-change-in-production"
    print("[WARNING] Using default SECRET_KEY. Set SECRET_KEY environment variable in production!")

SESSION_COOKIE_NAME = "session"

# Rate limiting for verify-code (in-memory, per email)
# Structure: {email: [(timestamp, failed_attempts), ...]}
_verify_code_attempts: dict = defaultdict(list)
VERIFY_CODE_MAX_ATTEMPTS = 5
VERIFY_CODE_LOCKOUT_SECONDS = 300  # 5 minutes

# Session management using itsdangerous
from itsdangerous import URLSafeTimedSerializer
session_serializer = URLSafeTimedSerializer(SECRET_KEY)


def create_session(user_id: int, email: str) -> str:
    """Create a signed session token."""
    data = {"user_id": user_id, "email": email}
    return session_serializer.dumps(data)


def verify_session(token: str, max_age: int = 86400) -> Optional[dict]:
    """Verify session token and return user data."""
    try:
        data = session_serializer.loads(token, max_age=max_age)
        return data
    except Exception:
        return None


def send_verification_email(email: str, code: str) -> bool:
    """Send verification code via email. Returns True if successful."""
    # Check SMTP configuration
    if not SMTP_HOST or not SMTP_USER or not SMTP_PASS:
        print(f"[ERROR] SMTP not configured. Set SMTP_HOST, SMTP_USER, SMTP_PASS in .env")
        print(f"[INFO] Would send to {email}: {code}")
        return False
    if not FROM_EMAIL or '@' not in FROM_EMAIL:
        print(f"[ERROR] FROM_EMAIL not configured properly: {FROM_EMAIL}")
        print(f"[INFO] Would send to {email}: {code}")
        return False
    
    print(f"[INFO] Sending email to {email} from {FROM_EMAIL}")
    
    try:
        message = MIMEMultipart("alternative")
        message["Subject"] = "SP500 登录验证码"
        message["From"] = FROM_EMAIL
        message["To"] = email
        
        text_content = f"""您的登录验证码是: {code}

验证码有效期为 5 分钟。

如果不是您本人操作，请忽略此邮件。"""
        
        html_content = f"""<html>
<body style="font-family: Arial, sans-serif; padding: 20px;">
<h2>SP500 登录验证码</h2>
<p>您的登录验证码是: <strong style="font-size: 24px; letter-spacing: 2px;">{code}</strong></p>
<p style="color: #666;">验证码有效期为 5 分钟。</p>
<p style="color: #999; font-size: 12px;">如果不是您本人操作，请忽略此邮件。</p>
</body>
</html>"""
        
        message.attach(MIMEText(text_content, "plain"))
        message.attach(MIMEText(html_content, "html"))
        
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context) as server:
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(FROM_EMAIL, email, message.as_string())
        
        return True
    except Exception as e:
        print(f"[ERROR] Failed to send email: {e}")
        return False


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    templates = request.app.state.templates
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/send-code")
def send_login_code(
    email: str = Form(...),
    db: Session = Depends(get_db)
):
    # 检查1分钟内是否已发送（防止高频点击）
    recent_sent = db.query(EmailLoginCode).filter(
        EmailLoginCode.email == email,
        EmailLoginCode.used == False,
        EmailLoginCode.created_at >= datetime.utcnow() - timedelta(minutes=1)
    ).first()
    
    if recent_sent:
        return {"message": "1分钟内只能发送一次验证码，请稍后再试"}
    
    # 删除5分钟前的过期验证码
    db.query(EmailLoginCode).filter(
        EmailLoginCode.email == email,
        EmailLoginCode.used == False,
        EmailLoginCode.created_at < datetime.utcnow() - timedelta(minutes=5)
    ).delete(synchronize_session='fetch')
    
    code = ''.join(secrets.choice('0123456789') for _ in range(6))
    login_code = EmailLoginCode(
        email=email,
        code=code
    )
    db.add(login_code)
    db.commit()
    
    send_verification_email(email, code)
    
    return {"message": "验证码已发送，请注意查收"}


@router.post("/verify-code")
def verify_login_code(
    email: str = Form(...),
    code: str = Form(...),
    db: Session = Depends(get_db)
):
    # Check rate limiting
    current_time = time.time()
    attempts = _verify_code_attempts[email]

    # Clean up old attempts (older than lockout period)
    attempts[:] = [(ts, count) for ts, count in attempts if current_time - ts < VERIFY_CODE_LOCKOUT_SECONDS]

    # Check if locked out
    total_failed = sum(count for ts, count in attempts)
    if total_failed >= VERIFY_CODE_MAX_ATTEMPTS:
        raise HTTPException(status_code=429, detail="验证次数过多，请5分钟后再试")

    # 查找未使用且在有效期内的验证码
    login_code = db.query(EmailLoginCode).filter(
        EmailLoginCode.email == email,
        EmailLoginCode.used == False,
        EmailLoginCode.created_at >= datetime.utcnow() - timedelta(minutes=5)
    ).first()

    if not login_code or not secrets.compare_digest(login_code.code, code):
        # Record failed attempt
        attempts.append((current_time, 1))
        raise HTTPException(status_code=400, detail="验证码无效或已过期")

    # Clear failed attempts on success
    _verify_code_attempts[email] = []

    # 标记验证码为已使用
    login_code.used = True
    db.commit()
    
    # 检查用户是否存在，不存在则自动注册
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(email=email)
        db.add(user)
        db.commit()
    
    # 创建会话
    session_token = create_session(user.id, user.email)
    
    response = RedirectResponse(url="/dashboard", status_code=302)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_token,
        httponly=True,
        samesite="lax",
        max_age=86400,  # 24 hours
        secure=False  # Set to True in production with HTTPS
    )
    return response


@router.post("/logout")
def logout():
    """Clear session and redirect to login."""
    response = RedirectResponse(url="/auth/login", status_code=302)
    response.delete_cookie(key=SESSION_COOKIE_NAME)
    return response


# Dependency to get current user from session
def get_current_user(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    """Get current logged-in user from session cookie."""
    session_token = request.cookies.get(SESSION_COOKIE_NAME)
    if not session_token:
        return None
    
    session_data = verify_session(session_token)
    if not session_data:
        return None
    
    user = db.query(User).filter(User.id == session_data.get("user_id")).first()
    return user


def require_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Require current user - raises 401 if not logged in."""
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="未登录")
    return user
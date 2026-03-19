import os
import stripe
import json
import hmac
import hashlib
from fastapi import APIRouter, Depends, HTTPException, Request, Form, Header
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from ..models import User
from ..utils.db import get_db
from .auth import require_current_user

router = APIRouter()

# Stripe configuration
stripe.api_key = os.getenv("STRIPE_API_KEY")
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")


@router.get("/subscribe", response_class=HTMLResponse)
def subscribe_page(request: Request, user: User = Depends(require_current_user)):
    """Subscription page - requires login."""
    templates = request.app.state.templates
    return templates.TemplateResponse("subscribe.html", {"request": request, "user": user})


@router.post("/create-checkout-session")
def create_checkout_session(
    user: User = Depends(require_current_user),
    db: Session = Depends(get_db)
):
    """Create Stripe checkout session for subscription."""
    # Ensure user has stripe customer ID
    if not user.stripe_customer_id:
        customer = stripe.Customer.create(
            email=user.email
        )
        user.stripe_customer_id = customer.id
        db.commit()
    
    # Create checkout session
    checkout_session = stripe.checkout.Session.create(
        customer=user.stripe_customer_id,
        payment_method_types=["card"],
        line_items=[
            {
                "price": STRIPE_PRICE_ID,
                "quantity": 1,
            },
        ],
        mode="subscription",
        success_url=f"{BASE_URL}/billing/success",
        cancel_url=f"{BASE_URL}/billing/cancel",
    )
    
    return {"url": checkout_session.url}


@router.get("/success", response_class=HTMLResponse)
def success_page(request: Request):
    """Payment success page."""
    templates = request.app.state.templates
    return templates.TemplateResponse("success.html", {"request": request})


@router.get("/cancel", response_class=HTMLResponse)
def cancel_page(request: Request):
    """Payment canceled page."""
    templates = request.app.state.templates
    return templates.TemplateResponse("cancel.html", {"request": request})


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db),
    stripe_signature: str = Header(None)
):
    """Handle Stripe webhook events."""
    payload = await request.body()
    
    # Verify webhook signature if secret is configured
    if STRIPE_WEBHOOK_SECRET and stripe_signature:
        try:
            event = stripe.Webhook.construct_event(
                payload, stripe_signature, STRIPE_WEBHOOK_SECRET
            )
        except ValueError:
            return JSONResponse(status_code=400, content={"error": "Invalid payload"})
        except stripe.error.SignatureVerificationError:
            return JSONResponse(status_code=400, content={"error": "Invalid signature"})
    else:
        # For testing without signature verification
        event = json.loads(payload)
    
    # Handle the event
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        await handle_checkout_completed(session, db)
    
    elif event["type"] == "customer.subscription.updated":
        subscription = event["data"]["object"]
        await handle_subscription_updated(subscription, db)
    
    elif event["type"] == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        await handle_subscription_deleted(subscription, db)
    
    elif event["type"] == "invoice.payment_failed":
        invoice = event["data"]["object"]
        await handle_payment_failed(invoice, db)
    
    return {"status": "success"}


async def handle_checkout_completed(session: dict, db: Session):
    """Handle successful checkout."""
    customer_id = session.get("customer")
    subscription_id = session.get("subscription")
    
    user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
    if user:
        user.subscription_status = "active"
        db.commit()
        print(f"[STRIPE] User {user.email} subscription activated: {subscription_id}")


async def handle_subscription_updated(subscription: dict, db: Session):
    """Handle subscription updates."""
    customer_id = subscription.get("customer")
    status = subscription.get("status")
    
    user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
    if user:
        user.subscription_status = status
        db.commit()
        print(f"[STRIPE] User {user.email} subscription updated: {status}")


async def handle_subscription_deleted(subscription: dict, db: Session):
    """Handle subscription cancellation."""
    customer_id = subscription.get("customer")
    
    user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
    if user:
        user.subscription_status = "cancelled"
        db.commit()
        print(f"[STRIPE] User {user.email} subscription cancelled")


async def handle_payment_failed(invoice: dict, db: Session):
    """Handle failed payment."""
    customer_id = invoice.get("customer")
    
    user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
    if user:
        user.subscription_status = "payment_failed"
        db.commit()
        print(f"[STRIPE] Payment failed for user {user.email}")
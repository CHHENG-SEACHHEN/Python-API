from pydantic import BaseModel, EmailStr
from typing import List

# --- Auth Schemas ---
class UserSignup(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserSignin(BaseModel):
    username: str
    password: str
    agreed: bool = False

# --- Checkout Schemas ---
class CartItem(BaseModel):
    book_id: int
    quantity: int

class CheckoutRequest(BaseModel):
    user_id: int
    items: List[CartItem]
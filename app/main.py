from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import mysql.connector

from database import get_db
from schemas import UserSignup, UserSignin, CheckoutRequest
from security import hash_password, verify_password, create_access_token

app = FastAPI(title="Mini Book Shop API")
 
# 1. Enable CORS so your frontend (e.g., localhost:5500 or localhost:3000) can talk to this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace "*" with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Book Search & Catalog Endpoint
@app.get("/api/books")
def search_books(
    q: str = Query(default="", description="Search by title or author"),
    db=Depends(get_db)
):
    cursor = db.cursor(dictionary=True)
    if q:
        search_term = f"%{q}%"
        sql = "SELECT id, title, author, price, stock FROM books WHERE title LIKE %s OR author LIKE %s"
        cursor.execute(sql, (search_term, search_term))
    else:
        cursor.execute("SELECT id, title, author, price, stock FROM books")
    
    books = cursor.fetchall()
    cursor.close()
    return {"books": books}

# 3. Signup Endpoint
@app.post("/api/signup", status_code=201)
def signup(user: UserSignup, db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    
    # Check if email already exists
    cursor.execute("SELECT id FROM users WHERE email = %s", (user.email,))
    if cursor.fetchone():
        cursor.close()
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_pw = hash_password(user.password)
    sql = "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)"
    cursor.execute(sql, (user.username, user.email, hashed_pw))
    db.commit()
    
    new_user_id = cursor.lastrowid
    cursor.close()
    return {"message": "Account created successfully", "user_id": new_user_id}

# 4. Signin Endpoint
@app.post("/api/signin")
def signin(credentials: UserSignin, db=Depends(get_db)):
    if not credentials.agreed:
        raise HTTPException(status_code=400, detail="Please agree to the Terms and conditions.")

    cursor = db.cursor(dictionary=True)
    cursor.execute(
        "SELECT user_id, user_name, email, password FROM users WHERE user_name = %s",
        (credentials.username,)
    )
    user = cursor.fetchone()
    cursor.close()

    if not user or credentials.password != user["password"]:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_access_token({"sub": str(user["user_id"]), "email": user["email"]})
    return {
        "message": "Login successful!",
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "user_id": user["user_id"],
            "user_name": user["user_name"],
            "email": user["email"]
        }
    }

# 5. Checkout & Price Calculation Endpoint (Transactional)
@app.post("/api/checkout")
def checkout(order: CheckoutRequest, db=Depends(get_db)):
    if not order.items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    cursor = db.cursor(dictionary=True)
    try:
        # Start transaction so stock deduction and order creation succeed or fail together
        db.start_transaction()
        total_price = 0.0
        verified_items = []

        # Verify stock and fetch true prices from MySQL (never trust frontend prices!)
        for item in order.items:
            cursor.execute("SELECT id, title, price, stock FROM books WHERE id = %s FOR UPDATE", (item.book_id,))
            book = cursor.fetchone()

            if not book:
                raise HTTPException(status_code=404, detail=f"Book ID {item.book_id} not found")
            if book["stock"] < item.quantity:
                raise HTTPException(status_code=400, detail=f"Not enough stock for '{book['title']}'")

            item_total = float(book["price"]) * item.quantity
            total_price += item_total
            verified_items.append((book["id"], item.quantity, float(book["price"])))

        # Create the main order record
        cursor.execute(
            "INSERT INTO orders (user_id, total_price) VALUES (%s, %s)",
            (order.user_id, total_price)
        )
        order_id = cursor.lastrowid

        # Insert order items and deduct stock
        for book_id, qty, price in verified_items:
            cursor.execute(
                "INSERT INTO order_items (order_id, book_id, quantity, price_at_purchase) VALUES (%s, %s, %s, %s)",
                (order_id, book_id, qty, price)
            )
            cursor.execute(
                "UPDATE books SET stock = stock - %s WHERE id = %s",
                (qty, book_id)
            )

        db.commit()
        return {
            "message": "Checkout successful",
            "order_id": order_id,
            "total_price": round(total_price, 2)
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
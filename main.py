from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import mysql.connector

BASE_DIR = Path(__file__).parent

app = FastAPI()

# Enable CORS for local development requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files and set up templates directory (absolute paths,
# so it works no matter which folder you run the command from)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "New-template")


def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Callme099",
        database="python_sql"
    )


# Pydantic models for request body validation
class SignInRequest(BaseModel):
    username: str
    password: str
    agreed: bool


class SignUpRequest(BaseModel):
    username: str
    email: str
    password: str
    agreed: bool


# --- HTML Page Routes ---
@app.get("/")
def home(request: Request):
    return templates.TemplateResponse(request, "new home.html", {})


@app.get("/about")
def about(request: Request):
    return templates.TemplateResponse(request, "new about.html", {})


@app.get("/sale")
def sale(request: Request):
    return templates.TemplateResponse(request, "new sale.html", {})


@app.get("/contact")
def contact(request: Request):
    return templates.TemplateResponse(request, "new contact.html", {})


@app.get("/checkout")
def checkout(request: Request):
    return templates.TemplateResponse(request, "new checkout.html", {})


@app.get("/login")
def login(request: Request):
    return templates.TemplateResponse(request, "signin.html", {})


@app.get("/signup_page")
def signup_page(request: Request):
    return templates.TemplateResponse(request, "signup.html", {})


# --- API Sign In Endpoint ---
@app.post("/signin")
def signin(data: SignInRequest):
    if not data.agreed:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "You must agree to the terms and conditions."}
        )

    db = get_db()
    cursor = db.cursor(dictionary=True)
    try:
        query = "SELECT * FROM vw_users WHERE (user_name = %s OR email = %s) AND password = %s"
        cursor.execute(query, (data.username, data.username, data.password))
        user = cursor.fetchone()
    finally:
        cursor.close()
        db.close()

    if user:
        role = str(user.get("type_name", "")).lower()
        if "admin" in role:
            redirect_url = "/admin_dashboard"
        elif "cashier" in role:
            redirect_url = "/cashier_dashboard"
        else:
            redirect_url = "/user_dashboard"

        return {
            "status": "success",
            "message": f"Welcome back, {user.get('full_name') or user.get('user_name')}!",
            "redirect": redirect_url
        }

    return JSONResponse(
        status_code=401,
        content={"status": "error", "message": "Invalid username/email or password."}
    )


# --- API Sign Up Endpoint ---
@app.post("/signup")
def signup(data: SignUpRequest):
    if not data.agreed:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "You must agree to the terms."}
        )

    if not data.username or not data.email or not data.password:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "All fields are required."}
        )

    db = get_db()
    cursor = db.cursor(dictionary=True)

    try:
        # Find 'customer' user_type_id by default
        cursor.execute("SELECT user_type_id FROM user_types WHERE type_name = 'customer'")
        type_result = cursor.fetchone()

        if not type_result:
            return JSONResponse(
                status_code=500,
                content={"status": "error", "message": "Default 'customer' user type not found in database."}
            )

        customer_type_id = type_result["user_type_id"]

        insert_query = """
            INSERT INTO users (user_type_id, user_name, email, password, create_date, status)
            VALUES (%s, %s, %s, %s, NOW(), 1)
        """
        cursor.execute(insert_query, (customer_type_id, data.username, data.email, data.password))
        db.commit()

        return {
            "status": "success",
            "message": "Account created successfully!",
            "redirect": "/login"
        }

    except mysql.connector.Error as err:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": f"Database error: {err.msg}"}
        )
    finally:
        cursor.close()
        db.close()


# --- Dashboard Routes ---
@app.get("/admin_dashboard")
def admin_dashboard(request: Request):
    return templates.TemplateResponse(request, "admin.html", {})


@app.get("/cashier_dashboard")
def cashier_dashboard(request: Request):
    return templates.TemplateResponse(request, "cashier.html", {})


@app.get("/user_dashboard")
def user_dashboard(request: Request):
    return templates.TemplateResponse(request, "new home.html", {})


if __name__ == "__main__":
    import threading
    import webbrowser
    import uvicorn

    # Open the browser shortly after the server starts
    threading.Timer(1.5, lambda: webbrowser.open("http://127.0.0.1:8000")).start()
    uvicorn.run("main:app", host="127.0.0.1", port=8000)

from flask import Flask, render_template, request, jsonify
import mysql.connector

app = Flask(__name__)

def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="nenen9000",
        database="python_sql"
    )

@app.route('/')
def index():
    return render_template('index.html')

# Route to render the Signup page
@app.route('/signup_page')
def signup_page():
    return render_template('signup.html')

@app.route('/signin', methods=['POST'])
def signin():
    data = request.get_json()
    identifier = data.get('username')
    password = data.get('password')
    agreed = data.get('agreed')

    if not agreed:
        return jsonify({"status": "error", "message": "You must agree to the terms and conditions."}), 400

    db = get_db()
    cursor = db.cursor(dictionary=True)
    query = "SELECT * FROM vw_users WHERE (user_name = %s OR email = %s) AND password = %s"
    cursor.execute(query, (identifier, identifier, password))
    user = cursor.fetchone()
    cursor.close()
    db.close()

    if user:
        role = str(user.get('type_name', '')).lower()
        if 'admin' in role:
            redirect_url = '/admin_dashboard'
        elif 'cashier' in role:
            redirect_url = '/cashier_dashboard'
        else:
            redirect_url = '/user_dashboard'

        return jsonify({
            "status": "success", 
            "message": f"Welcome back, {user.get('full_name') or user.get('user_name')}!",
            "redirect": redirect_url
        })
        
    return jsonify({"status": "error", "message": "Invalid username/email or password."}), 401

@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    agreed = data.get('agreed')

    if not agreed:
        return jsonify({"status": "error", "message": "You must agree to the terms and conditions."}), 400

    if not username or not email or not password:
        return jsonify({"status": "error", "message": "All fields are required."}), 400

    db = get_db()
    cursor = db.cursor(dictionary=True)

    try:
        # Find 'customer' user_type_id by default
        cursor.execute("SELECT user_type_id FROM user_types WHERE type_name = 'customer'")
        type_result = cursor.fetchone()
        
        if not type_result:
            return jsonify({"status": "error", "message": "Default 'customer' user type not found in database."}), 500
        
        customer_type_id = type_result['user_type_id']

        # Changed 'active' to 1 since status is an integer column
        insert_query = """
            INSERT INTO users (user_type_id, user_name, email, password, create_date, status) 
            VALUES (%s, %s, %s, %s, NOW(), 1)
        """
        cursor.execute(insert_query, (customer_type_id, username, email, password))
        db.commit()
        
        return jsonify({"status": "success", "message": "Account created successfully!", "redirect": "/"})
    
    except mysql.connector.Error as err:
        return jsonify({"status": "error", "message": f"Database error: {err.msg}"}), 400
    finally:
        cursor.close()
        db.close()

@app.route('/admin_dashboard')
def admin_dashboard():
    return render_template('admin.html')

@app.route('/cashier_dashboard')
def cashier_dashboard():
    return render_template('cashier.html')

@app.route('/user_dashboard')
def user_dashboard():
    return render_template('user.html')

if __name__ == '__main__':
    app.run(debug=True)
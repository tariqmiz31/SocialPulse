import os
from dotenv import load_dotenv
from waitress import serve
import psycopg2
from werkzeug.security import generate_password_hash
from flask import Flask
from flask_cors import CORS

# Create Flask app
app = Flask(__name__)
CORS(app)

def create_admin_user():
    try:
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cur = conn.cursor()
        
        # Check if admin exists
        cur.execute("SELECT id FROM users WHERE username = 'admin'")
        if cur.fetchone() is None:
            # Create admin user with hashed password
            hashed_password = generate_password_hash('admin123')
            cur.execute(
                """
                INSERT INTO users (username, password, role, is_approved, status)
                VALUES (%s, %s, %s, %s, %s)
                """,
                ('admin', hashed_password, 'admin', True, 'active')
            )
            conn.commit()
            print("Admin user created successfully")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error creating admin user: {e}")

def main():
    # Load environment variables
    load_dotenv()
    
    # Validate required environment variables
    required_vars = ['DATABASE_URL']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
        return
    
    # Create admin user
    create_admin_user()
    
    # Configure app
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', os.urandom(24))
    
    # Get port from environment variable with fallback
    port = int(os.getenv("PORT", "5000"))
    
    print(f"Starting server on port {port}")
    print(f"Database URL configured: {bool(app.config['SQLALCHEMY_DATABASE_URI'])}")
    
    try:
        # Start production server with waitress
        serve(
            app,
            host="0.0.0.0",
            port=port,
            url_scheme='https',
            threads=4
        )
    except Exception as e:
        print(f"Error starting server: {e}")

if __name__ == "__main__":
    main()

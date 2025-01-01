import os
import sys
from dotenv import load_dotenv
from waitress import serve
from flask import Flask
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2

# Create Flask app
app = Flask(__name__)
CORS(app)

def create_test_user():
    try:
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cur = conn.cursor()

        # Check if test user exists
        cur.execute("SELECT id FROM users WHERE username = 'test_user'")
        if cur.fetchone() is None:
            # Create test user with hashed password
            hashed_password = generate_password_hash('Test@123')
            cur.execute(
                "INSERT INTO users (username, password) VALUES (%s, %s)",
                ('test_user', hashed_password)
            )
            conn.commit()
            print("Test user created successfully")

        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error creating test user: {e}")

def main():
    # Load environment variables
    load_dotenv()

    # Validate required environment variables
    required_vars = ['DATABASE_URL', 'SECRET_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
        sys.exit(1)

    # Configure app from environment
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', os.urandom(24))

    # Get port from environment variable with fallback
    port = int(os.getenv("PORT", "5000"))

    # Create test user
    create_test_user()

    print(f"Starting production server on port {port}")
    print(f"Database URL configured: {bool(app.config['SQLALCHEMY_DATABASE_URI'])}")

    try:
        # Start production server with waitress
        serve(
            app,
            host="0.0.0.0",
            port=port,
            url_scheme='https',
            threads=4,
            connection_limit=1000,
            channel_timeout=30
        )
    except Exception as e:
        print(f"Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
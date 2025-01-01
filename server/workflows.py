from flask_cors import CORS
from flask import Flask
from waitress import serve
from .start import app, main

def start_server():
    try:
        main()  # This will create admin user and setup the app
    except Exception as e:
        print(f"Error starting server: {e}")

if __name__ == "__main__":
    start_server()
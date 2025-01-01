from flask_cors import CORS
from flask import Flask
from waitress import serve
from .start import app, main
import logging
from logging.handlers import RotatingFileHandler

def setup_workflow_logging():
    logger = logging.getLogger('silvarium_workflow')
    logger.setLevel(logging.INFO)

    handler = RotatingFileHandler(
        '/tmp/silvarium_workflow.log',
        maxBytes=1024 * 1024,  # 1MB
        backupCount=3
    )
    handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s'
    ))
    logger.addHandler(handler)
    return logger

def start_server():
    logger = setup_workflow_logging()
    try:
        logger.info("Starting Silvarium Social server...")
        main()  # This will create admin user and setup the app
        logger.info("Server started successfully")
    except Exception as e:
        logger.error(f"Error starting server: {e}")
        raise

if __name__ == "__main__":
    start_server()
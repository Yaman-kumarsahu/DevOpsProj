# app.py

"""
This module contains the main application logic for the Flask API.
It initializes the Flask app, sets up routes, and handles requests.
"""

from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello_world():
     """
    Handles the '/' route. This function returns a simple greeting.
    
    Returns:
        str: A greeting message.
    """
    return 'Hello, Yaman!'

if __name__ == '__main__':
    app.run(debug=True)

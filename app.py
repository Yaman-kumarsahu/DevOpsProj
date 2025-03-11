"""
This module implements a simple Flask app with SocketIO functionality
for creating and joining rooms, sending messages, and handling user connections.
It also includes logging functionality to track activities and errors.
"""

# Standard imports
import logging
import random
from string import ascii_uppercase

# Third-party imports
from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import SocketIO, send, join_room, leave_room

# Initialize the rooms dictionary to store room information
rooms = {}

# Create Flask app and SocketIO instance
app = Flask(__name__)
app.config["SECRET_KEY"] = "Yaman@123"
socketio = SocketIO(app)


# Function to configure logging (can be passed custom logger for testing)
def configure_logger(logger=None):
    """
    Configures a logger for the application, adding both file and console handlers.
    If a logger is passed, it will use that, otherwise, a new one is created.

    Args:
        logger (logging.Logger, optional): The custom logger to configure.

    Returns:
        logging.Logger: The configured logger instance.
    """
    if logger is None:
        logger = logging.getLogger("FlaskApp")

        # Set log level (can be DEBUG, INFO, ERROR)
        logger.setLevel(logging.DEBUG)

        # Create a file handler to log messages to a file
        file_handler = logging.FileHandler('logs/app.log')
        file_handler.setLevel(logging.DEBUG)

        # Create a log format
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)

        # Add file handler to the logger
        logger.addHandler(file_handler)

        # Add a stream handler to log to console as well (optional)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger

# Initialize logger
logger = configure_logger()

# Log every incoming HTTP request
@app.before_request
def log_request():

    """
    Logs each incoming HTTP request with details such as the remote address,
    request date, method, URL, and user agent.
    """
    logger.info("%s - - [%s] \"%s %s %s\"",
                request.remote_addr,
                request.date,
                request.method,
                request.url,
                request.environ.get('HTTP_USER_AGENT', ''))

# Room generation function
def generate_unique_code(length):
    """
    Generates a unique code for the room using uppercase letters.

    Args:
        length (int): The length of the code to be generated.

    Returns:
        str: A unique room code.
    """
    while True:
        code = "".join(random.choice(ascii_uppercase) for _ in range(length))
        if code not in rooms:
            break
    return code

@app.route("/", methods=["POST", "GET"])
def home():
    """
    Handles the home route where users can create a new room or join an existing one.
    """
    session.clear()
    if request.method == "POST":
        name = request.form.get("name")
        code = request.form.get("code")
        join = request.form.get("join", False)
        create = request.form.get("create", False)

        if not name:
            logger.warning("User attempted to join without a name")
            return render_template("home.html", error="Please enter a name.", code=code, name=name)

        if join is not False and not code:
            logger.warning("User attempted to join without a room code")
            return render_template("home.html", error="Please enter a room code.", code=code, name=name)

        room = code
        if create is not False:
            room = generate_unique_code(4)
            rooms[room] = {"members": 0, "messages": []}
            logger.info("Created a new room with code %s", room)
        elif code not in rooms:
            logger.warning("Room %s does not exist", code)
            return render_template("home.html", error="Room does not exist.", code=code, name=name)

        session["room"] = room
        session["name"] = name
        logger.info("User %s joined room %s", name, room)
        return redirect(url_for("room"))

    return render_template("home.html")

@app.route("/room")
def room():
    """
    Displays the room page and ensures the user is in a valid room session.
    """
    room = session.get("room")
    if room is None or session.get("name") is None or room not in rooms:
        logger.warning("User tried to access a room without a valid session")
        return redirect(url_for("home"))

    logger.info("User %s is in room %s", session.get("name"), room)
    return render_template("room.html", code=room, messages=rooms[room]["messages"])

@socketio.on("message")
def message(data):
    """
    Handles incoming messages from clients and broadcasts them to the room.
    """
    room = session.get("room")
    if room not in rooms:
        logger.error("Message received in an invalid room %s", room)
        return

    content = {
        "name": session.get("name"),
        "message": data["data"]
    }
    send(content, to=room)
    rooms[room]["messages"].append(content)
    logger.info("Message from %s in room %s: %s", session.get('name'), room, data['data'])

@socketio.on("connect")
def connect():

    """
    Handles a new connection from a user, ensuring they have a valid room and name.
    """

    room = session.get("room")
    name = session.get("name")
    if not room or not name:
        logger.warning("User connected without a valid room or name")
        return
    if room not in rooms:
        leave_room(room)
        logger.error("Room %s no longer exists, user will be disconnected", room)
        return

    join_room(room)
    send({"name": name, "message": "has entered the room"}, to=room)
    rooms[room]["members"] += 1
    logger.info("%s joined room %s", name, room)

@socketio.on("disconnect")
def disconnect():
    """
    Handles a user's disconnection from the room, updating the room member count.
    """
    room = session.get("room")
    name = session.get("name")
    leave_room(room)

    if room in rooms:
        rooms[room]["members"] -= 1
        if rooms[room]["members"] <= 0:
            del rooms[room]
        logger.info("%s left room %s, members remaining: %d", name, room, rooms[room]["members"])

    send({"name": name, "message": "has left the room"}, to=room)
    logger.info("%s has left room %s", name, room)

if __name__ == "__main__":
    socketio.run(app, debug=True)

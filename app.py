import logging
from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import join_room, leave_room, send, SocketIO
import random
from string import ascii_uppercase

# Create Flask app and SocketIO instance
app = Flask(__name__)
app.config["SECRET_KEY"] = "Yaman@123"
socketio = SocketIO(app)

# In-memory room data
rooms = {}

# Function to configure logging (can be passed custom logger for testing)
def configure_logger(logger=None):
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
    logger.info(f"{request.remote_addr} - - [{request.date}] \"{request.method} {request.url} {request.environ.get('HTTP_USER_AGENT', '')}\"")

# Room generation function
def generate_unique_code(length):
    while True:
        code = ""
        for _ in range(length):
            code += random.choice(ascii_uppercase)
        
        if code not in rooms:
            break
    
    return code

@app.route("/", methods=["POST", "GET"])
def home():
    session.clear()
    if request.method == "POST":
        name = request.form.get("name")
        code = request.form.get("code")
        join = request.form.get("join", False)
        create = request.form.get("create", False)

        if not name:
            logger.warning(f"User attempted to join without a name")
            return render_template("home.html", error="Please enter a name.", code=code, name=name)

        if join != False and not code:
            logger.warning(f"User attempted to join without a room code")
            return render_template("home.html", error="Please enter a room code.", code=code, name=name)
        
        room = code
        if create != False:
            room = generate_unique_code(4)
            rooms[room] = {"members": 0, "messages": []}
            logger.info(f"Created a new room with code {room}")
        elif code not in rooms:
            logger.warning(f"Room {code} does not exist")
            return render_template("home.html", error="Room does not exist.", code=code, name=name)
        
        session["room"] = room
        session["name"] = name
        logger.info(f"User {name} joined room {room}")
        return redirect(url_for("room"))

    return render_template("home.html")

@app.route("/room")
def room():
    room = session.get("room")
    if room is None or session.get("name") is None or room not in rooms:
        logger.warning("User tried to access a room without a valid session")
        return redirect(url_for("home"))

    logger.info(f"User {session.get('name')} is in room {room}")
    return render_template("room.html", code=room, messages=rooms[room]["messages"])

@socketio.on("message")
def message(data):
    room = session.get("room")
    if room not in rooms:
        logger.error(f"Message received in an invalid room {room}")
        return 
    
    content = {
        "name": session.get("name"),
        "message": data["data"]
    }
    send(content, to=room)
    rooms[room]["messages"].append(content)
    logger.info(f"Message from {session.get('name')} in room {room}: {data['data']}")

@socketio.on("connect")
def connect(auth):
    room = session.get("room")
    name = session.get("name")
    if not room or not name:
        logger.warning(f"User connected without a valid room or name")
        return
    if room not in rooms:
        leave_room(room)
        logger.error(f"Room {room} no longer exists, user will be disconnected")
        return
    
    join_room(room)
    send({"name": name, "message": "has entered the room"}, to=room)
    rooms[room]["members"] += 1
    logger.info(f"{name} joined room {room}")

@socketio.on("disconnect")
def disconnect():
    room = session.get("room")
    name = session.get("name")
    leave_room(room)

    if room in rooms:
        rooms[room]["members"] -= 1
        if rooms[room]["members"] <= 0:
            del rooms[room]
        logger.info(f"{name} left room {room}, members remaining: {rooms[room]['members']}")
    
    send({"name": name, "message": "has left the room"}, to=room)
    logger.info(f"{name} has left room {room}")

if __name__ == "__main__":
    socketio.run(app, debug=True)

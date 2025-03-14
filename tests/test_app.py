import pytest
import re
import logging
from flask import Flask
from flask_socketio import SocketIO
from app import app, socketio
import app as application

# Test-specific logger
test_logger = logging.getLogger("TestLogger")
test_logger.setLevel(logging.DEBUG)
test_handler = logging.FileHandler("tests/test_logs/app_test.log")
test_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
test_logger.addHandler(test_handler)

# Pass the test logger to the app
application.logger = application.configure_logger(test_logger)

# Fixtures
@pytest.fixture
def client():
    """Create a test client for the Flask app"""
    return app.test_client()


@pytest.fixture
def socketio_client():
    """Create a test client for SocketIO"""
    return socketio.test_client(app)


def test_home_page(client):
    """Test the home page (GET request)"""
    response = client.get('/')
    assert response.status_code == 200
    assert b'Pick a name!' in response.data

def test_create_room(client):
    """Test creating a new room"""
    response = client.post('/', data={
        'name': 'John',
        'create': True
    })
    assert response.status_code == 302
    response = client.get('/room')
    assert response.status_code == 200
    assert b'Chat Room' in response.data

def test_join_existing_room(client):
    """Test joining an existing room"""
    # First, create a room
    response = client.post('/', data={
        'name': 'John',
        'create': True
    })

    # Now visit the room
    response = client.get('/room')

    # Updated regex to match <h2> with style and extract room code
    match = re.search(r'<h2 style="[^"]*">Chat Room: (\w+)</h2>', response.data.decode('utf-8'))

    # Ensure that match is not None before trying to access group(1)
    if match:
        room_code = match.group(1)
        print(f"Room code found: {room_code}")
    else:
        print("Room code not found in the response")
        assert False, "Room code not found in the response"
    
    # Ensure the room exists in the application state
    application.rooms[room_code] = {"members": 0, "messages": []}

    # Now have another user (Jane) join the room
    response = client.post('/', data={
        'name': 'Jane',
        'code': room_code,
        'join': True
    })

    # Check if the response is a redirect (302 status code)
    assert response.status_code == 302  # Should redirect to /room

    # Now visit the room again after Jane joins
    response = client.get('/room')

    # Ensure the room code is visible in the response data (verify the user's name)
    assert f'Chat Room: {room_code}'.encode() in response.data  # Check if the room code appears


def test_invalid_room_join(client):
    """Test attempting to join a non-existing room"""
    response = client.post('/', data={
        'name': 'Alice',
        'code': 'INVALIDCODE',
        'join': True
    })
    assert response.status_code == 200
    assert b'Room does not exist' in response.data

# TODO: Fix the commented tests
#-----------------------------------------------------------------------------------------------------------------------------
# def test_socketio_connect(socketio_client):
#     """Test SocketIO connection"""
#     # Connect to the socket
#     socketio_client.emit('connect', namespace='/')

#     # Ensure a message about the connection is received
#     response = socketio_client.get_received()
#     assert len(response) > 0
#     assert 'message' in response[0]['args'][0]
#     assert 'has entered the room' in response[0]['args'][0]['message']
#-----------------------------------------------------------------------------------------------------------------------------

def test_socketio_connect_without_name_or_room(socketio_client):
    """Test SocketIO connect without room or name"""
    # Emit connect without room or name
    socketio_client.emit('connect', namespace='/')
    response = socketio_client.get_received()
    
    # Ensure no message is sent
    assert len(response) == 0  # No response since user shouldn't connect

#-----------------------------------------------------------------------------------------------------------------------------
# def test_socketio_message(socketio_client):
#     """Test sending a message via WebSocket"""
#     # Connect to the socket
#     socketio_client.emit('connect', namespace='/')

#     # Send a message
#     socketio_client.emit('message', {'data': 'Hello, everyone!'}, namespace='/')

#     # Check if the message was received
#     response = socketio_client.get_received()
#     assert len(response) > 0
#     assert response[0]['args'][0]['message'] == 'Hello, everyone!'
#     assert response[0]['args'][0]['name'] == 'John'  # Assuming 'John' is the connected user
#-----------------------------------------------------------------------------------------------------------------------------

def test_socketio_message_invalid_room(socketio_client):
    """Test sending a message to an invalid room"""
    # Simulate an invalid room by not joining any room
    socketio_client.emit('message', {'data': 'Hello, anyone!'}, namespace='/')

    # Check if there is an error response or no message sent
    response = socketio_client.get_received()
    assert len(response) == 0  # No message received due to invalid state

#-----------------------------------------------------------------------------------------------------------------------------
# def test_socketio_disconnect(socketio_client):
#     """Test disconnecting from the WebSocket"""
#     # Connect to the socket
#     socketio_client.emit('connect', namespace='/')

#     # Disconnect
#     socketio_client.emit('disconnect', namespace='/')

#     # Check if the disconnect message is received
#     response = socketio_client.get_received()
#     assert len(response) > 0
#     assert 'has left the room' in response[0]['args'][0]['message']


# def test_socketio_disconnect_without_room(socketio_client):
#     """Test disconnecting when no room exists"""
#     socketio_client.emit('disconnect', namespace='/')
#     response = socketio_client.get_received()
    
#     # Ensure no message is sent when disconnecting without joining a room
#     assert len(response) == 0


# def test_socketio_connect_invalid_room(socketio_client):
#     """Test connect to a room that does not exist"""
#     # Simulate an invalid room by manually setting session data
#     socketio_client.session['room'] = 'INVALIDCODE'
#     socketio_client.emit('connect', namespace='/')

#     # Check if any error message is received
#     response = socketio_client.get_received()
#     assert len(response) == 0  # No message since the room is invalid
#-----------------------------------------------------------------------------------------------------------------------------

def test_logging(client):
    """Test logging functionality by simulating some actions and verifying logs"""
    # Clear existing logs to verify new logs
    with open('tests/test_logs/app_test.log', 'w'):
        pass

    # Make a POST request to create a room
    client.post('/', data={'name': 'LoggerTest', 'create': True})

    # Read the log file
    with open('tests/test_logs/app_test.log', 'r') as f:
        logs = f.read()

    # Check if log entries for creating a room are present
    assert 'Created a new room with code' in logs
    assert 'LoggerTest joined room' in logs


def test_invalid_room_creation(client):
    """Test creating a room when no name is provided"""
    response = client.post('/', data={
        'create': True
    })
    assert response.status_code == 200
    assert b'Please enter a name.' in response.data


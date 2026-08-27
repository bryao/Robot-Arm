from flask import Flask, render_template
from flask_socketio import SocketIO
from canStepper import MKSServo42DCANController
import cv2
import base64
import time

app = Flask(__name__)
# Removed async_mode='eventlet' so Flask-SocketIO uses standard threading
socketio = SocketIO(app, cors_allowed_origins="*")


# Initialize Motor Interface
motor = MKSServo42DCANController()

# Initialize Camera with DirectShow on Windows for better stability
cap = cv2.VideoCapture('/dev/video0', cv2.CAP_V4L2)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)

frame_retrieval_delay = 0.033  # ~30 FPS
thread = None

def background_thread():
    """Capture frames and broadcast via WebSockets."""
    print("Camera streaming thread started...")
    while True:
        socketio.sleep(frame_retrieval_delay)
        ret, frame = cap.read()
        if not ret:
            print("Error: Failed to capture image from camera.")
            continue
        
        # Compress and encode image
        _, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
        jpg_as_text = base64.b64encode(buffer).decode('utf-8')
        
        socketio.emit('frame', {'data': jpg_as_text})

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    global thread
    print('Client connected')
    if thread is None:
        thread = socketio.start_background_task(background_thread)

@socketio.on('pan')
def handle_pan(data):
    direction = data.get('direction')
    if direction == 'left':
        print('turning left')
        motor.turn_left()
    elif direction == 'right':
        print('turning right')
        motor.turn_right()

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5001, debug=False)
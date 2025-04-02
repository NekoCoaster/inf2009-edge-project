import gpiozero
import base64
import time
import os
import subprocess
import threading
import paho.mqtt.client as mqtt

# MQTT Config
BROKER = "nekocoaster.ddns.net"
PORT = 16883
USERNAME = "team24"
PASSWORD = "qwerty123456"

PUBLISH_NAV_TOPIC = "team24/rov/navcam"
PUBLISH_CAMERA_TOPIC = "team24/rov/camera"

SUB_TOPICS = [
    "team24/fog/AI_Status",
    "team24/fog/result",
    "team24/fog/navdir"
]

# State variables
FOG_NAVDIR = 'E'  # Default to 'E' for stop.
FOG_AI_BUSY = False
FOG_RESULT = False

# Motor Setup
in1 = gpiozero.OutputDevice(16)
in2 = gpiozero.OutputDevice(26)
en_a = gpiozero.PWMOutputDevice(12)

in3 = gpiozero.OutputDevice(5)
in4 = gpiozero.OutputDevice(6)
en_b = gpiozero.PWMOutputDevice(13)

en_a.on()
en_b.on()



# -----------------------------------------
# LiDAR distance Functions
# -----------------------------------------

# Function to get the 90-degree distance
def get_90_degree_distance():
    try:
        with open(os.path.expanduser("~/scan_90deg.txt"), "r") as f:
            value = float(f.read().strip())
            return value
    except Exception:
        return None

# Function to check if the distance is safe (less than threshold)
def wait_for_safe_90_distance(threshold=0.2):
    while True:
        distance = get_90_degree_distance()
        if distance is not None:
            print(f" 90° distance: {distance:.2f} m")
            if distance < threshold:
                print("Emergency stop! Object too close (< 0.2m). Aborting movement.")
                move_backward(speed=0.5, duration=0.3)
                return False
            return True
        time.sleep(0.1)

# -----------------------------------------
# Movement and Image Capture Functions
# -----------------------------------------

def stop():
    en_a.value = 0
    en_b.value = 0
    in1.off()
    in2.off()
    in3.off()
    in4.off()
    print("Motors stopped.")

def move_forward(speed=1.0, duration=2):
    en_a.value = 0.5
    en_b.value = speed
    in1.off()
    in2.on()
    in3.on()
    in4.off()
    print("Moving forward")
    time.sleep(duration)
    stop()

def move_backward(speed=0.5, duration=0.5):
    en_a.value = 0.9
    en_b.value = speed
    in1.on()
    in2.off()
    in3.off()
    in4.on()
    print("Moving backward")
    time.sleep(duration)
    stop()

def rotate_left(speed=1.0, duration=0.4):
    en_a.value = 0.5
    en_b.value = speed
    in1.on()
    in2.off()
    in3.on()
    in4.off()
    print("Rotating left")
    time.sleep(duration)
    stop()

def rotate_right(speed=1.0, duration=0.3):
    en_a.value = 0.5
    en_b.value = speed
    in1.off()
    in2.on()
    in3.off()
    in4.on()
    print("Rotating right")
    time.sleep(duration)
    stop()

def capture_and_send_image_object():
    image_path = "objective.jpg"
    subprocess.run(["fswebcam", "-S", "20", "-r", "1280x720", "--no-banner", image_path])
    print("Object image captured.")
    with open(image_path, "rb") as img_file:
        image_b64 = base64.b64encode(img_file.read()).decode("utf-8")
        mqtt_client.publish(PUBLISH_CAMERA_TOPIC, image_b64)
        print("Object image sent to MQTT.")

def capture_and_send_image_navigation():
    image_path = "navigation.jpg"
    subprocess.run(["fswebcam", "-S", "20", "-r", "1280x720", "--no-banner", image_path])
    print("Navigation image captured.")
    with open(image_path, "rb") as img_file:
        image_b64 = base64.b64encode(img_file.read()).decode("utf-8")
        mqtt_client.publish(PUBLISH_NAV_TOPIC, image_b64)
        print("Navigation image sent to MQTT.")

# -----------------------------------------
# Topic Handlers
# -----------------------------------------

def handle_ai_status(payload):
    global FOG_AI_BUSY
    # Expected values: "READY" or "BUSY"
    if payload.upper() == "BUSY":
        FOG_AI_BUSY = True
    elif payload.upper() == "READY":
        FOG_AI_BUSY = False
    print(f"[AI Status] Updated to: {payload}")

def handle_result(payload):
    global FOG_RESULT
    # Expected values: "YES", "NO", or "BUSY"
    if payload.upper() == "YES":
        FOG_RESULT = True
        print("[Result] Goal object found. Stopping ROV.")
        stop()
    elif payload.upper() == "NO":
        FOG_RESULT = False
        print("[Result] Goal object not found.")
    else:
        print("[Result] Still processing...")
    print(f"[Result] Updated to: {payload}")

def handle_navdir(payload):
    global FOG_NAVDIR
    # Expected values: "W", "A", "S", "D", "E", or "BUSY"
    if payload.upper() != "BUSY":
        FOG_NAVDIR = payload.upper()
    print(f"[NavDir] Updated to: {payload}")

# Dictionary mapping topics to their handler functions
topic_handlers = {
    "team24/fog/AI_Status": handle_ai_status,
    "team24/fog/result": handle_result,
    "team24/fog/navdir": handle_navdir,
}

# -----------------------------------------
# MQTT Callbacks
# -----------------------------------------

def on_connect(client, userdata, flags, rc):
    print(f"Connected with result code {rc}")
    for topic in SUB_TOPICS:
        client.subscribe(topic)
        print(f"Subscribed to {topic}")

def on_message(client, userdata, msg):
    payload = msg.payload.decode().strip()
    handler = topic_handlers.get(msg.topic)
    if handler:
        handler(payload)
    else:
        print(f"[Unhandled Topic] {msg.topic}: {payload}")

# -----------------------------------------
# Main Control Loop
# -----------------------------------------

def main_thread():
    global FOG_NAVDIR, FOG_AI_BUSY, FOG_RESULT
    while True:
        if not FOG_RESULT and not FOG_AI_BUSY:
            # Stage 1: Capture image for object detection
            capture_and_send_image_object()
            time.sleep(1)  # Wait for the image to be sent
            
            # Wait until the AI has finished processing
            while FOG_AI_BUSY:
                print("Waiting for AI to process object image...")
                time.sleep(1)
            
            # Stage 2: Capture image for navigation commands
            capture_and_send_image_navigation()
            time.sleep(1)  # Wait for the image to be sent
            
            while FOG_AI_BUSY:
                print("Waiting for AI to process navigation image...")
                time.sleep(1)
            
            # Stage 3: Execute navigation command based on AI result
            if FOG_NAVDIR == 'W':
                if wait_for_safe_90_distance():  # Check if it's safe to move
                    move_forward()
            elif FOG_NAVDIR == 'S':
                if wait_for_safe_90_distance():  # Check if it's safe to move
                    move_backward()
            elif FOG_NAVDIR == 'A':
                if wait_for_safe_90_distance():  # Check if it's safe to move
                    rotate_left()
            elif FOG_NAVDIR == 'D':
                if wait_for_safe_90_distance():  # Check if it's safe to move
                    rotate_right()
            elif FOG_NAVDIR == 'E':
                stop()
            
            FOG_NAVDIR = 'E'  # Reset to stop after executing command
        else:
            print("ROV inactive: either goal object has been found or AI is processing.")
            time.sleep(1)

# -----------------------------------------
# MQTT Client Setup and Main Loop
# -----------------------------------------

mqtt_client = mqtt.Client()
mqtt_client.username_pw_set(USERNAME, PASSWORD)
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(BROKER, PORT, 60)

# Run the main control loop in a separate daemon thread
main_thread_thread = threading.Thread(target=main_thread, daemon=True)
main_thread_thread.start()

# Start the MQTT loop (blocking call)
mqtt_client.loop_forever()

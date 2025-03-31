import gpiozero
import base64
import time
import os
import subprocess
import threading
import paho.mqtt.client as mqtt
import subprocess
import threading


# MQTT Config
BROKER = "nekocoaster.ddns.net"
PORT = 16883
USERNAME = "team24"
PASSWORD = "qwerty123456"

PUBLISH_IMAGE_TOPIC = "team24/rov/navcam"
PUBLISH_GOAL_TOPIC = "team24/fog/goal"
SUB_TOPICS = [
    "team24/fog/AI_Status",
    "team24/fog/result",
    "team24/fog/navdir"
]

# Motor Setup
in1 = gpiozero.OutputDevice(16)
in2 = gpiozero.OutputDevice(26)
en_a = gpiozero.PWMOutputDevice(12)

in3 = gpiozero.OutputDevice(5)
in4 = gpiozero.OutputDevice(6)
en_b = gpiozero.PWMOutputDevice(13)

en_a.on()
en_b.on()

# State variables
goal_sent = False
ai_ready = False
result_received = False
navdir_received = False

# Timing
last_ai_status = 0
last_result = 0
nav_timeout_timer = None

# Add this first
def get_90_degree_distance():
    try:
        with open(os.path.expanduser("~/scan_90deg.txt"), "r") as f:
            value = float(f.read().strip())
            return value
    except Exception:
        return None

# Then this below it
def wait_for_safe_90_distance(threshold=0.2):
    while True:
        distance = get_90_degree_distance()
        if distance is not None:
            print(f"📏 90° distance: {distance:.2f} m")
            if distance < threshold:
                print("🛑 Emergency stop! Object too close (< 0.3m). Aborting movement.")
                return False
            return True
        time.sleep(0.1)



def stop():
    global result_received
    en_a.value = 0
    en_b.value = 0
    in1.off()
    in2.off()
    in3.off()
    in4.off()
    print("Motors stopped.")

    if not result_received:
        capture_and_send_image()
    else:
        print("🚫 Skipping image capture: goal already found.")


def move_forward(speed=0.75, duration=3):
    en_a.value = speed
    en_b.value = speed
    in1.off()
    in2.on()
    in3.on()
    in4.off()
    print("Moving forward")
    time.sleep(duration)
    stop()

def move_backward(speed=0.6, duration=2):
    en_a.value = 0.61
    en_b.value = speed
    in1.on()
    in2.off()
    in3.off()
    in4.on()
    print("Moving backward")
    time.sleep(duration)
    stop()

def rotate_left(speed=1.0, duration=0.4):
    en_a.value = speed
    en_b.value = speed
    in1.on()
    in2.off()
    in3.on()
    in4.off()
    print("Rotating left")
    time.sleep(duration)
    stop()

def rotate_right(speed=1.0, duration=0.3):
    en_a.value = speed
    en_b.value = speed
    in1.off()
    in2.on()
    in3.off()
    in4.on()
    print("Rotating right")
    time.sleep(duration)
    stop()

def capture_and_send_image():
    image_path = "image2.jpg"
    subprocess.run(["fswebcam", "-S", "20", "-r", "1280x720", "--no-banner", image_path])
    print("Image captured.")

    with open(image_path, "rb") as img_file:
        image_b64 = base64.b64encode(img_file.read()).decode("utf-8")
        mqtt_client.publish(PUBLISH_IMAGE_TOPIC, image_b64)
        print("Image sent to MQTT.")

def prompt_for_goal():
    global ai_ready, result_received, navdir_received
    ai_ready = False
    result_received = False
    navdir_received = False

    while True:
        goal = input("\n🎯 Enter NEW goal for the AI to find: ").strip()
        if goal:
            mqtt_client.publish(PUBLISH_GOAL_TOPIC, goal)
            print(f"✅ Goal '{goal}' sent to MQTT topic {PUBLISH_GOAL_TOPIC}")
            return True
        print("❗ Goal cannot be empty. Please try again.")

def start_navdir_timeout_timer():
    global nav_timeout_timer

    if nav_timeout_timer:
        nav_timeout_timer.cancel()

    def timeout_check():
        global navdir_received
        if not navdir_received:
            print("⚠️ No navdir received in 10s. Resending image...")
            capture_and_send_image()

    nav_timeout_timer = threading.Timer(10.0, timeout_check)
    nav_timeout_timer.start()

# MQTT callbacks
def on_connect(client, userdata, flags, rc):
    print(f"Connected with result code {rc}")
    for topic in SUB_TOPICS:
        client.subscribe(topic)
        print(f"Subscribed to {topic}")

    global goal_sent, ai_ready, result_received, navdir_received
    ai_ready = False
    result_received = False
    navdir_received = False
    goal_sent = prompt_for_goal()
    if goal_sent:
        capture_and_send_image()

def on_message(client, userdata, msg):
    global ai_ready, result_received, navdir_received, nav_timeout_timer, goal_sent

    topic = msg.topic
    payload = msg.payload.decode().strip().upper()
    print(f"Received on {topic}: {payload}")

    if topic == "team24/fog/AI_Status":
        if payload == "READY":
            ai_ready = True
            print("AI is READY for new image.")
            if ai_ready and result_received:
                start_navdir_timeout_timer()
        else:
            ai_ready = False
            print("AI is BUSY.")

    elif topic == "team24/fog/result":
        if payload in ["YES", "NO"]:
            result_received = True
            print(f"AI Result: {payload}")
            if ai_ready and result_received:
                start_navdir_timeout_timer()
        if payload == "YES":
            print("Goal FOUND. Requesting new goal...")
            if nav_timeout_timer:
                nav_timeout_timer.cancel()
            ai_ready = False
            result_received = True
            navdir_received = False
            stop()
            print("🕒 Waiting for NEW goal. Please enter it manually below:")
            '''
            goal_sent = prompt_for_goal()
            if goal_sent:
                capture_and_send_image()
                '''


    elif topic == "team24/fog/navdir":
        time.sleep(2)
        if result_received and not ai_ready:
            print("🛑 Ignoring navdir. Goal already found. Prompting for new goal.")
            stop()
            goal_sent = prompt_for_goal()
            if goal_sent:
                capture_and_send_image()
            return  # Exit navdir handling early

        navdir_received = True
        if nav_timeout_timer:
            nav_timeout_timer.cancel()
        print(f"NAVDIR received: {payload}")
        if payload in ["W", "S", "A", "D"]:
            print(f"[DEBUG] Navdir '{payload}' received. Checking distance...")
            if wait_for_safe_90_distance():
                print("[DEBUG] Safe to move.")
                if payload == "W":
                    print("[DEBUG] Executing move_forward()")
                    move_forward()
                elif payload == "S":
                    print("[DEBUG] Executing move_backward()")
                    move_backward()
                elif payload == "A":
                    print("[DEBUG] Executing rotate_left()")
                    rotate_left()
                elif payload == "D":
                    print("[DEBUG] Executing rotate_right()")
                    rotate_right()
            else:
                print("⚠️ Movement skipped due to safety condition.")

        elif payload == "STOP":
            stop()
        elif payload == "BUSY":
            print("Navdir: Server still processing.")


# MQTT Client Setup
mqtt_client = mqtt.Client()
mqtt_client.username_pw_set(USERNAME, PASSWORD)
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(BROKER, PORT, 60)

# Start MQTT Loop
mqtt_client.loop_forever()


import base64
import io
import sys
from PIL import Image, ImageTk
import tkinter as tk
import paho.mqtt.client as mqtt

# -------- MQTT Configuration --------
MQTT_BROKER = "nekocoaster.ddns.net"       # Replace with your broker
MQTT_PORT = 16883
MQTT_TOPIC = "team24/rov/navcam"        # Replace with your topic
MQTT_USERNAME = "ImageViewer"         # Replace with your username
MQTT_PASSWORD = "qwerty123456"         # Replace with your password

# -------- GUI Setup --------
class ImageViewer:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Live MQTT Image Viewer")
        self.label = tk.Label(self.root)
        self.label.pack()

    def update_image(self, image_data):
        image = Image.open(io.BytesIO(image_data))
        photo = ImageTk.PhotoImage(image)
        self.label.config(image=photo)
        self.label.image = photo  # Prevent garbage collection

    def run(self):
        self.root.mainloop()

# -------- MQTT Callbacks --------
viewer = ImageViewer()

def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))
    if rc == 0:
        client.subscribe(MQTT_TOPIC)
    else:
        print("Failed to connect. Return code:", rc)

def on_message(client, userdata, msg):
    try:
        base64_str = msg.payload.decode("utf-8")
        image_data = base64.b64decode(base64_str)
        viewer.update_image(image_data)
        print("Image updated")
    except Exception as e:
        print(f"Failed to process message: {e}")

# -------- MQTT Client Setup --------
client = mqtt.Client()
client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
client.on_connect = on_connect
client.on_message = on_message

try:
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
except Exception as e:
    print(f"Failed to connect to MQTT Broker: {e}")
    sys.exit(1)

# -------- Start MQTT in Background --------
client.loop_start()

# -------- Start GUI --------
viewer.run()

# Optional: Stop loop when GUI is closed
client.loop_stop()
client.disconnect()

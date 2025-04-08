import base64
import io
import sys
import copy
import time
import threading
import warnings

import paho.mqtt.client as mqtt
from PIL import Image
import torch

# Import LLaVA modules (make sure llava is installed)
from llava.model.builder import load_pretrained_model
from llava.mm_utils import process_images, tokenizer_image_token
from llava.constants import IMAGE_TOKEN_INDEX, DEFAULT_IMAGE_TOKEN
from llava.conversation import conv_templates

# ------------------------------
# 0. Configurable variables
# ------------------------------

# MQTT Configuration
MQTT_BROKER = "nekocoaster.ddns.net"       # Replace with your broker 
MQTT_PORT = 16883
MQTT_USERNAME = "llava"         # Replace with your username 
MQTT_PASSWORD = "qwerty123456"         # Replace with your password

# Image Configuration
IMG_MAX_RES = 360  # The maximum width/height of the incoming image

# MQTT Topics
TOPIC_ROV_CAMERA = "team24/rov/camera"       # Images (base64 string) published by the ROV
TOPIC_FOG_AI_STATUS = "team24/fog/AI_Status"   # Publish "READY" or "BUSY" (AI status)
TOPIC_FOG_RESULT = "team24/fog/result"         # Publish "YES", "NO" or "BUSY" (detection result)
TOPIC_COMMAND_OBJECTIVE = "team24/fog/goal"  # Contains the object to look for

# Global variable for the current objective (default if none received)
objective = "object"

# Global variable to indicate if the model is busy processing an image.
model_busy = False
busy_lock = threading.Lock()

# ------------------------------
# 1. Connect & Load the Model
# ------------------------------

# First, try connecting to the MQTT broker using username and password.
client = mqtt.Client()
client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("DEBUG - Connected to MQTT Broker")
        # Subscribe to image and objective topics
        client.subscribe(TOPIC_ROV_CAMERA)
        client.subscribe(TOPIC_COMMAND_OBJECTIVE)
    else:
        print("DEBUG - Failed to connect, return code", rc)
        sys.exit(1)

client.on_connect = on_connect

try:
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
except Exception as e:
    print("DEBUG - MQTT connection error:", e)
    sys.exit(1)

# Load the model (this may take some time)
warnings.filterwarnings("ignore")
pretrained = "lmms-lab/llava-onevision-qwen2-7b-ov-chat"
model_name = "llava_qwen"
device = "cuda"
device_map = "cuda"

print("DEBUG - Loading pretrained model")
tokenizer, model, image_processor, max_length = load_pretrained_model(pretrained, None, model_name, device_map=device_map)
print("DEBUG - Setting model to eval()")
model.eval()

# ------------------------------
# 2. Image Processing & Model Inference
# ------------------------------

def process_image(base64_payload):
    """
    Given a base64 string payload, decode the image, resize if needed,
    build a fresh prompt using the current objective, run the model, and return YES/NO.
    """
    global objective
    try:
        # Decode the base64 string into binary data and open the image
        image_data = base64.b64decode(base64_payload)
        image = Image.open(io.BytesIO(image_data)).convert("RGB")

        # Resize the image if its width or height exceeds IMG_MAX_RES while preserving aspect ratio
        width, height = image.size
        if width > IMG_MAX_RES or height > IMG_MAX_RES:
            scale = IMG_MAX_RES / float(max(width, height))
            new_width = int(width * scale)
            new_height = int(height * scale)
            image = image.resize((new_width, new_height))
            print(f"DEBUG - Resized image to {new_width}x{new_height}")
        else:
            print("DEBUG - Image size is within limits")

        # Build a fresh prompt using DEFAULT_IMAGE_TOKEN and the current objective.
        # For example: "DEFAULT_IMAGE_TOKEN\nJust answer with 'Yes' or 'No'. Does this image contain <objective>?"
        question = DEFAULT_IMAGE_TOKEN + "\nJust answer with 'Yes' or 'No'. Does this image contain " + objective + "?"
        print(f"DEBUG - Question: {question}")

        # Process the image using the provided image_processor from LLaVA.
        image_tensor = process_images([image], image_processor, model.config)
        image_tensor = [_image.to(dtype=torch.float16, device=device) for _image in image_tensor]

        # Prepare a fresh conversation template (to avoid contamination from previous prompts)
        conv_template = "qwen_2"
        conv = copy.deepcopy(conv_templates[conv_template])
        conv.append_message(conv.roles[0], question)
        conv.append_message(conv.roles[1], None)
        prompt_question = conv.get_prompt()
        print(f"DEBUG - Prompt: {prompt_question}")

        # Tokenize the prompt and attach the image token(s)
        input_ids = tokenizer_image_token(prompt_question, tokenizer, IMAGE_TOKEN_INDEX, return_tensors="pt").unsqueeze(0).to(device)
        image_sizes = [image.size]
        print(f"DEBUG - Image sizes: {image_sizes}")

        # Generate answer from the model
        cont = model.generate(
            input_ids,
            images=image_tensor,
            image_sizes=image_sizes,
            do_sample=False,
            temperature=0,
            max_new_tokens=16,
        )

        text_outputs = tokenizer.batch_decode(cont, skip_special_tokens=True)
        print("DEBUG - Model output:", text_outputs)

        # Determine result based on output text (check for YES or NO in output)
        result_text = text_outputs[0].strip().upper()
        if "YES" in result_text:
            result = "YES"
        elif "NO" in result_text:
            result = "NO"
        else:
            result = "NO"  # Fallback if not clear

        print("DEBUG - Final result:", result)
        return result
    except Exception as e:
        print("DEBUG - Error processing image:", e)
        return None

# ------------------------------
# 3. MQTT Message Callbacks
# ------------------------------

def on_message(client, userdata, msg):
    global model_busy, objective
    topic = msg.topic
    payload = msg.payload.decode("utf-8")
    print(f"DEBUG - Received message on topic {topic}")

    # Update objective if received on the corresponding topic.
    if topic == TOPIC_COMMAND_OBJECTIVE:
        objective = payload
        print(f"DEBUG - Updated objective to: {objective}")

    # Process image if received on the camera topic.
    elif topic == TOPIC_ROV_CAMERA:
        # Check if model is busy processing a previous image.
        with busy_lock:
            if model_busy:
                print("DEBUG - Model is busy, publishing BUSY")
                client.publish(TOPIC_FOG_AI_STATUS, "BUSY")
                client.publish(TOPIC_FOG_RESULT, "BUSY")
                return
            else:
                model_busy = True

        # Publish BUSY status
        client.publish(TOPIC_FOG_AI_STATUS, "BUSY")
        client.publish(TOPIC_FOG_RESULT, "BUSY")

        # Process the image in a separate thread so as not to block the MQTT loop.
        def processing_thread():
            global model_busy
            result = process_image(payload)
            if result is not None:
                client.publish(TOPIC_FOG_RESULT, result)
            else:
                client.publish(TOPIC_FOG_RESULT, "NO")
            client.publish(TOPIC_FOG_AI_STATUS, "READY")
            with busy_lock:
                model_busy = False

        t = threading.Thread(target=processing_thread)
        t.start()

client.on_message = on_message

# ------------------------------
# 4. Start the MQTT Loop
# ------------------------------

client.loop_start()

# Keep the script running indefinitely until a KeyboardInterrupt is received.
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("DEBUG - Exiting...")
finally:
    client.loop_stop()
    client.disconnect()

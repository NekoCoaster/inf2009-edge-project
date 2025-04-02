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
MQTT_USERNAME = "llava"                     # Replace with your username
MQTT_PASSWORD = "qwerty123456"              # Replace with your password

# Image Configuration
IMG_MAX_RES = 360  # The maximum width/height of incoming images

# MQTT Topics
TOPIC_ROV_CAMERA       = "team24/rov/camera"    # Images (base64) published by the ROV
TOPIC_ROV_NAVCAM       = "team24/rov/navcam"      # Navigation camera images (base64)
TOPIC_COMMAND_OBJECTIVE = "team24/fog/goal"       # Contains the object to look for

TOPIC_FOG_AI_STATUS    = "team24/fog/AI_Status"   # Publish "READY" or "BUSY" (AI status)
TOPIC_FOG_RESULT       = "team24/fog/result"      # Publish "YES" or "NO" (object detection result)
TOPIC_FOG_NAVDIR       = "team24/fog/navdir"      # Publish navigation directions (W, A, S, D, or STOP)

# Global variable for the current objective (default if none received)
objective = "object"

# Global variable to indicate if the model is busy processing an image.
model_busy = False
busy_lock = threading.Lock()

# ------------------------------
# 1. Connect & Load the Model
# ------------------------------

client = mqtt.Client()
client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("DEBUG - Connected to MQTT Broker")
        # Subscribe to all relevant topics
        client.subscribe(TOPIC_ROV_CAMERA)
        client.subscribe(TOPIC_ROV_NAVCAM)
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
# 2. Image Processing & Model Inference Functions
# ------------------------------

def process_image(base64_payload):
    """
    Process an image from the ROV camera topic.
    Returns "YES" or "NO" based on whether the image contains the current objective.
    """
    global objective
    try:
        image_data = base64.b64decode(base64_payload)
        image = Image.open(io.BytesIO(image_data)).convert("RGB")
        
        # Resize while maintaining aspect ratio if necessary
        width, height = image.size
        if width > IMG_MAX_RES or height > IMG_MAX_RES:
            scale = IMG_MAX_RES / float(max(width, height))
            new_width = int(width * scale)
            new_height = int(height * scale)
            image = image.resize((new_width, new_height))
            print(f"DEBUG - Resized image to {new_width}x{new_height}")
        else:
            print("DEBUG - Image size is within limits")
        
        # Build prompt using the current objective
        question = DEFAULT_IMAGE_TOKEN + "\nJust answer with 'Yes' or 'No'. Does this image contain " + objective + "?"
        print(f"DEBUG - Question: {question}")

        image_tensor = process_images([image], image_processor, model.config)
        image_tensor = [_image.to(dtype=torch.float16, device=device) for _image in image_tensor]

        conv_template = "qwen_2"
        conv = copy.deepcopy(conv_templates[conv_template])
        conv.append_message(conv.roles[0], question)
        conv.append_message(conv.roles[1], None)
        prompt_question = conv.get_prompt()
        print(f"DEBUG - Prompt: {prompt_question}")

        input_ids = tokenizer_image_token(prompt_question, tokenizer, IMAGE_TOKEN_INDEX, return_tensors="pt").unsqueeze(0).to(device)
        image_sizes = [image.size]
        print(f"DEBUG - Image sizes: {image_sizes}")

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

        result_text = text_outputs[0].strip().upper()
        if "YES" in result_text:
            result = "YES"
        elif "NO" in result_text:
            result = "NO"
        else:
            result = "NO"  # Fallback if unclear

        print("DEBUG - Final result:", result)
        return result
    except Exception as e:
        print("DEBUG - Error processing image:", e)
        return None

def process_navcam_image(base64_payload):
    """
    Process an image from the ROV navigation camera topic.
    Returns a navigation command: one of "W", "A", "S", "D", or "STOP".
    """
    try:
        image_data = base64.b64decode(base64_payload)
        image = Image.open(io.BytesIO(image_data)).convert("RGB")
        
        width, height = image.size
        if width > IMG_MAX_RES or height > IMG_MAX_RES:
            scale = IMG_MAX_RES / float(max(width, height))
            new_width = int(width * scale)
            new_height = int(height * scale)
            image = image.resize((new_width, new_height))
            print(f"DEBUG - [Navcam] Resized image to {new_width}x{new_height}")
        else:
            print("DEBUG - [Navcam] Image size is within limits")
        
        # Build prompt for navigation directions
        question = DEFAULT_IMAGE_TOKEN + "\nBased on this first person view image, where can I move? Answer with only one of the following letters: W = forward, A = Turn Left, S = backwards, D = turn right, E = End Movement (Stop)."
        # question = DEFAULT_IMAGE_TOKEN + "\nAnswer with one of: W, A, S, D, E where W = forward, A = turn left , S = backwards, D = turn right and E = stop. Based on this image, can I drive forward? if not, should I turn left, or right, or reverse or stop?"
        print(f"DEBUG - [Navcam] Question: {question}")

        image_tensor = process_images([image], image_processor, model.config)
        image_tensor = [_image.to(dtype=torch.float16, device=device) for _image in image_tensor]

        conv_template = "qwen_2"
        conv = copy.deepcopy(conv_templates[conv_template])
        conv.append_message(conv.roles[0], question)
        conv.append_message(conv.roles[1], None)
        prompt_question = conv.get_prompt()
        print(f"DEBUG - [Navcam] Prompt: {prompt_question}")

        input_ids = tokenizer_image_token(prompt_question, tokenizer, IMAGE_TOKEN_INDEX, return_tensors="pt").unsqueeze(0).to(device)
        image_sizes = [image.size]
        print(f"DEBUG - [Navcam] Image sizes: {image_sizes}")

        cont = model.generate(
            input_ids,
            images=image_tensor,
            image_sizes=image_sizes,
            do_sample=False,
            temperature=0,
            max_new_tokens=16,
        )

        text_outputs = tokenizer.batch_decode(cont, skip_special_tokens=True)
        print("DEBUG - [Navcam] Model output:", text_outputs)

        result_text = text_outputs[0].strip().upper()
        # Look for one of the expected navigation commands: W, A, S, D.
        for cmd in ["W", "A", "S", "D"]:
            if cmd in result_text:
                result = cmd
                break
        else:
            result = "STOP"  # Fallback: if no clear command, reply "STOP"

        print("DEBUG - [Navcam] Final navigation result:", result)
        return result
    except Exception as e:
        print("DEBUG - [Navcam] Error processing navcam image:", e)
        return None

# ------------------------------
# 3. MQTT Message Callbacks
# ------------------------------

def on_message(client, userdata, msg):
    global model_busy, objective
    topic = msg.topic
    payload = msg.payload.decode("utf-8")
    print(f"DEBUG - Received message on topic {topic}")

    # Update objective if received
    if topic == TOPIC_COMMAND_OBJECTIVE:
        objective = payload
        print(f"DEBUG - Updated objective to: {objective}")

    # Process image from the ROV camera topic (object detection)
    elif topic == TOPIC_ROV_CAMERA:
        with busy_lock:
            if model_busy:
                print("DEBUG - Model is busy (camera), publishing BUSY")
                client.publish(TOPIC_FOG_AI_STATUS, "BUSY")
                client.publish(TOPIC_FOG_RESULT, "BUSY")
                return
            else:
                model_busy = True

        client.publish(TOPIC_FOG_AI_STATUS, "BUSY")
        client.publish(TOPIC_FOG_RESULT, "BUSY")

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

    # Process image from the ROV navigation camera topic (for driving directions)
    elif topic == TOPIC_ROV_NAVCAM:
        with busy_lock:
            if model_busy:
                print("DEBUG - Model is busy (navcam), publishing BUSY")
                client.publish(TOPIC_FOG_NAVDIR, "BUSY")
                return
            else:
                model_busy = True

        client.publish(TOPIC_FOG_AI_STATUS, "BUSY")
        client.publish(TOPIC_FOG_NAVDIR, "BUSY")

        def navcam_processing_thread():
            global model_busy
            result = process_navcam_image(payload)
            if result is not None:
                client.publish(TOPIC_FOG_NAVDIR, result)
            else:
                client.publish(TOPIC_FOG_NAVDIR, "STOP")
            client.publish(TOPIC_FOG_AI_STATUS, "READY")
            with busy_lock:
                model_busy = False

        t = threading.Thread(target=navcam_processing_thread)
        t.start()

client.on_message = on_message

# ------------------------------
# 4. Start the MQTT Loop
# ------------------------------

client.loop_start()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("DEBUG - Exiting...")
finally:
    client.loop_stop()
    client.disconnect()

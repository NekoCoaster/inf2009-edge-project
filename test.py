# pip install git+https://github.com/LLaVA-VL/LLaVA-NeXT.git
from llava.model.builder import load_pretrained_model
from llava.mm_utils import get_model_name_from_path, process_images, tokenizer_image_token
from llava.constants import IMAGE_TOKEN_INDEX, DEFAULT_IMAGE_TOKEN, DEFAULT_IM_START_TOKEN, DEFAULT_IM_END_TOKEN, IGNORE_INDEX
from llava.conversation import conv_templates, SeparatorStyle

from PIL import Image
import requests
import copy
import torch
import warnings
import time

warnings.filterwarnings("ignore")

pretrained = "lmms-lab/llava-onevision-qwen2-7b-ov-chat"
model_name = "llava_qwen"
device = "cuda"
device_map = "cuda"

print("DEBUG - Loading pretrained model")
tokenizer, model, image_processor, max_length = load_pretrained_model(pretrained, None, model_name, device_map=device_map)

print("DEBUG - Setting model to eval()")
model.eval()

print("DEBUG - Downloading image")
#url = "https://github.com/haotian-liu/LLaVA/blob/1a91fc274d7c35a9b50b3cb29c4247ae5837ce39/images/llava_v1_5_radar.jpg?raw=true"
url = "https://images.pexels.com/photos/14543829/pexels-photo-14543829.jpeg"
image = Image.open(requests.get(url, stream=True).raw).convert("RGB").resize((360,360))

start_time = time.time()
print("DEBUG - Converting image to tensor")
image_tensor = process_images([image], image_processor, model.config)

print("DEBUG - Converting tensor to float16 on CUDA")
image_tensor = [_image.to(dtype=torch.float16, device=device) for _image in image_tensor]

conv_template = "qwen_2"
question = DEFAULT_IMAGE_TOKEN + "\nJust answer with 'Yes' or 'No'. Is there a Coca-Cola can in this image?"
print(f"DEBUG - Question set to: {question}")

print("DEBUG - Performing deep copy of conversation template")
conv = copy.deepcopy(conv_templates[conv_template])

print("DEBUG - Appending messages")
conv.append_message(conv.roles[0], question)
conv.append_message(conv.roles[1], None)

print("DEBUG - Getting prompt from conversation")
prompt_question = conv.get_prompt()

print("DEBUG - Tokenizing input")
input_ids = tokenizer_image_token(prompt_question, tokenizer, IMAGE_TOKEN_INDEX, return_tensors="pt").unsqueeze(0).to(device)

image_sizes = [image.size]
print(f"DEBUG - Image sizes: {image_sizes}")

print("DEBUG - Calling model.generate()")
cont = model.generate(
    input_ids,
    images=image_tensor,
    image_sizes=image_sizes,
    do_sample=False,
    temperature=0,
    max_new_tokens=16,
)

print("DEBUG - Decoding generated tokens")
text_outputs = tokenizer.batch_decode(cont, skip_special_tokens=True)

print("DEBUG - Output:")
print(text_outputs)

end_time = time.time()
print(f"DEBUG - Time taken: {end_time - start_time:.2f} seconds")

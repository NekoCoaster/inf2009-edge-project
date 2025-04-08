#!/bin/bash
# Clone the LLaVA-NeXT repository
git clone https://github.com/LLaVA-VL/LLaVA-NeXT.git
cd LLaVA-NeXT

# Create a new conda environment "llava_next" with Python 3.10 and install it non-interactively
conda create -n llava_next python=3.10 -y

# Activate the new environment
conda activate llava_next

# Upgrade pip (which enables PEP 660 support) and install the package in editable mode.
pip install --upgrade pip
pip install -e ".[train]"  # Note: You might need to repeat this command due to occasional CRC-32 errors.
pip install flash-attn==2.7.3 --no-build-isolation

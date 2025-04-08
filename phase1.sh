#!/bin/bash
# Update and upgrade system packages
sudo apt update && sudo apt upgrade -y

# Install Python 3.10 and necessary development packages
# sudo apt install -y python3.10 python3.10-venv python3.10-distutils python3.10-dev

# Download and install CUDA for WSL-Ubuntu
wget https://developer.download.nvidia.com/compute/cuda/repos/wsl-ubuntu/x86_64/cuda-wsl-ubuntu.pin
sudo mv cuda-wsl-ubuntu.pin /etc/apt/preferences.d/cuda-repository-pin-600
wget https://developer.download.nvidia.com/compute/cuda/12.1.0/local_installers/cuda-repo-wsl-ubuntu-12-1-local_12.1.0-1_amd64.deb
sudo dpkg -i cuda-repo-wsl-ubuntu-12-1-local_12.1.0-1_amd64.deb
sudo cp /var/cuda-repo-wsl-ubuntu-12-1-local/cuda-*-keyring.gpg /usr/share/keyrings/
sudo apt-get update
sudo apt-get -y install cuda

# Add CUDA environment variables to .bashrc and source it
echo 'export CUDA_HOME=/usr/local/cuda' >> ~/.bashrc
echo 'export PATH=$CUDA_HOME/bin:$PATH' >> ~/.bashrc
echo 'export LD_LIBRARY_PATH=$CUDA_HOME/lib64:$LD_LIBRARY_PATH' >> ~/.bashrc
source ~/.bashrc

# Download the Miniconda installer
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh

# Run the installer in batch mode (-b) with installation prefix (-p)
bash Miniconda3-latest-Linux-x86_64.sh -b -p $HOME/miniconda3

# Initialize conda for bash (this updates your ~/.bashrc)
$HOME/miniconda3/bin/conda init bash

# Source the updated .bashrc so that the conda command becomes available in this shell
source ~/.bashrc

# Configure conda to automatically activate the base environment at shell startup
conda config --set auto_activate_base true

# Optionally, source .bashrc again to ensure the settings take effect
source ~/.bashrc

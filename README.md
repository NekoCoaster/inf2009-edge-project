# inf2009-edge-project

Requires Python 3.10
Uses Cuda 12.1

VLM Repo: https://huggingface.co/lmms-lab/llava-onevision-qwen2-7b-ov-chat
Model link: https://huggingface.co/lmms-lab/llava-onevision-qwen2-7b-ov-chat

Partially reconstructed commands used to setting up the venvironment required to run the model:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3.10 python3.10-venv python3.10-distutils python3.10-dev
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1
curl -sS https://bootstrap.pypa.io/get-pip.py | python3.10
sudo ln -s /usr/local/bin/pip3.10 /usr/bin/pip3
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc


wget https://developer.download.nvidia.com/compute/cuda/repos/wsl-ubuntu/x86_64/cuda-wsl-ubuntu.pin
sudo mv cuda-wsl-ubuntu.pin /etc/apt/preferences.d/cuda-repository-pin-600
wget https://developer.download.nvidia.com/compute/cuda/12.1.0/local_installers/cuda-repo-wsl-ubuntu-12-1-local_12.1.0-1_amd64.deb
sudo dpkg -i cuda-repo-wsl-ubuntu-12-1-local_12.1.0-1_amd64.deb
sudo cp /var/cuda-repo-wsl-ubuntu-12-1-local/cuda-*-keyring.gpg /usr/share/keyrings/
sudo apt-get update
sudo apt-get -y install cuda


export CUDA_HOME=/usr/local/cuda
export PATH=$CUDA_HOME/bin:$PATH
export LD_LIBRARY_PATH=$CUDA_HOME/lib64:$LD_LIBRARY_PATH

wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh



git clone https://github.com/LLaVA-VL/LLaVA-NeXT.git

<restart terminal>

cd LLaVA-NeXT

conda create -n llava python=3.10 -y
conda activate llava
pip install --upgrade pip  # Enable PEP 660 support.
pip install git+https://github.com/LLaVA-VL/LLaVA-NeXT.git
pip install packaging
pip install setuptools
pip install --upgrade setuptools
pip install --upgrade requests huggingface_hub idna certifi yaml
pip install -e ".[train]"
```

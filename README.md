# Description

This project consists of testing a RAG.

# Setup

## Python3.11 virtual environment creation (Windows)
```bash
python.exe -m venv py_311
.\py_311\Scripts\activate
python --version
```

## Python3.11 virtual environment creation (Linux)
```bash
python3.11 -m venv py_311
source ./py_311/bin/activate
python3.11 --version
```

## Dependencies installation
```bash
pip install --upgrade pip
pip install --upgrade setuptools
pip install --upgrade wheel
pip install -r ./requirements.txt
```

# Dataset generation & Training
## Openimages backgrounds download
```bash
python3.11 ./src/scripts/rag-sample.py
```
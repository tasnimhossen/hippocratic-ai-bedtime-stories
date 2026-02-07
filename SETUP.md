# SETUP

## Local setup (recommended)

### 1) Create a virtual environment (optional)
```bash
python -m venv .venv
source .venv/bin/activate
```

### 2) Install deps
```bash
pip install -r requirements.txt
```

### 3) Set your API key (do NOT commit it)
```bash
export OPENAI_API_KEY="YOUR_KEY_HERE"
```

### 4) Run
```bash
python main.py
```

## Offline (no key)
```bash
export USE_MOCK=true
python main.py
```

## Google Colab
- Store the key as a Colab secret named `OPENAI_API_KEY`
- In a notebook cell:
```python
import os
from google.colab import userdata
os.environ["OPENAI_API_KEY"] = userdata.get("OPENAI_API_KEY")
```
Then run the script.

import os
import json
from datetime import datetime

def init_logs(company):
    base = os.path.join("logs", company)
    os.makedirs(base, exist_ok=True)
    os.makedirs(os.path.join(base, "raw_ai"), exist_ok=True)
    return base

def append_log(company, message):
    base = os.path.join("logs", company)
    os.makedirs(base, exist_ok=True)
    with open(os.path.join(base, "execution.log"), "a", encoding="utf-8") as f:
        f.write(f"{datetime.now()} | {message}\n")

def log_json(company, filename, data):
    base = os.path.join("logs", company)
    os.makedirs(base, exist_ok=True)
    with open(os.path.join(base, filename), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def log_text(company, filename, content):
    base = os.path.join("logs", company)
    os.makedirs(base, exist_ok=True)
    with open(os.path.join(base, filename), "w", encoding="utf-8") as f:
        f.write(content)
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import escape
import torch
from transformers import DistilBertTokenizerFast, DistilBertForSequenceClassification
import pickle
import json
import random
import logging
import os

# Database functions
from database import (
    store_conversation, get_user_history,
    store_user_details, get_user_name,
    get_user_preferences, store_journal_entry,
    get_journal_entries
)

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Load model
model_path = "distilbert_model"
MODEL_ZIP_PATH = "distilbert_model.zip"
URL = "https://drive.google.com/drive/folders/1MmMiuz05pNX6UEoJ4GloNmSEfrBJlCKR?usp=drive_link"

if not os.path.exists(model_path):
    print("Downloading model...")
    os.system(f"gdown --folder https://drive.google.com/drive/folders/1MmMiuz05pNX6UEoJ4GloNmSEfrBJlCKR?usp=drive_link/{URL} -O {MODEL_FOLDER}")
    gdown.download(MODEL_ZIP_PATH, quiet=False)

    print("Extracting model...")
    with zipfile.ZipFile(MODEL_ZIP_PATH, 'r') as zip_ref:
        zip_ref.extractall(MODEL_FOLDER)

    print("Model ready.")
tokenizer = DistilBertTokenizerFast.from_pretrained(model_path)
model = DistilBertForSequenceClassification.from_pretrained(model_path)

# Label encoder
with open(os.path.join(model_path, "label_encoder.pkl"), "rb") as f:
    label_encoder = pickle.load(f)

# Intent responses
with open("dataset.json", "r") as f:
    data = json.load(f)
responses = {intent["tag"]: intent["responses"] for intent in data["intents"]}

@app.route("/")
def home():
    return "✅ Mental health chatbot with relaxation tools is running."

def get_chatbot_response(user_message, user_id):
    """Use DistilBERT to classify and generate a response."""
    inputs = tokenizer(user_message, padding=True, truncation=True, return_tensors="pt")
    with torch.no_grad():
        outputs = model(**inputs)
    predicted_class = torch.argmax(outputs.logits, dim=1).item()
    tag = label_encoder.classes_[predicted_class]

    # Custom relaxation and journaling handling
    if tag == "relaxation" or "breathing" in user_message.lower():
        return "Let's do a breathing exercise. Focus all your attention on your breathing. Breathe in deeply through your nose, hold for a moment, and breathe out slowly. Repeat this for a few minutes.", tag
    elif tag == "journaling":
        return "Please take a moment to write down your thoughts. How are you feeling right now?", tag

    return random.choice(responses.get(tag, ["I'm here for you. Tell me more."])), tag

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_id = escape(data.get("user_id", "guest").strip())
    user_message = escape(data.get("message", "").strip())

    if not user_message:
        bot_message = "Hello, I'm Dr. SYNO. How are you feeling today?"
        store_conversation(user_id, user_message, bot_message)
        return jsonify({"bot_message": bot_message})

    if "my name is" in user_message.lower():
        name = user_message.lower().split("my name is")[-1].strip().split(" ")[0]
        store_user_details(user_id, name)

    bot_message, tag = get_chatbot_response(user_message, user_id)

    if not tag:
        tag = "default"

    tool = None
    if "[tool:" in bot_message:
        start = bot_message.find("[tool:") + len("[tool:")
        end = bot_message.find("]", start)
        tool = bot_message[start:end]
        bot_message = bot_message.replace(f"[tool:{tool}]", "").strip()

    store_conversation(user_id, user_message, bot_message)
    return jsonify({"bot_message": bot_message, "tool": tool, "tag": tag})

@app.route("/store_user", methods=["POST"])
def store_user():
    data = request.json
    user_id = escape(data.get("user_id", "guest").strip())
    name = escape(data.get("name", "").strip())
    email = escape(data.get("email", "").strip())
    preferences = data.get("preferences", {})

    if not all([user_id, name, email]):
        return jsonify({"status": "failure", "message": "Missing fields"}), 400

    try:
        store_user_details(user_id, name, email, preferences)
        return jsonify({"status": "success"}), 200
    except Exception as e:
        logging.error(f"User store error: {e}")
        return jsonify({"status": "failure", "message": str(e)}), 500

@app.route("/store_message", methods=["POST"])
def store_message():
    data = request.json
    user_id = escape(data.get("user_id", "guest").strip())
    user_message = escape(data.get("user_message", "").strip())
    bot_message = escape(data.get("bot_message", "").strip())

    if not user_message or not bot_message:
        return jsonify({"status": "failure", "message": "Invalid input"}), 400

    try:
        store_conversation(user_id, user_message, bot_message)
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"status": "failure", "message": str(e)}), 500

@app.route("/journal", methods=["POST"])
def save_journal():
    data = request.json
    user_id = escape(data.get("user_id", "guest").strip())
    entry = escape(data.get("entry", "").strip())

    if not entry:
        return jsonify({"status": "failure", "message": "Entry required"}), 400

    try:
        store_journal_entry(user_id, entry)
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"status": "failure", "message": str(e)}), 500

@app.route("/journal", methods=["GET"])
def get_journals():
    user_id = escape(request.args.get("user_id", "guest").strip())
    try:
        entries = get_journal_entries(user_id)
        return jsonify({"entries": entries}), 200
    except Exception as e:
        return jsonify({"status": "failure", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

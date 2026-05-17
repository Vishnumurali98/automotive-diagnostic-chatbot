
import os
import random
import json
import re
import time
from flask import Flask, request, jsonify, render_template
from google import genai
from dotenv import load_dotenv
from rag_engine import retrieve_context

# Load environment variables
load_dotenv()

# Initialize Gemini client
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

app = Flask(__name__)

#----------
# LOAD DATA
# --------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

INTENTS_PATH = os.path.join(BASE_DIR, "intents.json")

with open(INTENTS_PATH, "r", encoding="utf-8") as f:
    knowledge_base = json.load(f)
    intents_data = knowledge_base["intents"]

# --------------
# GLOBAL MEMORY
# --------------
response_cache = {}
chat_history = []

# Modes & flows
diagnose_mode = False
last_intent = None
service_step = None
service_data = {}

# ------------------
# HOME PAGE
# ---------------
@app.route('/')
def index():
    return render_template("index.html")

# ---------------------
# SET MODE
# -------------------
@app.route('/set_mode', methods=['POST'])
def set_mode():
    global diagnose_mode, last_intent, service_step

    data = request.json

    if data.get("mode") == "diagnose":
        diagnose_mode = True

    if data.get("mode") == "service":
        last_intent = "service_booking"
        service_step = "ask_date"

    return jsonify({"status": "ok"})

# ---------------------
# RESET CHAT
# -----------------------
@app.route('/reset', methods=["POST"])
def reset_chat():
    global last_intent, service_step, service_data, chat_history, diagnose_mode

    last_intent = None
    service_step = None
    service_data = {}
    chat_history = []
    diagnose_mode = False

    return jsonify({"reset": "successful"})

# --------------------
# TEXT CLEANING
# --------------------
def clean_text(text):
    return re.sub(r"[^\w\s]", "", text.lower())

# -------------------------
# SIMILARITY
# ------------------------
def similarity_score(user_msg, pattern):
    user_words = set(user_msg.split())
    pattern_words = set(pattern.split())
    return len(user_words & pattern_words) / max(len(pattern_words), 1)

# -------------------------
# FIND INTENT
# ------------------------
def find_best_intent(user_msg):
    user_msg = clean_text(user_msg)

    best_score = 0
    best_intent = None

    for intent in intents_data:
        for pattern in intent["patterns"]:
            score = similarity_score(user_msg, clean_text(pattern))
            if score > best_score:
                best_score = score
                best_intent = intent

    return best_intent, best_score

# ---------------------------
# RAG + GEMINI
# -----------------------------
def ask_gemini(user_message):
    print("\n--- RAG RETRIEVAL ---")
    print(f"Query sent to retriever: {user_message}")

    retrieved_docs = retrieve_context(user_message)

    print("Retrieved Documents:")
    for i, doc in enumerate(retrieved_docs):
        print(f"{i + 1}. {doc[:100]}...")

        print("\n--- GEMINI GENERATION ---")
        print("Sending structured prompt to Gemini...")
    context = "\n\n".join(retrieved_docs)

    history_text = "\n".join([
        f"{c['role']}: {c['message']}" for c in chat_history[-5:]
    ])

    prompt = f"""
You are an intelligent automotive diagnostic assistant.

Use the provided automotive documentation.

Provide:
1. Explanation
2. Causes
3. Safety advice
4. Next steps

Also clearly mention which system this issue belongs to.

Conversation history:
{history_text}

Context:
{context}

User question:
{user_message}
"""

    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=prompt
    )

    return response.text.strip()

# -------------------------
# MAIN CHAT
# -------------------------
@app.route('/message', methods=['POST'])
def chatting():
    global last_intent, service_step, service_data, chat_history, diagnose_mode

    user_message = request.json.get("message", "").strip()

    if not user_message:
        return jsonify({"reply": "Please describe your vehicle issue."})

    clean_msg = clean_text(user_message)

    # Save user message
    chat_history.append({"role": "user", "message": user_message})

    # -------------------------
    # CACHE
    # --------------------------
    if clean_msg in response_cache:
        print("\n--- CACHE HIT ---")
        print(f"User Query: {user_message}")
        return jsonify({
            "reply": response_cache[clean_msg],
            "source": "cache",
            "confidence": 1.0
        })

    # -------------------------
    # SERVICE FLOW
    # -----------------------
    if last_intent == "service_booking":

        print("\n--- SERVICE FLOW ---")
        print(f"Current Step: {service_step}")
        print(f"User Input: {user_message}")
        if service_step == "ask_date":
            print("Step: Asking Date")
            valid_months = [
                "jan", "feb", "mar", "apr", "may", "jun",
                "jul", "aug", "sep", "oct", "nov", "dec"
            ]

            if not any(m in user_message.lower() for m in valid_months):
                print("Invalid date entered")
                return jsonify({
                    "reply": "Please enter a valid date.",
                    "source": "service_flow",
                    "confidence": 1.0
                })

            service_data["date"] = user_message
            service_step = "ask_location"

            return jsonify({
                "reply": "Please provide your location.",
                "source": "service_flow",
                "confidence": 1.0
            })

        elif service_step == "ask_location":
            print("Step: Asking Location")
            if len(user_message) < 3 or user_message.lower() in ["hi", "hello", "ok"]:
                print("Invalid location entered")
                return jsonify({
                    "reply": "Please enter a valid location.",
                    "source": "service_flow",
                    "confidence": 1.0
                })

            service_data["location"] = user_message

            print("Service Booking Completed")
            print(f"Date: {service_data['date']}")
            print(f"Location: {service_data['location']}")

            reply = (
                "✅ Service Confirmed!\n\n"
                f"📅 Date: {service_data['date']}\n"
                f"📍 Location: {service_data['location']}\n\n"
                "Our team will contact you shortly."
            )

            last_intent = None
            service_step = None
            service_data = {}

            return jsonify({
                "reply": reply,
                "source": "service_flow",
                "confidence": 1.0
            })

    # -------------------------
    # INTENT DETECTION
    #---------------------------
    intent, confidence = find_best_intent(user_message)
    print("\n--- INTENT DETECTION ---")
    print(f"User Query: {user_message}")
    print(f"Detected Intent: {intent['tag'] if intent else 'None'}")
    print(f"Confidence Score: {confidence:.2f}")
    # -------------------------
    # HANDLE GREETING FIRST
    # --------------------------
    INTENT_THRESHOLD = 0.7
    simple_intents = ["greeting", "goodbye", "thank_you"]

    if intent and confidence >= INTENT_THRESHOLD and intent["tag"] in simple_intents:
        reply = random.choice(intent["responses"])
        return jsonify({
            "reply": reply,
            "source": "knowledge_base",
            "confidence": confidence
        })

    # ----------------------
    # VALIDATION
    # -------------------------
    words = user_message.lower().split()

    invalid_words = ["hi", "hello", "ok", "test"]

    def is_gibberish(text):
        return len(set(text)) <= 3

    if (
        len(user_message) < 3
        or not any(char.isalpha() for char in user_message)
        or user_message.lower() in invalid_words
        or is_gibberish(user_message)
        or (len(words) == 1 and len(words[0]) < 4)
    ):
        return jsonify({
            "reply": "I didn’t understand your issue. Please describe your vehicle problem clearly.",
            "source": "validation",
            "confidence": 1.0
        })

    # -------------------------
    # SERVICE INTENT TRIGGER
    # ------------------------
    if intent and intent["tag"] == "service_booking":
        last_intent = "service_booking"
        service_step = "ask_date"

        return jsonify({
            "reply": "📅 Please provide your preferred service date.",
            "source": "service_flow",
            "confidence": 1.0
        })

    # ---------------------------
    # FORCE RAG MODE (DIAGNOSE)
    # --------------------------
    if diagnose_mode:
        try:
            time.sleep(1.5)
            reply = ask_gemini(user_message)
            source = "rag_gemini"
        except Exception as e:
            print("Error:", e)
            reply = "I'm having trouble analysing that issue. Please try again."
            source = "error"

        chat_history.append({"role": "bot", "message": reply})

        return jsonify({
            "reply": reply,
            "source": source,
            "confidence": 1.0
        })

    # -------------------------
    # NORMAL FLOW
    # ------------------------
    try:
        time.sleep(1.5)
        reply = ask_gemini(user_message)
        source = "rag_gemini"
    except Exception as e:
        print("Error:", e)
        reply = "I'm having trouble analysing that issue."
        source = "error"

    chat_history.append({"role": "bot", "message": reply})
    response_cache[clean_msg] = reply

    print("\n--- FINAL RESPONSE ---")
    print(f"Source: {source}")
    print(f"Confidence: {confidence:.2f}")
    print(f"User Message: {user_message}")
    print("Response Generated Successfully\n")

    return jsonify({
        "reply": reply,
        "source": source,
        "confidence": round(confidence, 2)
    })


# ----------------------
# RUN
# ----------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=5000)
# -------end---------

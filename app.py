from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import json
import requests
import time

app = Flask(__name__)
CORS(app)

# Define greetings and farewells
greeting_keywords = ["hi", "hello", "hey", "hii", "good morning", "good afternoon", "good evening"]
farewell_keywords = ["bye", "goodbye", "see you", "see ya", "thank you", "thanks", "ok bye", "bye bye"]

# Load model and FAISS index
model = SentenceTransformer('paraphrase-MiniLM-L6-v2')
index = faiss.read_index("missions.index")

# Load mission data
with open("mission_data.json", "r", encoding="utf-8") as f:
    mission_json = json.load(f)
    mission_data = [item["details"] for item in mission_json]

# Load custom responses (optional)
with open("custom_responses.json", "r", encoding="utf-8") as f:
    custom_data = json.load(f)
    custom_greetings = custom_data.get("greetings", {})

# Per-user memory
user_memory = {}

# Embedding generation
def generate_embeddings(query):
    return model.encode([query])

# FAISS search
def search_in_faiss(query, k=1):
    query_embedding = generate_embeddings(query)
    query_embedding = np.array(query_embedding).astype('float32')
    D, I = index.search(query_embedding, k=1)
    return I[0], D[0]

# Summarize response using Ollama (LLM)
def summarize_with_ollama(context, user_query, memory):
    try:
        extended_context = (memory.get("last_context", "") + "\n\n" + context).strip()[:600]
        prompt = f"""You are a helpful assistant for the Indian Space Science Data Centre (ISSDC).
Answer the user's question based only on the mission-related context below.
Avoid unnecessary repetition and be concise.

### Context:
{extended_context}

### Previous Question:
{memory.get("last_question", "")}

### Current Question:
{user_query}

### Answer:"""

        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "phi",
                "prompt": prompt,
                "stream": False
            },
            timeout=60
        )
        response.raise_for_status()
        result = response.json()
        return result.get("response", "⚠️ Model response missing or malformed.")
    except Exception as e:
        return f"⚠️ Error: {str(e)}"

# Chat logic with memory
def generate_response(query, session_id):
    query_lower = query.lower().strip()
    memory = user_memory.setdefault(session_id, {"last_context": "", "last_question": ""})

    if query_lower in greeting_keywords:
        return (
            "👋 Hello! How can I assist you today?<br><br>"
            "I can help you with:<br>"
            "<button onclick=\"handleButton('Space Missions')\">🚀 Space Missions</button><br>"
            "<button onclick=\"handleButton('Data Access')\">🛰️ Data Access</button><br>"
            "<button onclick=\"handleButton('More Help')\">❓ More Help</button><br>"
            "<br>Or feel free to type your question below. 📩",
            "N/A"
        )

    if query_lower in farewell_keywords:
        return "👋 You're welcome! Have a great day! 🌟", "N/A"

    I, D = search_in_faiss(query_lower)
    retrieved_data = [mission_data[i] for i in I]
    combined_context = "\n\n".join(retrieved_data).strip()[:1000]

    memory["last_context"] = combined_context
    memory["last_question"] = query
    answer = summarize_with_ollama(combined_context, query, memory)
    return answer, combined_context

# Web routes
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    start_time = time.time()
    data = request.get_json(force=True)
    user_query = data.get("message", "")
    query_cleaned = user_query.strip().lower()

    if query_cleaned in greeting_keywords:
        response = "Hi! How can I assist you today?"
        context = "N/A"
    elif query_cleaned in farewell_keywords:
        response = "👋 You're welcome! Have a great day! 🌟"
        context = "N/A"
    else:
        indices, distances = search_in_faiss(user_query)
        index_id = indices[0]
        distance = distances[0]
        similarity_score = 1 - distance

        THRESHOLD = 0.75
        if similarity_score < THRESHOLD:
            response = "Sorry, I couldn't find information about that mission."
            context = "N/A"
        else:
            matched_mission = mission_data[index_id]
            response = matched_mission
            context = matched_mission

    response_time = round(time.time() - start_time, 2)

    return jsonify({
        "response": response,
        "context": context,
        "response_time": response_time
    })

@app.route("/ask", methods=["POST"])
def ask():
    try:
        data = request.get_json(force=True)
        user_message = data.get("message", "")
        session_id = data.get("session_id", "default_user")
        if not user_message:
            return jsonify({"error": "No message received"}), 400

        start_time = time.time()
        response_text, context = generate_response(user_message, session_id)
        end_time = time.time()

        response_time = round(end_time - start_time, 2)

        return jsonify({
            "response": response_text,
            "context": context,
            "response_time": response_time
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)

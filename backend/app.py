from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app)

# Rasa sunucusu adresi
RASA_URL = "http://127.0.0.1:5005/webhooks/rest/webhook"

# Chat endpoint
@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    message = data.get("message", "")
    sender_id = data.get("sender_id", "user")  # Varsayılan: user

    print(f"[{sender_id}] Gelen mesaj: {message}")

    if not message:
        return jsonify({"response": "Lütfen bir mesaj girin."})

    try:
        rasa_response = requests.post(RASA_URL, json={"sender": sender_id, "message": message})
        print(f"[RASA STATUS] {rasa_response.status_code}")
        print(f"[RASA RESPONSE] {rasa_response.text}")
    except Exception as e:
        print(f"[HATA] Rasa'ya istek atılamadı: {str(e)}")
        return jsonify({"response": "❗ Rasa sunucusuna erişilemedi."})

    if rasa_response.status_code == 200:
        messages = rasa_response.json()
        if messages:
            first = messages[0]
            response_text = first.get("text") or first.get("custom", {}).get("text", "")
            pdf_filename = first.get("custom", {}).get("pdf")

            return jsonify({
                "response": response_text,
                "pdf": pdf_filename
            })
        else:
            return jsonify({"response": "❗ Yanıt alınamadı."})
    else:
        return jsonify({"response": "❗ Rasa sunucusuna erişilemedi."})

# PDF servis endpointi
@app.route("/pdfs/<filename>")
def serve_pdf(filename):
    return send_from_directory("pdfs", filename)

if __name__ == "__main__":
    app.run(port=8000)

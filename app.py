from flask import Flask, request, jsonify
from google.cloud import dialogflow_v2 as dialogflow
import os
import uuid

app = Flask(__name__)

# Ruta al archivo de credenciales
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "dialogflow_key.json"

# Nombre del proyecto (lo encuentras en tu archivo .json o en Google Cloud Console)
DIALOGFLOW_PROJECT_ID = "controlvoz-vwye"  # <-- reemplaza esto con el ID real

@app.route("/dialogflow", methods=["POST"])
def procesar_texto():
    data = request.get_json()
    texto = data.get("mensaje", "")

    if not texto:
        return jsonify({"error": "No se recibió ningún mensaje"}), 400

    session_id = str(uuid.uuid4())
    session_client = dialogflow.SessionsClient()
    session = session_client.session_path(DIALOGFLOW_PROJECT_ID, session_id)

    text_input = dialogflow.types.TextInput(text=texto, language_code="es")
    query_input = dialogflow.types.QueryInput(text=text_input)

    try:
        response = session_client.detect_intent(session=session, query_input=query_input)
        fulfillment_text = response.query_result.fulfillment_text
        return jsonify({"respuesta": fulfillment_text})
    except Exception as e:
        print("❌ Error:", e)
        return jsonify({"error": "No se pudo conectar a Dialogflow"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)


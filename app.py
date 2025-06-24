from flask import Flask, request, jsonify
from google.cloud import dialogflow_v2 as dialogflow
import os
import uuid

app = Flask(__name__)

# Ruta a tus credenciales de Dialogflow
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "dialogflow_key.json"

# Tu ID de proyecto en Dialogflow
DIALOGFLOW_PROJECT_ID = "controlvoz-vwye"  # <-- Asegúrate que esté correcto

# Estado simulado del foco
estado_foco = {
    "encendido": False
}

# Ruta principal: procesar mensaje desde Flutter
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
        action = response.query_result.action

        # Acciones personalizadas: encender o apagar
        if "encender" in action:
            estado_foco["encendido"] = True
        elif "apagar" in action:
            estado_foco["encendido"] = False

        return jsonify({
            "respuesta": fulfillment_text,
            "accion": action,
            "estado": estado_foco["encendido"]
        })

    except Exception as e:
        print("❌ Error:", e)
        return jsonify({"error": "No se pudo conectar a Dialogflow"}), 500

# Ruta para consultar el estado del foco
@app.route("/foco/estado", methods=["GET"])
def estado():
    return jsonify({"encendido": estado_foco["encendido"]})

# Ruta para encender el foco (puedes usarla manualmente o desde Flutter)
@app.route("/foco/encender", methods=["POST"])
def encender():
    estado_foco["encendido"] = True
    return jsonify({"mensaje": "Foco encendido", "encendido": True})

# Ruta para apagar el foco
@app.route("/foco/apagar", methods=["POST"])
def apagar():
    estado_foco["encendido"] = False
    return jsonify({"mensaje": "Foco apagado", "encendido": False})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

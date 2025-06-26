from flask import Flask, request, jsonify
from google.cloud import dialogflow_v2 as dialogflow
from tuya_connector import TuyaOpenAPI
import os
import uuid
import requests
import time
import hashlib
import hmac

app = Flask(__name__)

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "dialogflow_key.json"
DIALOGFLOW_PROJECT_ID = "controlvoz-vwye"  # <-- Asegúrate que esté correcto

ACCESS_ID = "ajyqpwwctqukna5rk3gr"
ACCESS_KEY = "31b4f4248afb495ca42113048c587715"
API_ENDPOINT = "https://openapi.tuyaus.com"
MQ_ENDPOINT = "wss://mqe.tuyaus.com:8285/"
DEVICE_ID = "eb0d182f5aac27e0bfwolo"

estado_foco = {
    "encendido": False
}

openapi = TuyaOpenAPI(API_ENDPOINT, ACCESS_ID, ACCESS_KEY)
openapi.connect()

COLOR_MAP = {
    "rojo": 0,
    "verde": 120,
    "azul": 240,
    "amarillo": 60,
    "rosado": 330,
    "violeta": 270
}

INTENSIDAD_MAP = {
    "baja": 20,
    "media": 500,
    "alta": 1000
}

def controlar_foco_real(encender=None, color=None, intensidad=None):
    comandos = []

    if encender is not None:
        comandos.append({"code": "switch_led", "value": encender})

    if intensidad and intensidad in INTENSIDAD_MAP:
        comandos.append({"code": "bright_value_v2", "value": INTENSIDAD_MAP[intensidad]})

    if color and color in COLOR_MAP:
        hue = COLOR_MAP[color]
        comandos.append({
            "code": "colour_data_v2",
            "value": {
                "h": hue,
                "s": 1000,
                "v": 1000
            }
        })

    if not comandos:
        print("⚠️ No hay comandos para enviar a Tuya.")
        return False

    try:
        response = openapi.post(f"/v1.0/iot-03/devices/{DEVICE_ID}/commands", {"commands": comandos})
        print("🔧 Tuya API response:", response)
        return response.get("success", False)
    except Exception as e:
        print("❌ Error enviando comando a Tuya:", e)
        return False

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
        parameters = response.query_result.parameters

        color = parameters.get("color")
        intensidad = parameters.get("intensidad")

        encender = None

        # 🔁 Procesar acciones desde Dialogflow
        if action in ["encender", "luces.encender"]:
            encender = True
            estado_foco["encendido"] = True
        elif action in ["apagar", "luces.apagar"]:
            encender = False
            estado_foco["encendido"] = False

        # Ejecutar comando
        controlar_foco_real(encender=encender, color=color, intensidad=intensidad)

        return jsonify({
            "respuesta": fulfillment_text,
            "accion": action,
            "estado": estado_foco["encendido"]
        })

    except Exception as e:
        print("❌ Error:", e)
        return jsonify({"error": "No se pudo conectar a Dialogflow"}), 500


# ✅ Consultar estado del foco
@app.route("/foco/estado", methods=["GET"])
def estado():
    return jsonify({"encendido": estado_foco["encendido"]})

# 🔘 Encender foco manualmente
@app.route("/foco/encender", methods=["POST"])
def encender():
    estado_foco["encendido"] = True
    controlar_foco_real(encender=True)
    return jsonify({"mensaje": "Foco encendido", "encendido": True})

# 🔌 Apagar foco manualmente
@app.route("/foco/apagar", methods=["POST"])
def apagar():
    estado_foco["encendido"] = False
    controlar_foco_real(encender=False)
    return jsonify({"mensaje": "Foco apagado", "encendido": False})

# ▶️ Ejecutar servidor
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
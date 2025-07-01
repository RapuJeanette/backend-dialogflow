import re
from flask import Flask, request, jsonify
from google.cloud import dialogflow_v2 as dialogflow
from tuya_connector import TuyaOpenAPI
import os
import uuid

app = Flask(__name__)

# Configuración de Dialogflow y Tuya
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "dialogflow_key.json"
DIALOGFLOW_PROJECT_ID = "controlvoz-vwye"

estado_foco = {
    "encendido": False,
    "color": None,   # p.ej. "azul"
    "intensidad": 100  # porcentaje 1-100
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

def controlar_foco_real(encender=None, color=None, intensidad=None):
    comandos = []

    # Actualizar estado si viene color/intensidad nuevos
    if color:
        estado_foco["color"] = color

    if intensidad is not None:
        try:
            intensidad = int(intensidad)
            intensidad = max(1, min(100, intensidad))
            estado_foco["intensidad"] = intensidad
        except:
            pass

    # Si hay color en estado, mandar modo color y color_data con brillo actual
    if estado_foco["color"]:
        comandos.append({"code": "work_mode", "value": "colour"})
        hue = COLOR_MAP.get(estado_foco["color"], 0)
        brillo_tuya = int((estado_foco["intensidad"] / 100) * 1000)
        comandos.append({
            "code": "colour_data_v2",
            "value": {
                "h": hue,
                "s": 1000,
                "v": brillo_tuya
            }
        })
    else:
        # Si no hay color (modo blanco), mandar solo brillo con bright_value_v2
        brillo_tuya = int((estado_foco["intensidad"] / 100) * 1000)
        comandos.append({"code": "bright_value_v2", "value": brillo_tuya})

    # Comando switch_led si viene
    if encender is not None:
        comandos.append({"code": "switch_led", "value": encender})
        estado_foco["encendido"] = encender

    if not comandos:
        print("⚠️ No hay comandos para enviar a Tuya.")
        return False

    print("📤 Enviando comandos a Tuya:", comandos)

    try:
        response = openapi.post(f"/v1.0/iot-03/devices/{DEVICE_ID}/commands", {"commands": comandos})
        print("🔧 Tuya API response:", response)
        return response.get("success", False)
    except Exception as e:
        print("❌ Error enviando comando a Tuya:", e)
        return False
    
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
        intensidad_raw = parameters.get("intensidad_porcentaje")
        print(f"DEBUG => intensidad_raw recibido: {intensidad_raw}")
        intensidad = None
        if isinstance(intensidad_raw, dict):
            intensidad = intensidad_raw.get("amount")
        elif isinstance(intensidad_raw, (int, float)):
            intensidad = intensidad_raw
        elif isinstance(intensidad_raw, str):
    # Extraer solo números del string
            numeros = re.findall(r'\d+', intensidad_raw)
            if numeros:
                intensidad = int(numeros[0])

        print(f"DEBUG => intensidad procesada: {intensidad}")

        if intensidad is not None:
            # Validar rango y pasar a string para tu función
            intensidad = max(1, min(100, int(intensidad)))

        encender = None

        if action in ["encender", "luces.encender"]:
            encender = True
            estado_foco["encendido"] = True

        elif action in ["apagar", "luces.apagar"]:
            encender = False
            estado_foco["encendido"] = False

        elif action == "luces.modificar_intensidad":
            encender = True
            estado_foco["encendido"] = True

        elif action == "luces.modificar_color":
            encender = True
            estado_foco["encendido"] = True

        elif action == "luces.modificar_completo":
            encender = True
            estado_foco["encendido"] = True

        elif action == "encenderluzcolor":
            encender = True
            estado_foco["encendido"] = True

        elif action == "encenderluzcolorintensidad":
            encender = True
            estado_foco["encendido"] = True

        elif action == "encenderluzintensidad":
            encender = True
            estado_foco["encendido"] = True

        print(f"DEBUG => acción: {action}, color: {color}, intensidad: {intensidad}, encender: {encender}")
        controlar_foco_real(encender=encender, color=color, intensidad=intensidad)

        return jsonify({
            "respuesta": fulfillment_text,
            "accion": action,
            "estado": estado_foco["encendido"]
        })

    except Exception as e:
        print("❌ Error:", e)
        return jsonify({"error": "No se pudo conectar a Dialogflow"}), 500

@app.route("/foco/estado", methods=["GET"])
def estado():
    return jsonify({"encendido": estado_foco["encendido"]})

@app.route("/foco/encender", methods=["POST"])
def encender():
    estado_foco["encendido"] = True
    controlar_foco_real(encender=True)
    return jsonify({"mensaje": "Foco encendido", "encendido": True})

@app.route("/foco/apagar", methods=["POST"])
def apagar():
    estado_foco["encendido"] = False
    controlar_foco_real(encender=False)
    return jsonify({"mensaje": "Foco apagado", "encendido": False})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

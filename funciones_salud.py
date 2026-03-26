# =====================================================================
# 0. INTERFAZ HTML DE CHAT PARA COLAB (SUSTITUYE A LOS PRINT)
# =====================================================================

from IPython.display import display, HTML

def interfaz_chat(texto, emisor="asistente"):
    """
    Sustituye a los print() para crear burbujas de chat visuales en la celda de Colab.
    Emisores: 'asistente', 'usuario', 'sistema', 'alerta'
    """
    # Limpiamos los saltos de línea básicos de consola a HTML
    texto = str(texto).replace('\n', '<br>')
    
    if emisor == "asistente":
        html = f"""<div style="background-color: #E3F2FD; border-radius: 15px; padding: 15px; margin: 10px 0; border-left: 5px solid #2196F3; font-family: Arial, sans-serif; max-width: 85%; box-shadow: 2px 2px 5px rgba(0,0,0,0.1);">
            <b style="color: #1565C0;">🩺 Asistente:</b><br><span style="font-size: 16px;">{texto}</span>
        </div>"""
    
    elif emisor == "usuario":
        html = f"""<div style="background-color: #F5F5F5; border-radius: 15px; padding: 15px; margin: 10px 0; border-right: 5px solid #4CAF50; font-family: Arial, sans-serif; max-width: 85%; margin-left: auto; text-align: right; box-shadow: 2px 2px 5px rgba(0,0,0,0.1);">
            <b style="color: #2E7D32;">👤 Tú:</b><br><span style="font-size: 16px;">{texto}</span>
        </div>"""
        
    elif emisor == "sistema":
        html = f"""<div style="background-color: #FFF3E0; border-radius: 10px; padding: 10px; margin: 10px auto; text-align: center; font-family: Arial, sans-serif; font-size: 13px; color: #E65100; max-width: 60%;">
            ⚙️ <i>{texto}</i>
        </div>"""
        
    elif emisor == "alerta":
        html = f"""<div style="background-color: #FFEBEE; border-radius: 10px; padding: 10px; margin: 10px auto; text-align: center; font-family: Arial, sans-serif; font-size: 14px; color: #C62828; border: 1px solid #EF9A9A;">
            ⚠️ <b>{texto}</b>
        </div>"""

    display(HTML(html))


# =====================================================================
# 1. FUNCIONES DE MEMORIA Y GESTIÓN DE DATOS
# =====================================================================
import os
import json

def cargar_memoria():
    if os.path.exists("memoria_salud.json"):
        with open("memoria_salud.json", "r") as f:
            return json.load(f)
    else:
        # Si no existe, creamos un perfil vacío
        perfil_vacio = {"nombre": None, "medicinas": [], "ultimas_adiciones": []}
        with open("memoria_salud.json", "w") as f:
            json.dump(perfil_vacio, f, indent=4)
        return perfil_vacio

def guardar_memoria(datos):
    with open("memoria_salud.json", "w") as f:
        json.dump(datos, f, indent=4)


# =====================================================================
# 2. FUNCIONES DE AUDIO (GRABACIÓN Y SÍNTESIS DE VOZ)
# =====================================================================
import asyncio
import edge_tts
from IPython.display import Audio, display
from google.colab import output
from base64 import b64decode

# Función para generar y reproducir el audio
async def generar_voz(texto, esperar=True, tiempo_extra=1.2):
    # Elegimos la voz: 'es-ES-ElviraNeural' (Mujer, España, muy clara)
    # O 'es-ES-AlvaroNeural' si prefieres hombre.
    VOICE = "es-ES-AlvaroNeural"
    OUTPUT_FILE = "respuesta_asistente.mp3"

    communicate = edge_tts.Communicate(texto, VOICE, rate="-10%") # rate="-10%" si la quieres más lenta
    await communicate.save(OUTPUT_FILE)

    # Reproducir en Colab
    display(Audio(OUTPUT_FILE, autoplay=True))

    # Calculamos el tiempo para no solapar audios
    if esperar:
        tiempo_estimado = (len(texto) * 0.1) + tiempo_extra
        await asyncio.sleep(tiempo_estimado)


# Código JavaScript para grabar audio desde el navegador
RECORD_JS = """
const sleep  = time => new Promise(resolve => setTimeout(resolve, time))
const b2text = blob => new Promise(resolve => {
  const reader = new FileReader()
  reader.onloadend = e => resolve(e.srcElement.result)
  reader.readAsDataURL(blob)
})
var record = time => new Promise(async resolve => {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
  const recorder = new MediaRecorder(stream)
  const chunks = []
  recorder.ondataavailable = e => chunks.push(e.data)
  recorder.start()
  await sleep(time)
  recorder.onstop = async ()=>{
    const blob = new Blob(chunks)
    const text = await b2text(blob)
    resolve(text)
  }
  recorder.stop()
})
"""

def grabar_audio(segundos=5):
    interfaz_chat(f"Escuchando durante {segundos} segundos...", emisor="sistema")
    output.eval_js(RECORD_JS)
    audio_b64 = output.eval_js(f"record({segundos*1000})")
    audio_bytes = b64decode(audio_b64.split(',')[1])
    with open("audio_usuario.wav", "wb") as f:
        f.write(audio_bytes)
    return "audio_usuario.wav"


# =====================================================================
# 3. FUNCIONES DE UTILIDAD (FECHAS)
# =====================================================================
from datetime import datetime

# función auxiliar para tener la fecha en español
def obtener_fecha_hoy_formato_json():
    # Diccionario con las abreviaturas exactas en español
    meses_abrev = [
        "ene", "feb", "mar", "abr", "may", "jun",
        "jul", "ago", "sep", "oct", "nov", "dic"
    ]

    hoy = datetime.now()

    # Formateamos el día para que siempre tenga 2 cifras (ej. 05 en vez de 5)
    dia = f"{hoy.day:02d}"
    mes = meses_abrev[hoy.month - 1]
    anio = hoy.year

    # Resultado final: ej. "26-mar-2026"
    return f"{dia}-{mes}-{anio}"


# =====================================================================
# 4. FUNCIONES DE PRESENTACIÓN E INTERACCIÓN
# =====================================================================
import asyncio

async def presentacion(memoria, model_whisper, model_texto, tokenizer_texto):
    if memoria.get("nombre") is None:
        texto_bienvenida = "¡Hola! Soy tu Asistente de Salud. Como es nuestra primera vez hablando, no sé nada de ti. Para poder ayudarte mejor... ¿cómo te llamas?"

        interfaz_chat(texto_bienvenida, emisor="asistente")
        await generar_voz(texto_bienvenida)  

        # Grabamos al usuario
        archivo_wav = grabar_audio(segundos=5)

        # 1. Transcribimos el audio con Whisper
        resultado = model_whisper.transcribe(
            archivo_wav, 
            language="es",
            no_speech_threshold=0.3, # si no detecta voz, que no intente transcribir nada
            condition_on_previous_text=False, #parametros antihistorial para que no se confunda con lo que ha dicho antes
            temperature=0.0 #parametro anti alucinaciones para que no invente palabras y se centre en lo que ha dicho el usuario
        )
        texto_bruto = resultado["text"].strip()
        interfaz_chat(f"{texto_bruto}", emisor="usuario")

        # 2. PROCESAMOS EL NOMBRE CON QWEN
        interfaz_chat("Procesando tu nombre...", emisor="sistema")

        # Preparamos el prompt estricto para extraer solo el nombre
        mensajes = [
            {"role": "system", "content": "Eres un asistente experto en extracción de entidades. Tu única tarea es leer una frase y devolver ÚNICAMENTE el nombre propio de la persona que se presenta. No añadas puntos, ni saludos, ni explicaciones. Solo la palabra del nombre."},
            {"role": "user", "content": f"Extrae el nombre de esta frase: '{texto_bruto}'"}
        ]

        # Tokenizamos y mandamos al modelo
        texto_prompt = tokenizer_texto.apply_chat_template(mensajes, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer_texto([texto_prompt], return_tensors="pt").to(model_texto.device)

        # Generamos la respuesta con temperature baja para mayor precisión
        outputs = model_texto.generate(**inputs, max_new_tokens=10, temperature=0.1)
        nombre_limpio = tokenizer_texto.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True).strip()

        interfaz_chat(f"Nombre extraído: '{nombre_limpio}'", emisor="sistema")
        # ========================================================

        #Guardamos el nombre limpio en memoria
        memoria["nombre"] = nombre_limpio
        guardar_memoria(memoria)

        texto_confirmacion = f"¡Perfecto, {memoria['nombre']}! He creado tu perfil. Ya podemos empezar con las consultas."
        interfaz_chat(texto_confirmacion, emisor="asistente")
        await generar_voz(texto_confirmacion)

        # RETORNAMOS LA MEMORIA ACTUALIZADA
        return memoria

    else:
        texto_retorno = f"¡Hola de nuevo, {memoria['nombre']}! ¿Qué hacemos hoy?"
        interfaz_chat(texto_retorno, emisor="asistente")
        await generar_voz(texto_retorno)
        return memoria


# =====================================================================
# 5. FUNCIONES DE PROCESAMIENTO VISUAL (RECETAS)
# =====================================================================
import torch
import re
import json
from qwen_vl_utils import process_vision_info

# Fijamos los números mínimo y máximo de  píxeles para la foto
MIN_PIXELS = 256 * 28 * 28
# Aumentamos el máximo a casi 1 millón de píxeles para que lea el texto nítido
MAX_PIXELS = 1280 * 28 * 28

def analizar_receta(ruta_imagen, memoria, model_vision, processor_vision):
    prompt = f"""
Extract prescription information from the image and return ONLY valid JSON.
The output must be in Spanish.

Format:
{{
  "lista_completa": [
    {{
      "nombre": "",
      "dosis": "",
      "fin": ""
    }}
  ],
  "adiciones": []
}}

Rules:
- Only JSON
- Escape all internal quotes
- All fields must be strings
- Keep Spanish text in output
- STRICTLY FORBIDDEN: Do not include info like legal texts, medical appointment reminders, prices, VAT/IVA, warnings about medicine accumulation, or prescription expiration info.
- "fin" = treatment end date

History (ignore for extraction):
{memoria.get('medicinas', [])}
"""

    mensajes = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": ruta_imagen},
                {"type": "text", "text": prompt},
            ],
        }
    ]

    try:
        interfaz_chat("El modelo de visión está leyendo la imagen...", emisor="sistema")

        text = processor_vision.apply_chat_template(mensajes, tokenize=False, add_generation_prompt=True)
        image_inputs, video_inputs = process_vision_info(mensajes)

        inputs = processor_vision(
            text=[text],
            images=image_inputs,
            videos=video_inputs,
            padding=True,
            return_tensors="pt",
            min_pixels=MIN_PIXELS,
            max_pixels=MAX_PIXELS
        ).to("cuda")

        with torch.no_grad():
            generated_ids = model_vision.generate(**inputs, max_new_tokens=1024)

        generated_ids_trimmed = [
            out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
        ]

        del inputs
        del generated_ids
        torch.cuda.empty_cache()

        texto_respuesta = processor_vision.batch_decode(
            generated_ids_trimmed,
            skip_special_tokens=True
        )[0].strip()

        # Extraer JSON
        match = re.search(r'\{.*\}', texto_respuesta, re.DOTALL)
        if not match:
            interfaz_chat("No hay JSON válido en la respuesta", emisor="alerta")
            interfaz_chat(texto_respuesta, emisor="sistema")
            return None

        json_text = match.group(0)

        # Escapar comillas internas
        json_text = re.sub(r'(\w)"(\w)', r'\1\\"\\2', json_text)

        datos_json = json.loads(json_text)

        lista = datos_json.get("lista_completa", [])
        adiciones = datos_json.get("adiciones", [])

        if not lista:
            return None

        return [lista, adiciones]

    except Exception as e:
        interfaz_chat(f"Error: {e}", emisor="alerta")
        return None


# =====================================================================
# 6. GESTIÓN DE MEDICAMENTOS (REGISTRO)
# =====================================================================
def registrar_en_memoria(nuevos_datos):
    memoria = cargar_memoria()
    memoria.setdefault('medicinas', [])
    memoria.setdefault('ultimas_adiciones', [])

    lista_nuevas = nuevos_datos[0]  # recetas extraídas
    ultimas_adiciones = []

    for receta in lista_nuevas:
        # Identificador único: nombre + dosis + fecha fin
        key = (receta['nombre'], receta['dosis'], receta['fin'])
        # comprobar si ya existe
        existe = any(
            (m['nombre'], m['dosis'], m['fin']) == key
            for m in memoria['medicinas']
        )
        if not existe:
            memoria['medicinas'].append(receta)
            ultimas_adiciones.append(receta)

    memoria['ultimas_adiciones'] = ultimas_adiciones

    guardar_memoria(memoria)
    return memoria

# =====================================================================
# 7. OPCIÓN 1: AÑADIR RECETAS
# =====================================================================
from google.colab import files

async def subir_receta(memoria, model_vision, processor_vision):
    texto_peticion = "Por favor, sube la foto de tu receta o medicina."
    interfaz_chat(texto_peticion, emisor="asistente")
    await generar_voz(texto_peticion)

    # Abre el selector de archivos de Colab
    await asyncio.sleep(1) # mini margen
    subido = files.upload()

    if subido:
        nombre_archivo = list(subido.keys())[0]

        interfaz_chat("Analizando imagen...", emisor="sistema")
        datos_extraidos = analizar_receta(nombre_archivo, memoria, model_vision, processor_vision)

        if datos_extraidos:
            # Guardamos en la memoria JSON
            memoria_actualizada = registrar_en_memoria(datos_extraidos)

            # Extraemos las últimas adiciones que sí se guardaron
            ultimas = memoria_actualizada.get('ultimas_adiciones', [])

            if ultimas:
                nombres = [med['nombre'] for med in ultimas]
                if len(nombres) == 1:
                    confirmacion = f"He leído y guardado correctamente: {nombres[0]}. Ya está en tu lista de recordatorios."
                else:
                    confirmacion = f"He leído y guardado correctamente: {', '.join(nombres[:-1])} y {nombres[-1]}. Ya están en tu lista de recordatorios."
            else:
                confirmacion = "No se han añadido nuevas medicinas; ya estaban en tu lista."

            interfaz_chat(confirmacion, emisor="asistente")
            await generar_voz(confirmacion)

            # Mostramos cómo queda la lista visualmente
            mostrar_recordatorios(memoria_actualizada)

            # Borramos el archivo tras procesarlo
            if os.path.exists(nombre_archivo):
                os.remove(nombre_archivo)
                interfaz_chat(f"Archivo temporal '{nombre_archivo}' eliminado.", emisor="sistema")

            return memoria_actualizada

        else:
            confirmacion = "He leído la información que me has proporcionado, y ya estaba introducida en el registro. Aquí tienes el registro y puedes comprobar que está todo en orden:"
            interfaz_chat(confirmacion, emisor="asistente")
            await generar_voz(confirmacion)

            # Mostramos cómo queda la lista visualmente
            mostrar_recordatorios(memoria)

            # Borramos el archivo tras procesarlo
            if os.path.exists(nombre_archivo):
                os.remove(nombre_archivo)
                interfaz_chat(f"Archivo temporal '{nombre_archivo}' eliminado.", emisor="sistema")

            return memoria

    await generar_voz("No se ha subido ninguna imagen.")
    return memoria

def mostrar_recordatorios(memoria):
    texto = "<b>--- TUS MEDICAMENTOS REGISTRADOS ---</b><br>"
    for m in memoria.get("medicinas", []):
        fin = m.get('fin', '')
        texto += f"💊 {m['nombre']} - {m['dosis']} - Fecha Fin: {fin}<br>"
    interfaz_chat(texto, emisor="sistema")


# =====================================================================
# 8. OPCIÓN 2: MODIFICAR Y ELIMINAR 
# =====================================================================

# AÑADIDO: Parámetro primera_vez
async def cambios_meds_menu(memoria, model_whisper, model_texto, tokenizer_texto, primera_vez=True):
    historial = memoria.get("medicinas", [])

    if not historial:
        interfaz_chat("No hay medicamentos registrados aún.", emisor="asistente")
        await generar_voz("No hay medicamentos registrados aún.")
        return memoria

    # Mostrar menú al usuario
    menu_pantalla = (
        "Diga el número de la opción que le interesa:\n"
        "1. Eliminar un medicamento\n"
        "2. Modificar un medicamento\n"
    )
    interfaz_chat(menu_pantalla, emisor="asistente")

    if primera_vez:
        texto_voz = menu_pantalla
    else:
        texto_voz = "Di 1 para eliminar un medicamento, o 2 para modificarlo."

    await generar_voz(texto_voz)

    # Escuchar respuesta
    archivo_audio = grabar_audio(segundos=5)
    resultado = model_whisper.transcribe(
            archivo_audio, 
            language="es",
            no_speech_threshold=0.3, # si no detecta voz, que no intente transcribir nada
            condition_on_previous_text=False, #parametros antihistorial para que no se confunda con lo que ha dicho antes
            temperature=0.0 #parametro anti alucinaciones para que no invente palabras y se centre en lo que ha dicho el usuario
        )
    eleccion_texto = resultado["text"].strip().lower()
    interfaz_chat(f"{eleccion_texto}", emisor="usuario")

    # Convertir respuesta a número de opción
    prompt_normalizar = f"""
    El usuario ha dicho: "{eleccion_texto}"

    Devuelve solo un número (1 o 2) que corresponde a la opción correcta:
    1 → Eliminar un medicamento
    2 → Modificar un medicamento

    Responde solo con el número, nada más.
    """

    # Preparar input para Qwen de texto
    messages = [
        {"role": "system", "content": "Eres un asistente que convierte texto en un número de opción."},
        {"role": "user", "content": prompt_normalizar}
    ]

    text_input = tokenizer_texto.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer_texto(text_input, return_tensors="pt").to("cuda")

    with torch.no_grad():
        outputs = model_texto.generate(
            **inputs,
            max_new_tokens=10,
            do_sample=False, # el modelo siempre toma el token más probable (como “greedy decoding”)
            temperature=None,
            top_p=None,
            top_k=None
        )

    # Extraer número
    respuesta_completa = tokenizer_texto.decode(outputs[0], skip_special_tokens=True).strip()
    
    # Buscar el contenido después de la última aparición de 'assistant'
    match = re.search(r'assistant\s*(.*)', respuesta_completa, re.IGNORECASE | re.DOTALL)
    if match:
        respuesta_modelo = match.group(1).strip()  # Esto es solo lo que generó el modelo
    else:
        respuesta_modelo = respuesta_completa  # fallback

    # Ahora extraemos solo el dígito
    match_num = re.search(r'\b([12])\b', respuesta_modelo)
    if match_num:
        numero_opcion = int(match_num.group(1))
    else:
        interfaz_chat("No entendí tu elección. Vamos a intentarlo de nuevo.", emisor="alerta")
        await generar_voz("No entendí tu elección. Vamos a intentarlo de nuevo.")
        # Pasamos primera_vez=False para que no repita todo
        return await cambios_meds_menu(memoria, model_whisper, model_texto, tokenizer_texto, primera_vez=False)

    # Convertir a int y manejar error
    try:
        opcion = int(numero_opcion)
    except:
        interfaz_chat("No entendí tu elección. Vamos a intentarlo de nuevo.", emisor="alerta")
        await generar_voz("No entendí tu elección. Vamos a intentarlo de nuevo.")
        return await cambios_meds_menu(memoria, model_whisper, model_texto, tokenizer_texto, primera_vez=False)

    # Ejecutar flujo correspondiente
    if opcion == 1:
        memoria = await eliminar_med(memoria, model_whisper, model_texto, tokenizer_texto)
    elif opcion == 2:
        memoria = await modificar_med(memoria, model_whisper, model_texto, tokenizer_texto)

    return memoria

# AÑADIDO: Parámetro primera_vez
async def eliminar_med(memoria, model_whisper, model_texto, tokenizer_texto, primera_vez=True):
    historial = memoria.get("medicinas", [])

    if not historial:
        interfaz_chat("No hay medicamentos para eliminar.", emisor="asistente")
        await generar_voz("No hay medicamentos para eliminar.")
        return memoria

    # Mostrar lista de medicamentos
    texto_lista = "<b>--- Lista actual de medicamentos ---</b><br>"
    for i, med in enumerate(historial, 1):
        texto_lista += f"{i}. {med['nombre']} - {med['dosis']} - Fin: {med['fin']}<br>"
    interfaz_chat(texto_lista, emisor="sistema")
    
    if primera_vez:
        await generar_voz("Estos son tus medicamentos actuales.")
        mensaje = "Dime el número del medicamento que quieres eliminar."
    else:
        mensaje = "Por favor, di un número válido de la lista para eliminar."

    # Pedir nombre del medicamento a eliminar
    interfaz_chat(mensaje, emisor="asistente")
    await generar_voz(mensaje)

    archivo_audio = grabar_audio(segundos=8)
    resultado = model_whisper.transcribe(
            archivo_audio, 
            language="es",
            no_speech_threshold=0.3, # si no detecta voz, que no intente transcribir nada
            condition_on_previous_text=False, #parametros antihistorial para que no se confunda con lo que ha dicho antes
            temperature=0.0 #parametro anti alucinaciones para que no invente palabras y se centre en lo que ha dicho el usuario
        )
    eleccion_texto = resultado["text"].strip().lower()
    interfaz_chat(f"{eleccion_texto}", emisor="usuario")

    # Buscar coincidencias
    prompt_normalizar = f"""
    El usuario ha dicho: "{eleccion_texto}"

    Devuelve solo el número del medicamento que quiere seleccionar.

    Reglas:
    - Si el número está escrito en letras pásalo a formato NÚMERO
    - Responde SOLO con un número
    - No escribas nada más
    """

    messages = [
        {"role": "system", "content": "Eres un asistente que convierte texto en un número."},
        {"role": "user", "content": prompt_normalizar}
    ]

    text_input = tokenizer_texto.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer_texto(text_input, return_tensors="pt").to("cuda")

    with torch.no_grad():
        outputs = model_texto.generate(
            **inputs,
            max_new_tokens=5,
            do_sample=False,
            temperature=None, top_p=None, top_k=None
        )

    respuesta_completa = tokenizer_texto.decode(outputs[0], skip_special_tokens=True).strip()
    match = re.search(r'assistant\s*(.*)', respuesta_completa, re.IGNORECASE | re.DOTALL)
    respuesta_modelo = match.group(1).strip() if match else respuesta_completa

    match_num = re.search(r'\b(\d+)\b', respuesta_modelo)
    if match_num:
        indice = int(match_num.group(1))-1
    else:
        interfaz_chat("No entendí el número. Vamos a intentarlo de nuevo.", emisor="alerta")
        await generar_voz("No entendí el número. Vamos a intentarlo de nuevo.")
        return await eliminar_med(memoria, model_whisper, model_texto, tokenizer_texto, primera_vez=False)

    if 0 <= indice < len(historial):
        med = historial[indice]
        confirm_msg = f"¿Seguro que quieres eliminar {med['nombre']}?"
        interfaz_chat(confirm_msg, emisor="asistente")
        await generar_voz(confirm_msg)

        archivo_conf = grabar_audio(segundos=5)
        resultado_conf = model_whisper.transcribe(
            archivo_conf, 
            language="es",
            no_speech_threshold=0.3,
            condition_on_previous_text=False,
            temperature=0.0
        )
        respuesta_conf = resultado_conf["text"].lower()

        if any(p in respuesta_conf for p in ["sí", "si", "vale", "correcto"]):
            memoria["medicinas"].pop(indice)
            guardar_memoria(memoria)
            interfaz_chat(f"He eliminado {med['nombre']}.", emisor="asistente")
            await generar_voz(f"He eliminado {med['nombre']}.")
            await generar_voz(f"Aquí tienes tu lista actualizada.")
            mostrar_recordatorios(memoria)
        else:
            interfaz_chat("No he eliminado el medicamento.", emisor="asistente")
            await generar_voz("No he eliminado el medicamento.")
        return memoria
    else:
        interfaz_chat("Ese número no está en la lista. Vamos a probar de nuevo.", emisor="alerta")
        await generar_voz("Ese número no está en la lista. Vamos a probar de nuevo.")
        return await eliminar_med(memoria, model_whisper, model_texto, tokenizer_texto, primera_vez=False)

# AÑADIDO: Parámetro primera_vez
async def modificar_med(memoria, model_whisper, model_texto, tokenizer_texto, primera_vez=True):
    historial = memoria.get("medicinas", [])

    if not historial:
        interfaz_chat("No hay medicamentos para modificar.", emisor="asistente")
        await generar_voz("No hay medicamentos para modificar.")
        return memoria

    texto_lista = "<b>--- Lista actual de medicamentos ---</b><br>"
    for i, med in enumerate(historial, 1):
        texto_lista += f"{i}. {med['nombre']} - {med['dosis']} - Fin: {med['fin']}<br>"
    interfaz_chat(texto_lista, emisor="sistema")
    
    if primera_vez:
        await generar_voz("Estos son tus medicamentos actuales.")
        mensaje = "Dime el número del medicamento que quieres modificar."
    else:
        mensaje = "Por favor, di un número válido de la lista para modificar."

    interfaz_chat(mensaje, emisor="asistente")
    await generar_voz(mensaje)

    archivo_audio = grabar_audio(segundos=8)
    resultado = model_whisper.transcribe(
        archivo_audio, 
        language="es",
        no_speech_threshold=0.3, # si no detecta voz, que no intente transcribir nada
        condition_on_previous_text=False,
        temperature=0.0
    )
    eleccion_texto = resultado["text"].strip().lower()
    interfaz_chat(f"{eleccion_texto}", emisor="usuario")

    prompt_normalizar = f"""
    El usuario ha dicho: "{eleccion_texto}"
    Devuelve solo el número del medicamento que quiere seleccionar.
    Reglas:
    - Si el número está escrito en letras pásalo a formato NÚMERO
    - Responde SOLO con un número
    - No escribas nada más
    """

    messages = [
        {"role": "system", "content": "Eres un asistente que convierte texto en un número."},
        {"role": "user", "content": prompt_normalizar}
    ]

    text_input = tokenizer_texto.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer_texto(text_input, return_tensors="pt").to("cuda")

    with torch.no_grad():
        outputs = model_texto.generate(
            **inputs,
            max_new_tokens=5,
            do_sample=False,
            temperature=None, top_p=None, top_k=None
        )

    respuesta_completa = tokenizer_texto.decode(outputs[0], skip_special_tokens=True).strip()
    match = re.search(r'assistant\s*(.*)', respuesta_completa, re.IGNORECASE | re.DOTALL)
    respuesta_modelo = match.group(1).strip() if match else respuesta_completa

    match_num = re.search(r'\b(\d+)\b', respuesta_modelo)
    if match_num:
        indice = int(match_num.group(1))-1
    else:
        interfaz_chat("No entendí el número. Vamos a intentarlo de nuevo.", emisor="alerta")
        await generar_voz("No entendí el número. Vamos a intentarlo de nuevo.")
        return await modificar_med(memoria, model_whisper, model_texto, tokenizer_texto, primera_vez=False)

    if not (0 <= indice < len(historial)):
      interfaz_chat("Ese número no está en la lista. Vamos a intentarlo de nuevo.", emisor="alerta")
      await generar_voz("Ese número no está en la lista. Vamos a intentarlo de nuevo.")
      return await modificar_med(memoria, model_whisper, model_texto, tokenizer_texto, primera_vez=False)

    med = historial[indice]

    # ========================
    # QUÉ MODIFICAR
    # ========================
    mensaje = f"Vas a modificar {med['nombre']}. ¿Qué campo quieres cambiar: nombre, dosis o fecha fin?"
    interfaz_chat(mensaje, emisor="asistente")
    await generar_voz(mensaje)
    
    archivo_audio = grabar_audio(segundos=7)
    resultado = model_whisper.transcribe(
            archivo_audio, 
            language="es",
            no_speech_threshold=0.3, # si no detecta voz, que no intente transcribir nada
            condition_on_previous_text=False, #parametros antihistorial para que no se confunda con lo que ha dicho antes
            temperature=0.0 #parametro anti alucinaciones para que no invente palabras y se centre en lo que ha dicho el usuario
        )
    campo_texto = resultado["text"].lower()
    interfaz_chat(f"{campo_texto}", emisor="usuario")

    # IA para interpretar campo
    prompt_campo = f"""
    El usuario ha dicho: "{campo_texto}"
    Devuelve SOLO una de estas palabras: nombre, dosis o fin.
    """

    messages = [
        {"role": "system", "content": "Clasifica en nombre, dosis o fin."},
        {"role": "user", "content": prompt_campo}
    ]

    text_input = tokenizer_texto.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer_texto(text_input, return_tensors="pt").to("cuda")

    with torch.no_grad():
        outputs = model_texto.generate(**inputs, max_new_tokens=5, do_sample=False, temperature=None, top_p=None, top_k=None)

    respuesta = tokenizer_texto.decode(outputs[0], skip_special_tokens=True)
    match = re.search(r'assistant\s*(.*)', respuesta, re.DOTALL)
    campo = match.group(1).strip() if match else respuesta.strip()

    if campo not in ["nombre", "dosis", "fin"]:
        interfaz_chat("No entendí qué quieres modificar. Vamos a intentarlo de nuevo.", emisor="alerta")
        await generar_voz("No entendí qué quieres modificar. Vamos a intentarlo de nuevo.")
        # Aquí también pasamos primera_vez=False para que no lea la lista de nuevo
        return await modificar_med(memoria, model_whisper, model_texto, tokenizer_texto, primera_vez=False)

    # ========================
    # NUEVO VALOR
    # ========================
    interfaz_chat(f"Dime el nuevo valor para {campo}.", emisor="asistente")
    await generar_voz(f"Dime el nuevo valor para {campo}.")

    archivo_audio = grabar_audio(segundos=10)
    resultado = model_whisper.transcribe(
            archivo_audio, 
            language="es",
            no_speech_threshold=0.3, # si no detecta voz, que no intente transcribir nada
            condition_on_previous_text=False, #parametros antihistorial para que no se confunda con lo que ha dicho antes
            temperature=0.0 #parametro anti alucinaciones para que no invente palabras y se centre en lo que ha dicho el usuario
        )
    nuevo_valor = resultado["text"].strip()
    interfaz_chat(f"{nuevo_valor}", emisor="usuario")

    # ========================
    # CONFIRMACIÓN
    # ========================
    interfaz_chat(f"¿Confirmas cambiar {campo} a {nuevo_valor}? (Responde con SÍ o NO)", emisor="asistente")
    await generar_voz(f"¿Confirmas cambiar {campo} a {nuevo_valor}? (Responde con SÍ o NO)")

    archivo_audio = grabar_audio(segundos=5)
    resultado = model_whisper.transcribe(
            archivo_audio, 
            language="es",
            no_speech_threshold=0.3,
            condition_on_previous_text=False,
            temperature=0.0
        )
    confirmacion = resultado["text"].lower()
    interfaz_chat(f"{confirmacion}", emisor="usuario")

    if any(p in confirmacion for p in ["sí", "si", "vale", "correcto"]):
        valor_anterior = med[campo]
        med[campo] = nuevo_valor
        guardar_memoria(memoria)

        # Mostrar cambio en interfaz
        texto_cambio = f"<b>--- Cambio realizado ---</b><br>Medicamento: {med['nombre']}<br>{campo.upper()}:<br>Antes: {valor_anterior}<br>Ahora: {nuevo_valor}"
        interfaz_chat(texto_cambio, emisor="sistema")

        interfaz_chat(f"He actualizado {campo} de {valor_anterior} a {nuevo_valor}.", emisor="asistente")
        await generar_voz(f"He actualizado {campo} de {valor_anterior} a {nuevo_valor}.")
        
        # Mostrar lista completa actualizada
        mostrar_recordatorios(memoria)
    else:
        interfaz_chat("No se ha realizado ningún cambio.", emisor="asistente")
        await generar_voz("No se ha realizado ningún cambio.")

    return memoria


# =====================================================================
# 9. OPCIÓN 3: TABLA DE HORARIOS (HTML)
# =====================================================================
from IPython.display import display, HTML

def resumen_visual(datos_medicinas):
    interfaz_chat("Organizando horarios con lógica exacta...", emisor="sistema")

    if isinstance(datos_medicinas, dict):
        datos_medicinas = datos_medicinas.get("medicinas", [])

    horarios = {"Mañana": [], "Mediodía": [], "Noche": []}
    hoy = datetime.now().date()

    for med in datos_medicinas:
        nombre = med.get("nombre", "").strip()
        dosis = med.get("dosis", "").strip()
        fin = med.get("fin", "").strip()

        # ---- FILTRAR POR FECHA ----
        if fin:
            try:
                fecha_fin = datetime.strptime(fin, "%d-%m-%Y").date()
                if fecha_fin < hoy:
                    continue
            except:
                pass

        # ---- LIMPIAR DOSIS ----
        dosis_limpia = re.split(r'\b(cada|durante)\b', dosis, flags=re.IGNORECASE)[0].strip(" ,.-")
        item = f"{nombre}<br><span style='color:red; font-weight:bold;'>{dosis_limpia}</span>"
        dosis_lower = dosis.lower()

        # ---- DISTRIBUCIÓN ----
        if "8 horas" in dosis_lower or "3 veces" in dosis_lower:
            horarios["Mañana"].append(item)
            horarios["Mediodía"].append(item)
            horarios["Noche"].append(item)
        elif "12 horas" in dosis_lower or "2 veces" in dosis_lower:
            horarios["Mañana"].append(item)
            horarios["Noche"].append(item)
        elif "24 horas" in dosis_lower or "1 vez" in dosis_lower or "cada día" in dosis_lower:
            horarios["Mañana"].append(item)
        else:
            horarios["Mañana"].append(item)

    def formatear(lista):
        if not lista:
            return "<i>Nada</i>"
        return "<br><br>".join(lista)

    html = f"""
    <div style="font-family: Arial; max-width: 650px; margin: 20px auto; border: 2px solid #333; border-radius: 15px; overflow: hidden;">
        <h2 style="background:#4CAF50;color:white;text-align:center;padding:15px;margin:0;">
            📅 Tu medicación diaria
        </h2>

        <table style="width:100%; border-collapse: collapse; font-size:18px;">
            <tr style="background:#FFF9C4;">
                <td style="padding:15px;font-weight:bold;width:30%;">☀️ Mañana</td>
                <td style="padding:15px;">{formatear(horarios["Mañana"])}</td>
            </tr>
            <tr style="background:#FFE0B2;">
                <td style="padding:15px;font-weight:bold;">🌤 Mediodía</td>
                <td style="padding:15px;">{formatear(horarios["Mediodía"])}</td>
            </tr>
            <tr style="background:#C5CAE9;">
                <td style="padding:15px;font-weight:bold;">🌙 Noche</td>
                <td style="padding:15px;">{formatear(horarios["Noche"])}</td>
            </tr>
        </table>
    </div>
    """
    display(HTML(html))


# =====================================================================
# 10. OPCIÓN 4: PREGUNTAS AL ASISTENTE
# =====================================================================

async def preguntas(model_whisper, model_texto, tokenizer_texto):
    #le decimos al usuario que puede preguntar
    mensaje_inicio = "Adelante, cuéntame. ¿Qué duda tienes sobre tu medicación o tu salud?"
    interfaz_chat(mensaje_inicio, emisor="asistente")
    await generar_voz(mensaje_inicio)

    #grabamos el audio con la funcion que ya teniamos definida
    #vamos a poner por ejemplo 10 segundos de escucha
    archivo_audio = grabar_audio(segundos=10)

    #transcribimos con Whisper
    interfaz_chat("Transcribiendo tu consulta...", emisor="sistema")
    resultado = model_whisper.transcribe(
            archivo_audio, 
            language="es",
            no_speech_threshold=0.3, # si no detecta voz, que no intente transcribir nada
            condition_on_previous_text=False, #parametros antihistorial para que no se confunda con lo que ha dicho antes
            temperature=0.0 #parametro anti alucinaciones para que no invente palabras y se centre en lo que ha dicho el usuario
        )
    pregunta_usuario = resultado["text"]
    interfaz_chat(f"{pregunta_usuario}", emisor="usuario")

    #cargamos el historial para dar contexto a gemini
    memoria = cargar_memoria()
    historial_raw = memoria.get("medicinas", [])

    # SOLUCIÓN AL JSON: Convertimos el JSON/Diccionario a texto natural
    historial_texto = ""
    for item in historial_raw:
        if isinstance(item, dict):
            # Si es un diccionario, unimos sus claves y valores de forma legible
            detalles = ", ".join([f"{k}: {v}" for k, v in item.items()])
            historial_texto += f"- {detalles}\n"
        else:
            # Por si acaso es solo una lista de strings
            historial_texto += f"- {item}\n"

    # Si el historial está vacío, le damos un valor por defecto
    if not historial_texto.strip():
        historial_texto = "El usuario no tiene medicación registrada actualmente."

    #construimos el prompt
    prompt = f"""
    You are a personal health assistant—direct and very respectful—designed for older adults.
    All in Spanish.
    The user has just asked you the following question by voice: “{pregunta_usuario}”

    RULES FOR YOUR RESPONSE:
    1. Respond VERY BRIEFLY. DO NOT THANK THE USER FOR THE QUESTION AND DO NOT SAY GOODBYE.
    2. If the user asks about drug interactions or dosages, refer ONLY to the user’s current medication history:{historial_texto}
    3. If the health concern is a serious medical issue, respond coherently but always recommend that they consult their doctor or pharmacist.
    4. If the medication for which they are asking about the dosage or expiration date is not in their medication history, tell them it is not in their history.
    6. Do not use complex formats or long lists, as this response will be read aloud.
    """

    #generamos la respuesta con Qwen de texto 1.5B
    inputs = tokenizer_texto(prompt, return_tensors="pt").to("cuda")

    with torch.no_grad():
        outputs = model_texto.generate(
            **inputs,
            max_new_tokens=150,
            temperature=0.1,
            do_sample=True,
            pad_token_id=tokenizer_texto.eos_token_id
        )

    # Decodificar respuesta
    # Contamos cuántos tokens tenía el prompt
    longitud_prompt = inputs.input_ids.shape[1] 
    # Recortamos el prompt de la salida
    tokens_generados = outputs[0][longitud_prompt:] 

    # Decodificamos
    respuesta_bruta = tokenizer_texto.decode(tokens_generados, skip_special_tokens=True).strip()

    # LA MAGIA: Rompemos el texto por los saltos de línea y nos quedamos SOLO con la primera línea.
    # Así, todo lo que empiece por "Nota:" o "¿Cómo puedo ayudarte?" se va a la basura.
    solo_la_respuesta = respuesta_bruta.split("\n")[0].strip()

    interfaz_chat(solo_la_respuesta, emisor="asistente")

    # Limpiamos para el TTS
    texto_limpio_para_voz = solo_la_respuesta.replace("*", "").replace('"', '')
    await generar_voz(texto_limpio_para_voz)


# =====================================================================
# 11. OPCIÓN 5: LECTOR DE DOCUMENTOS Y PDF
# =====================================================================
from pdf2image import convert_from_path
from qwen_vl_utils import process_vision_info

def analizar_documento(nombre_archivo, model_vision, processor_vision):
    paginas_a_procesar = []

    if nombre_archivo.lower().endswith('.pdf'):
        interfaz_chat(f"Convirtiendo PDF a imágenes: {nombre_archivo}", emisor="sistema")
        try:
            imagenes_pdf = convert_from_path(nombre_archivo, dpi=200)

            for i, imagen in enumerate(imagenes_pdf):
                temp_img_path = f"temp_page_{i}.png"
                imagen.save(temp_img_path, "PNG")
                paginas_a_procesar.append(temp_img_path)

        except Exception as e:
            interfaz_chat(f"Error al convertir el PDF: {e}", emisor="alerta")
            return None
    else:
        # si ya es una imagen no hace falta preprocesado
        paginas_a_procesar.append(nombre_archivo)

    texto_total = []
    prompt = """
    Extract all the information from the document.
    All in SPANISH.
    DO NOT ADD ANYTHING ELSE.
    """

    # BUCLE DE PROCESAMIENTO PÁGINA A PÁGINA
    try:
        for i, ruta_imagen in enumerate(paginas_a_procesar):
            interfaz_chat(f"Analizando página/imagen {i+1} de {len(paginas_a_procesar)}...", emisor="sistema")

            mensajes = [{
                "role": "user",
                "content": [
                    {"type": "image", "image": ruta_imagen},
                    {"type": "text", "text": prompt},
                ],
            }]

            interfaz_chat("El modelo de visión está leyendo la imagen...", emisor="sistema")
            text = processor_vision.apply_chat_template(mensajes, tokenize=False, add_generation_prompt=True)
            image_inputs, video_inputs = process_vision_info(mensajes)

            # Usa las variables globales MIN_PIXELS y MAX_PIXELS que pusimos antes en el archivo
            inputs = processor_vision(
                text=[text],
                images=image_inputs,
                videos=video_inputs,
                padding=True,
                return_tensors="pt",
                min_pixels=MIN_PIXELS,
                max_pixels=MAX_PIXELS
            ).to("cuda")

            with torch.no_grad():
                generated_ids = model_vision.generate(**inputs, max_new_tokens=1024)

            generated_ids_trimmed = [
                out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
            ]

            texto_pagina = processor_vision.batch_decode(
                generated_ids_trimmed,
                skip_special_tokens=True
            )[0].strip()

            texto_total.append(f"--- PÁGINA {i+1} ---\n{texto_pagina}")

            del inputs, generated_ids
            torch.cuda.empty_cache()

            if "temp_page_" in ruta_imagen and os.path.exists(ruta_imagen):
                os.remove(ruta_imagen)

    except Exception as e:
        interfaz_chat(f"Error durante la inferencia del modelo: {e}", emisor="alerta")
        return None

    return "\n\n".join(texto_total)


async def lector_docs(model_vision, processor_vision):
    interfaz_chat("Por favor, sube la foto de tu documento.", emisor="asistente")
    await generar_voz("Por favor, sube la foto de tu documento.")

    # Abre el selector de archivos de Colab
    await asyncio.sleep(1)
    subido = files.upload()

    if subido:
        nombre_archivo = list(subido.keys())[0]

        interfaz_chat("Analizando documento...", emisor="sistema")
        datos_extraidos = analizar_documento(nombre_archivo, model_vision, processor_vision)

        if datos_extraidos:
            interfaz_chat(datos_extraidos, emisor="asistente")
            await generar_voz(datos_extraidos)

            # Borramos el archivo tras procesarlo
            if os.path.exists(nombre_archivo):
                os.remove(nombre_archivo)
                interfaz_chat(f"Archivo temporal '{nombre_archivo}' eliminado.", emisor="sistema")
            return
        else:
            confirmacion = "Lo siento, el documento estaba vacío o no tenía el formato adecuado."
            interfaz_chat(confirmacion, emisor="asistente")
            await generar_voz(confirmacion)

            # Borramos el archivo tras procesarlo
            if os.path.exists(nombre_archivo):
                os.remove(nombre_archivo)
                interfaz_chat(f"Archivo temporal '{nombre_archivo}' eliminado.", emisor="sistema")
    else:
        conf = "Lo siento, no se ha podido cargar el documento."
        interfaz_chat(conf, emisor="alerta")



# =====================================================================
# 12. OPCIÓN 6: MENÚ DE AJUSTES + FUNCIONES DE CAMBIO DE NOMBRE Y BORRADO DE HISTORIAL
# =====================================================================
import re
import torch
import json
import asyncio

async def cambiar_nombre(memoria, model_whisper, model_texto, tokenizer_texto):
    texto_bienvenida = "¿Por qué nombre quieres que te llame?"
    interfaz_chat(texto_bienvenida, emisor="asistente")
    await generar_voz(texto_bienvenida)

    # Grabamos al usuario
    archivo_wav = grabar_audio(segundos=5)

    # 1. Transcribimos el audio con Whisper (usando el parámetro)
    resultado = model_whisper.transcribe(
            archivo_wav, 
            language="es",
            no_speech_threshold=0.3, # si no detecta voz, que no intente transcribir nada
            condition_on_previous_text=False, #parametros antihistorial para que no se confunda con lo que ha dicho antes
            temperature=0.0 #parametro anti alucinaciones para que no invente palabras y se centre en lo que ha dicho el usuario
        )
    texto_bruto = resultado["text"].strip()
    interfaz_chat(f"{texto_bruto}", emisor="usuario")

    # 2. PROCESAMOS EL NOMBRE CON QWEN (usando los parámetros)
    interfaz_chat("Procesando tu nombre...", emisor="sistema")

    # Preparamos el prompt estricto para extraer solo el nombre
    mensajes = [
        {"role": "system", "content": "Eres un asistente experto en extracción de entidades. Tu única tarea es leer una frase y devolver ÚNICAMENTE el nombre propio de la persona que se presenta. No añadas puntos, ni saludos, ni explicaciones. Solo la palabra del nombre."},
        {"role": "user", "content": f"Extrae el nombre de esta frase: '{texto_bruto}'"}
    ]

    # Tokenizamos y mandamos al modelo
    texto_prompt = tokenizer_texto.apply_chat_template(mensajes, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer_texto([texto_prompt], return_tensors="pt").to(model_texto.device)

    # Generamos la respuesta con temperature baja para mayor precisión
    outputs = model_texto.generate(**inputs, max_new_tokens=10, temperature=0.1)
    nombre_limpio = tokenizer_texto.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True).strip()

    interfaz_chat(f"Nombre extraído: '{nombre_limpio}'", emisor="sistema")
    # ========================================================

    # Guardamos el nombre limpio en memoria
    memoria["nombre"] = nombre_limpio
    guardar_memoria(memoria)

    texto_confirmacion = f"¡Perfecto, {memoria['nombre']}! Ya he cambiado tu nombre. 🤗"
    interfaz_chat(texto_confirmacion, emisor="asistente")
    await generar_voz(texto_confirmacion)

    # RETORNAMOS LA MEMORIA ACTUALIZADA
    return memoria


async def borrar_historial(memoria, model_whisper):
    texto = "¿Seguro que quieres eliminar tu historial? Si sigues adelante borraré todo tu registro de medicamentos y esta acción es irreversible. ¿Quieres seguir adelante?"
    interfaz_chat(texto, emisor="asistente")
    await generar_voz(texto)

    archivo_audio = grabar_audio(segundos=5)
    
    # Transcribimos con Whisper (usando el parámetro)
    resultado = model_whisper.transcribe(
            archivo_audio, 
            language="es",
            no_speech_threshold=0.3,
            condition_on_previous_text=False,
            temperature=0.0
        )
    confirmacion = resultado["text"].lower()
    interfaz_chat(confirmacion, emisor="usuario")

    if any(p in confirmacion for p in ["sí", "si", "vale", "correcto"]):
        # Mantenemos el nombre pero borramos el resto
        perfil_vacio = {"nombre": memoria['nombre'], "medicinas": [], "ultimas_adiciones": []}
        with open("memoria_salud.json", "w") as f:
            json.dump(perfil_vacio, f, indent=4)
            
        memoria = perfil_vacio
        interfaz_chat("Historial borrado correctamente.", emisor="sistema")
        await generar_voz("He borrado todo tu historial correctamente.")
        return memoria

    else:
        interfaz_chat("No se ha realizado ningún cambio.", emisor="sistema")
        await generar_voz("No se ha realizado ningún cambio.")

    return memoria

# AÑADIDO: Parámetro primera_vez
async def menu_ajustes(model_whisper, model_texto, tokenizer_texto, primera_vez=True):
    interfaz_chat("<b>AJUSTES 🔧</b>", emisor="sistema")
    # Texto para pantalla
    menu_pantalla = (
        "Puedes hacer las siguientes acciones: <br>"
        "1. Cambiar el nombre<br>"
        "2. Borrar tu historial<br>"
        "3. Volver al menú principal<br>"
        "Elige un número válido"
    )
    interfaz_chat(menu_pantalla, emisor="asistente")
    
    if primera_vez:
        texto_voz = menu_pantalla.replace("<br>", "\n")
    else:
        texto_voz = "¿Qué ajuste necesitas? Di 1, 2 o 3."
        
    await generar_voz(texto_voz)

    # Escuchar respuesta
    archivo_audio = grabar_audio(segundos=5)
    interfaz_chat("Transcribiendo...", emisor="sistema")
    resultado = model_whisper.transcribe(
            archivo_audio, 
            language="es",
            no_speech_threshold=0.3, # si no detecta voz, que no intente transcribir nada
            condition_on_previous_text=False, #parametros antihistorial para que no se confunda con lo que ha dicho antes
            temperature=0.0 #parametro anti alucinaciones para que no invente palabras y se centre en lo que ha dicho el usuario
        )
    eleccion_texto = resultado["text"].strip().lower()
    interfaz_chat(f"{eleccion_texto}", emisor="usuario")

    # Convertir respuesta a número de opción (1 al 3)
    prompt_normalizar = f"""
    El usuario ha dicho: "{eleccion_texto}"

    Devuelve solo un número del 1 al 3 que corresponde a la opción correcta:
    1 → Cambiar el nombre
    2 → Borrar el historial (o eliminar...)
    3 → Volver al menú principal

    REGLAS OBLIGATORIAS:
    - Si el usuario dice el número con letras (ej: "uno", "dos", "tres"), pásalo a formato NÚMERO (1, 2, 3).
    - Responde SOLO con el número matemático, nada más. 
    - Si el usuario dice algo distinto a un número que esté entre el 1 y el 3, responde SOLO con None.
    """

    # Preparar input para Qwen de texto
    messages = [
        {"role": "system", "content": "Eres un asistente que convierte la intención del usuario en un número de opción del 1 al 6."},
        {"role": "user", "content": prompt_normalizar}
    ]

    text_input = tokenizer_texto.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer_texto(text_input, return_tensors="pt").to(model_texto.device)

    interfaz_chat("Interpretando tu elección...", emisor="sistema")
    with torch.no_grad():
        outputs = model_texto.generate(
            **inputs,
            max_new_tokens=10,
            do_sample=False,
            temperature=None,
            top_p=None,
            top_k=None
        )

    # Extraer número
    respuesta_completa = tokenizer_texto.decode(outputs[0], skip_special_tokens=True).strip()

    match = re.search(r'assistant\s*(.*)', respuesta_completa, re.IGNORECASE | re.DOTALL)
    if match:
        respuesta_modelo = match.group(1).strip()
    else:
        respuesta_modelo = respuesta_completa

    # Buscar el primer dígito del 1 al 3
    match_num = re.search(r'\b([1-3])\b', respuesta_modelo)

    if match_num:
        opcion = int(match_num.group(1))
        return opcion
    else:
        # Si no detecta ninguna opción válida, avisa y reinicia
        error_msg = "No he logrado entender qué opción quieres. Vamos a intentarlo de nuevo."
        interfaz_chat(error_msg, emisor="alerta")
        await generar_voz(error_msg)
        return await menu_ajustes(model_whisper, model_texto, tokenizer_texto, primera_vez=False) # Llamada recursiva


# =====================================================================
# 13. MENÚ PRINCIPAL
# =====================================================================
import asyncio
import re
import torch

# AÑADIDO: Parámetro "primera_vez" con valor por defecto True
async def mostrar_menu_voz(model_whisper, model_texto, tokenizer_texto, primera_vez=True):
    interfaz_chat("<b>MENÚ PRINCIPAL 🩺</b>", emisor="sistema")

    # Texto COMPLETO para imprimir siempre en la PANTALLA (como ayuda visual)
    menu_pantalla = (
        "Tienes las siguientes opciones:<br>"
        "1. Registrar medicamentos mediante imágenes<br>"
        "2. Modificar o eliminar un medicamento<br>"
        "3. Ver la tabla resumen de tus tratamientos<br>"
        "4. Hacer preguntas por voz<br>"
        "5. Usar el lector de documentos<br>"
        "6. Ajustes<br>"
        "7. Salir del asistente<br>"
    )
    interfaz_chat(menu_pantalla, emisor="asistente")
    
    # LA MAGIA: Elegimos qué dice el asistente por VOZ dependiendo de si es la primera vez
    if primera_vez:
        texto_voz = menu_pantalla.replace("<br>", "\n") + "Di un número de opción válido."
    else:
        texto_voz = "¿Qué más necesitas hacer? Di un número del 1 al 7."
        
    await generar_voz(texto_voz)

    # Escuchar respuesta
    archivo_audio = grabar_audio(segundos=5)
    interfaz_chat("Transcribiendo...", emisor="sistema")
    resultado = model_whisper.transcribe(
            archivo_audio, 
            language="es",
            no_speech_threshold=0.3, # si no detecta voz, que no intente transcribir nada
            condition_on_previous_text=False, #parametros antihistorial para que no se confunda con lo que ha dicho antes
            temperature=0.0 #parametro anti alucinaciones para que no invente palabras y se centre en lo que ha dicho el usuario
        )
    eleccion_texto = resultado["text"].strip().lower()
    interfaz_chat(f"{eleccion_texto}", emisor="usuario")

    # Convertir respuesta a número de opción (1 al 7)
    prompt_normalizar = f"""
    El usuario ha dicho: "{eleccion_texto}"

    Devuelve solo un número del 1 al 7 que corresponde a la opción correcta:
    1 → Registrar medicamentos mediante imágenes (o añadir receta, subir foto...)
    2 → Modificar medicamentos (o cambiar, borrar...)
    3 → Ver Tabla Resumen de los tratamientos (o ver historial, ver mis pastillas...)
    4 → Hacer preguntas por voz (o preguntar algo, hablar contigo...)
    5 → Lector de documentos (o leer PDF, leer informe...)
    6 → Ajustes (o cambiar configuración, cambiar nombre...)
    7 → Salir (o apagar, adiós, terminar...)

    Responde SOLO con el número, nada más. Si el usuario dice algo distinto a un número que esté entre el 1 y el 7, responde SOLO con None.
    """

    # Preparar input para Qwen de texto
    messages = [
        {"role": "system", "content": "Eres un asistente que convierte la intención del usuario en un número de opción del 1 al 7."},
        {"role": "user", "content": prompt_normalizar}
    ]

    text_input = tokenizer_texto.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer_texto(text_input, return_tensors="pt").to(model_texto.device)

    interfaz_chat("Interpretando tu elección...", emisor="sistema")
    with torch.no_grad():
        outputs = model_texto.generate(
            **inputs,
            max_new_tokens=10,
            do_sample=False,
            temperature=None,
            top_p=None,
            top_k=None
        )

    # Extraer número
    respuesta_completa = tokenizer_texto.decode(outputs[0], skip_special_tokens=True).strip()

    match = re.search(r'assistant\s*(.*)', respuesta_completa, re.IGNORECASE | re.DOTALL)
    if match:
        respuesta_modelo = match.group(1).strip()
    else:
        respuesta_modelo = respuesta_completa

    # Buscar el primer dígito del 1 al 7
    match_num = re.search(r'\b([1-7])\b', respuesta_modelo)

    if match_num:
        opcion = int(match_num.group(1))
        return opcion
    else:
        # Si no detecta ninguna opción válida, avisa y reinicia
        error_msg = "No he logrado entender qué opción quieres. Vamos a intentarlo de nuevo."
        interfaz_chat(error_msg, emisor="alerta")
        await generar_voz(error_msg)
        # Si falla y vuelve a intentarlo, le pasamos False para que no le repita todo el menú largo
        return await mostrar_menu_voz(model_whisper, model_texto, tokenizer_texto, primera_vez=False) 
    

# =====================================================================
# 14. BUCLE PRINCIPAL DEL ASISTENTE
# =====================================================================
async def iniciar_asistente(model_whisper, model_texto, tokenizer_texto, model_vision, processor_vision):
    interfaz_chat("<b>🚀 INICIANDO SISTEMA MULTIMODAL DE SALUD...</b>", emisor="sistema")

    # 1. Cargar la memoria base desde el archivo JSON
    memoria = cargar_memoria()

    # 2. Presentación (Aquí actualizamos la memoria con el nombre si es nuevo)
    memoria = await presentacion(memoria, model_whisper, model_texto, tokenizer_texto)

    # NUEVO: Creamos la variable para controlar el menú
    es_primera_vez = True

    #esperamos un poco antes de lanzar el menú para que no pise la presentación
    await asyncio.sleep(6)

    # 3. Bucle del asistente, que acabará cuando el usuario decida
    while True:
        # Llamamos al menú por voz pasándole la variable
        opcion = await mostrar_menu_voz(model_whisper, model_texto, tokenizer_texto, primera_vez=es_primera_vez)
        
        # Una vez que ha pasado por el menú, apagamos el interruptor para las siguientes vueltas
        es_primera_vez = False

        # ==========================================
        # 4. RUTA HACIA LA FASE B (FUNCIONALIDADES)
        # ==========================================
        if opcion == 1:
            interfaz_chat("Opción 1 seleccionada: Registrar medicamentos mediante imágenes", emisor="sistema")
            memoria = await subir_receta(memoria, model_vision, processor_vision)

        elif opcion == 2:
            interfaz_chat("Opción 2 seleccionada: Modificar o eliminar medicamentos", emisor="sistema")
            memoria = await cambios_meds_menu(memoria, model_whisper, model_texto, tokenizer_texto)

        elif opcion == 3:
            interfaz_chat("Opción 3 seleccionada: Ver Tabla Resumen de los tratamientos", emisor="sistema")
            resumen_visual(memoria) # Esta función no usa await porque genera HTML directo

        elif opcion == 4:
            interfaz_chat("Opción 4 seleccionada: Preguntas por voz", emisor="sistema")
            await preguntas(model_whisper, model_texto, tokenizer_texto)

        elif opcion == 5:
            interfaz_chat("Opción 5 seleccionada: Lector de documentos", emisor="sistema")
            await lector_docs(model_vision, processor_vision)

        # ==========================================
        # 5. AJUSTES
        # ==========================================
        elif opcion == 6:
            op_ajustes = await menu_ajustes(model_whisper, model_texto, tokenizer_texto)
            if op_ajustes == 1:
                memoria = await cambiar_nombre(memoria, model_whisper, model_texto, tokenizer_texto)
            elif op_ajustes == 2:
                memoria = await borrar_historial(memoria, model_whisper)

        # ==========================================
        # 6. CERRAR SESIÓN
        # ==========================================
        elif opcion == 7:
            # Despedida y salimos del bucle
            despedida = f"¡Hasta pronto, {memoria['nombre']}! Cuídate mucho y recuerda seguir tus tratamientos."
            interfaz_chat(despedida, emisor="asistente")
            await generar_voz(despedida)
            break # El break es vital para salir del "while True" y apagar el asistente
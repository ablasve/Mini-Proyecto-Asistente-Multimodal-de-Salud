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

async def generar_voz(texto):
    # Elegimos la voz: 'es-ES-ElviraNeural' (Mujer, España, muy clara)
    # O 'es-ES-AlvaroNeural' si prefieres hombre.
    VOICE = "es-ES-ElviraNeural"
    OUTPUT_FILE = "respuesta_asistente.mp3"

    communicate = edge_tts.Communicate(texto, VOICE, rate="-10%") # rate="-10%" si la quieres más lenta
    await communicate.save(OUTPUT_FILE)

    # Reproducir en Colab
    display(Audio(OUTPUT_FILE, autoplay=True))


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
    print(f"Escuchando durante {segundos} segundos...")
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

# ATENCIÓN: Añadimos los modelos de audio y texto como parámetros
async def presentacion(memoria, model_whisper, model_texto, tokenizer_texto):
    if memoria.get("nombre") is None:
        texto_bienvenida = "¡Hola! Soy tu Asistente de Salud. Como es nuestra primera vez hablando, no sé nada de ti. Para poder ayudarte mejor... ¿cómo te llamas?"

        print(texto_bienvenida)
        await generar_voz(texto_bienvenida)  

        # Pausa para que termine de hablar antes de grabar
        await asyncio.sleep(13)

        # Grabamos al usuario
        archivo_wav = grabar_audio(segundos=5)

        # 1. Transcribimos el audio con Whisper (usando el parámetro)
        resultado = model_whisper.transcribe(archivo_wav, language="es")
        texto_bruto = resultado["text"].strip()
        print(f"Has dicho: '{texto_bruto}'")

        # 2. PROCESAMOS EL NOMBRE CON QWEN (usando los parámetros)
        print("Procesando tu nombre...")

        mensajes = [
            {"role": "system", "content": "Eres un asistente experto en extracción de entidades. Tu única tarea es leer una frase y devolver ÚNICAMENTE el nombre propio de la persona que se presenta. No añadas puntos, ni saludos, ni explicaciones. Solo la palabra del nombre."},
            {"role": "user", "content": f"Extrae el nombre de esta frase: '{texto_bruto}'"}
        ]

        texto_prompt = tokenizer_texto.apply_chat_template(mensajes, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer_texto([texto_prompt], return_tensors="pt").to(model_texto.device)

        outputs = model_texto.generate(**inputs, max_new_tokens=10, temperature=0.1)
        nombre_limpio = tokenizer_texto.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True).strip()

        print(f"Nombre extraído: '{nombre_limpio}'")
        # ========================================================

        # Guardamos el nombre limpio en memoria
        memoria["nombre"] = nombre_limpio
        guardar_memoria(memoria)

        texto_confirmacion = f"¡Perfecto, {memoria['nombre']}! He creado tu perfil. Ya podemos empezar con las consultas."
        print(f"\n {texto_confirmacion}")
        await generar_voz(texto_confirmacion)

        # RETORNAMOS LA MEMORIA ACTUALIZADA
        return memoria

    else:
        texto_retorno = f"¡Hola de nuevo, {memoria['nombre']}! ¿Qué hacemos hoy?"
        print(f"{texto_retorno}")
        await generar_voz(texto_retorno)
        return memoria


# =====================================================================
# 5. FUNCIONES DE PROCESAMIENTO VISUAL (RECETAS)
# =====================================================================
import torch
import re
import json
from qwen_vl_utils import process_vision_info

# Fijamos los números mínimo y máximo de píxeles para la foto
MIN_PIXELS = 256 * 28 * 28
MAX_PIXELS = 1280 * 28 * 28

# ATENCIÓN: Añadimos model_vision y processor_vision como parámetros
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
        print("El modelo local está leyendo la imagen...")

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

        # Liberar memoria de GPU manualmente
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
            print("No hay JSON válido en la respuesta")
            print(texto_respuesta)
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
        print("Error:", e)
        return None


# =====================================================================
# 6. GESTIÓN DE MEDICAMENTOS (REGISTRO)
# =====================================================================
# Esta función usa diccionarios y listas básicas de Python, no necesita modelos.
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
    print("\n[Asistente]: Por favor, sube la foto de tu receta o medicina.")
    await generar_voz("Por favor, sube la foto de tu receta o medicina.")

    # esperamos a que acabe el audio para subir el archivo
    await asyncio.sleep(5)

    # Abre el selector de archivos de Colab
    subido = files.upload()

    await asyncio.sleep(5)

    if subido:
        nombre_archivo = list(subido.keys())[0]

        print("--- Analizando imagen... ---")
        # ATENCIÓN: Pasamos los modelos a la función auxiliar
        datos_extraidos = analizar_receta(nombre_archivo, memoria, model_vision, processor_vision)

        if datos_extraidos:
            memoria_actualizada = registrar_en_memoria(datos_extraidos)
            ultimas = memoria_actualizada.get('ultimas_adiciones', [])

            if ultimas:
                nombres = [med['nombre'] for med in ultimas]
                if len(nombres) == 1:
                    confirmacion = f"He leído y guardado correctamente: {nombres[0]}. Ya está en tu lista de recordatorios."
                else:
                    confirmacion = f"He leído y guardado correctamente: {', '.join(nombres[:-1])} y {nombres[-1]}. Ya están en tu lista de recordatorios."
            else:
                confirmacion = "No se han añadido nuevas medicinas; ya estaban en tu lista."

            print(f"\n[Asistente]: {confirmacion}")
            await generar_voz(confirmacion)

            mostrar_recordatorios(memoria_actualizada)

            if os.path.exists(nombre_archivo):
                os.remove(nombre_archivo)
                print(f"Archivo temporal '{nombre_archivo}' eliminado.")

            return memoria_actualizada

        else:
            confirmacion = f"""
            He leído la información que me has proporcionado, y ya estaba introducida en el registro.
            Aquí tienes el registro y puedes comprobar que está todo en orden:
            """
            print(f"\n[Asistente]: {confirmacion}")
            await generar_voz(confirmacion)

            mostrar_recordatorios(memoria)

            if os.path.exists(nombre_archivo):
                os.remove(nombre_archivo)
                print(f"Archivo temporal '{nombre_archivo}' eliminado.")

            return memoria

    await generar_voz("No se ha subido ninguna imagen.")
    return memoria

def mostrar_recordatorios(memoria):
    print("\n--- TUS MEDICAMENTOS REGISTRADOS ---")
    for m in memoria.get("medicinas", []):
        fin = m.get('fin', '')
        print(f"💊 {m['nombre']} - {m['dosis']} - Fecha Fin Tratamiento: {fin}")
    print("------------------------------------\n")


# =====================================================================
# 8. OPCIÓN 2: MODIFICAR Y ELIMINAR 
# =====================================================================

async def cambios_meds_menu(memoria, model_whisper, model_texto, tokenizer_texto):
    historial = memoria.get("medicinas", [])

    if not historial:
        await generar_voz("No hay medicamentos registrados aún.")
        return memoria

    menu_texto = (
        "Diga el número de la opción que le interesa:\n"
        "1. Eliminar un medicamento\n"
        "2. Modificar un medicamento\n"
    )
    print(f"\n[Asistente]: {menu_texto}")
    await generar_voz(menu_texto)
    await asyncio.sleep(9)

    archivo_audio = grabar_audio(segundos=5)
    resultado = model_whisper.transcribe(archivo_audio, language="es")
    eleccion_texto = resultado["text"].strip().lower()
    print(f"Has elegido: {eleccion_texto}")

    prompt_normalizar = f"""
    El usuario ha dicho: "{eleccion_texto}"

    Devuelve solo un número (1 o 2) que corresponde a la opción correcta:
    1 → Eliminar un medicamento
    2 → Modificar un medicamento

    Responde solo con el número, nada más.
    """

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
            do_sample=False,
            temperature=None,
            top_p=None,
            top_k=None
        )

    respuesta_completa = tokenizer_texto.decode(outputs[0], skip_special_tokens=True).strip()
    match = re.search(r'assistant\s*(.*)', respuesta_completa, re.IGNORECASE | re.DOTALL)
    respuesta_modelo = match.group(1).strip() if match else respuesta_completa

    match_num = re.search(r'\b([12])\b', respuesta_modelo)
    if match_num:
        numero_opcion = int(match_num.group(1))
    else:
        await generar_voz("No entendí tu elección. Vamos a intentarlo de nuevo.")
        await asyncio.sleep(4)
        return await cambios_meds_menu(memoria, model_whisper, model_texto, tokenizer_texto)

    try:
        opcion = int(numero_opcion)
    except:
        await generar_voz("No entendí tu elección. Vamos a intentarlo de nuevo.")
        await asyncio.sleep(4)
        return await cambios_meds_menu(memoria, model_whisper, model_texto, tokenizer_texto)

    if opcion == 1:
        memoria = await eliminar_med(memoria, model_whisper, model_texto, tokenizer_texto)
    elif opcion == 2:
        memoria = await modificar_med(memoria, model_whisper, model_texto, tokenizer_texto)

    return memoria


async def eliminar_med(memoria, model_whisper, model_texto, tokenizer_texto):
    historial = memoria.get("medicinas", [])

    if not historial:
        await generar_voz("No hay medicamentos para eliminar.")
        return memoria

    print("\n--- Lista actual de medicamentos ---")
    for i, med in enumerate(historial, 1):
        print(f"{i}. {med['nombre']} - {med['dosis']} - Fin: {med['fin']}")
    print("-----------------------------------")
    await generar_voz("Estos son tus medicamentos actuales.")
    await asyncio.sleep(4)

    mensaje = "Dime el número del medicamento que quieres eliminar."
    print(f"\n[Asistente]: {mensaje}")
    await generar_voz(mensaje)
    await asyncio.sleep(5)

    archivo_audio = grabar_audio(segundos=8)
    resultado = model_whisper.transcribe(archivo_audio, language="es")
    eleccion_texto = resultado["text"].strip().lower()
    print(f"Has dicho: {eleccion_texto}")

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
        await generar_voz("No entendí el número. Vamos a intentarlo de nuevo.")
        return await eliminar_med(memoria, model_whisper, model_texto, tokenizer_texto)

    if 0 <= indice < len(historial):
        med = historial[indice]
        confirm_msg = f"¿Seguro que quieres eliminar {med['nombre']}?"
        print(confirm_msg)
        await generar_voz(confirm_msg)
        await asyncio.sleep(10)

        archivo_conf = grabar_audio(segundos=5)
        resultado_conf = model_whisper.transcribe(archivo_conf, language="es")
        respuesta_conf = resultado_conf["text"].lower()

        if any(p in respuesta_conf for p in ["sí", "si", "vale", "correcto"]):
            memoria["medicinas"].pop(indice)
            guardar_memoria(memoria)
            await generar_voz(f"He eliminado {med['nombre']}.")
            await asyncio.sleep(11)
            await generar_voz(f"Aquí tienes tu lista actualizada.")
            mostrar_recordatorios(memoria)
        else:
            await generar_voz("No he eliminado el medicamento.")
            await asyncio.sleep(3)
        return memoria
    else:
        await generar_voz("Ese número no está en la lista. Vamos a probar de nuevo.")
        await asyncio.sleep(5)
        return await eliminar_med(memoria, model_whisper, model_texto, tokenizer_texto)


async def modificar_med(memoria, model_whisper, model_texto, tokenizer_texto):
    historial = memoria.get("medicinas", [])

    if not historial:
        await generar_voz("No hay medicamentos para modificar.")
        await asyncio.sleep(4)
        return memoria

    print("\n--- Lista actual de medicamentos ---")
    for i, med in enumerate(historial, 1):
        print(f"{i}. {med['nombre']} - {med['dosis']} - Fin: {med['fin']}")
    print("-----------------------------------")
    await generar_voz("Estos son tus medicamentos actuales.")
    await asyncio.sleep(5)

    mensaje = "Dime el número del medicamento que quieres modificar."
    print(f"\n[Asistente]: {mensaje}")
    await generar_voz(mensaje)
    await asyncio.sleep(5)

    archivo_audio = grabar_audio(segundos=8)
    resultado = model_whisper.transcribe(archivo_audio, language="es")
    eleccion_texto = resultado["text"].strip().lower()

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
        await generar_voz("No entendí el número. Vamos a intentarlo de nuevo.")
        await asyncio.sleep(5)
        return await modificar_med(memoria, model_whisper, model_texto, tokenizer_texto)

    if not (0 <= indice < len(historial)):
      await generar_voz("Ese número no está en la lista. Vamos a intentarlo de nuevo.")
      await asyncio.sleep(5)
      return await modificar_med(memoria, model_whisper, model_texto, tokenizer_texto)

    med = historial[indice]

    mensaje = f"Vas a modificar {med['nombre']}. ¿Qué campo quieres cambiar: nombre, dosis o fecha fin?"
    print(f"\n[Asistente]: {mensaje}")
    await generar_voz(mensaje)
    await asyncio.sleep(12)
    
    archivo_audio = grabar_audio(segundos=7)
    resultado = model_whisper.transcribe(archivo_audio, language="es")
    campo_texto = resultado["text"].lower()

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
        await generar_voz("No entendí qué quieres modificar. Vamos a intentarlo de nuevo.")
        await asyncio.sleep(4)
        return await modificar_med(memoria, model_whisper, model_texto, tokenizer_texto)

    await generar_voz(f"Dime el nuevo valor para {campo}.")
    await asyncio.sleep(5)

    archivo_audio = grabar_audio(segundos=10)
    resultado = model_whisper.transcribe(archivo_audio, language="es")
    nuevo_valor = resultado["text"].strip()

    await generar_voz(f"¿Confirmas cambiar {campo} a {nuevo_valor}? (Responde con SÍ o NO)")
    await asyncio.sleep(10)

    archivo_audio = grabar_audio(segundos=5)
    resultado = model_whisper.transcribe(archivo_audio, language="es")
    confirmacion = resultado["text"].lower()

    if any(p in confirmacion for p in ["sí", "si", "vale", "correcto"]):
        valor_anterior = med[campo]
        med[campo] = nuevo_valor
        guardar_memoria(memoria)

        print("\n--- Cambio realizado ---")
        print(f"Medicamento: {med['nombre']}")
        print(f"{campo.upper()}:")
        print(f"  Antes: {valor_anterior}")
        print(f"  Ahora: {nuevo_valor}")
        print("------------------------")

        await generar_voz(f"He actualizado {campo} de {valor_anterior} a {nuevo_valor}.")
        mostrar_recordatorios(memoria)
    else:
        await generar_voz("No se ha realizado ningún cambio.")

    return memoria


# =====================================================================
# 9. OPCIÓN 3: TABLA DE HORARIOS (HTML)
# =====================================================================
from IPython.display import display, HTML

def resumen_visual(datos_medicinas):
    print("Organizando horarios con lógica exacta...")

    if isinstance(datos_medicinas, dict):
        datos_medicinas = datos_medicinas.get("medicinas", [])

    horarios = {"Mañana": [], "Mediodía": [], "Noche": []}
    hoy = datetime.now().date()

    for med in datos_medicinas:
        nombre = med.get("nombre", "").strip()
        dosis = med.get("dosis", "").strip()
        fin = med.get("fin", "").strip()

        if fin:
            try:
                fecha_fin = datetime.strptime(fin, "%d-%m-%Y").date()
                if fecha_fin < hoy:
                    continue
            except:
                pass

        dosis_limpia = re.split(r'\b(cada|durante)\b', dosis, flags=re.IGNORECASE)[0].strip(" ,.-")
        item = f"{nombre}<br><span style='color:red; font-weight:bold;'>{dosis_limpia}</span>"
        dosis_lower = dosis.lower()

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
    mensaje_inicio = "Adelante, cuéntame. ¿Qué duda tienes sobre tu medicación o tu salud?"
    print(f"\n[Asistente]: {mensaje_inicio}")
    await generar_voz(mensaje_inicio)
    await asyncio.sleep(6)

    archivo_audio = grabar_audio(segundos=10)

    print("\nTranscribiendo tu consulta...")
    resultado = model_whisper.transcribe(archivo_audio, language="es")
    pregunta_usuario = resultado["text"]
    print(f"Has preguntado: {pregunta_usuario}")

    memoria = cargar_memoria()
    historial_raw = memoria.get("medicinas", [])

    historial_texto = ""
    for item in historial_raw:
        if isinstance(item, dict):
            detalles = ", ".join([f"{k}: {v}" for k, v in item.items()])
            historial_texto += f"- {detalles}\n"
        else:
            historial_texto += f"- {item}\n"

    if not historial_texto.strip():
        historial_texto = "El usuario no tiene medicación registrada actualmente."

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

    inputs = tokenizer_texto(prompt, return_tensors="pt").to("cuda")

    with torch.no_grad():
        outputs = model_texto.generate(
            **inputs,
            max_new_tokens=150,
            temperature=0.1,
            do_sample=True,
            pad_token_id=tokenizer_texto.eos_token_id
        )

    longitud_prompt = inputs.input_ids.shape[1] 
    tokens_generados = outputs[0][longitud_prompt:] 

    respuesta_bruta = tokenizer_texto.decode(tokens_generados, skip_special_tokens=True).strip()
    solo_la_respuesta = respuesta_bruta.split("\n")[0].strip()

    print(f"\n Asistente: {solo_la_respuesta}")

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
        print(f"Convirtiendo PDF a imágenes: {nombre_archivo}")
        try:
            imagenes_pdf = convert_from_path(nombre_archivo, dpi=200)

            for i, imagen in enumerate(imagenes_pdf):
                temp_img_path = f"temp_page_{i}.png"
                imagen.save(temp_img_path, "PNG")
                paginas_a_procesar.append(temp_img_path)

        except Exception as e:
            print(f"Error al convertir el PDF: {e}")
            return None
    else:
        paginas_a_procesar.append(nombre_archivo)

    texto_total = []
    prompt = """
    Extract all the information from the document.
    All in SPANISH.
    DO NOT ADD ANYTHING ELSE.
    """

    try:
        for i, ruta_imagen in enumerate(paginas_a_procesar):
            print(f"Analizando página/imagen {i+1} de {len(paginas_a_procesar)}...")

            mensajes = [{
                "role": "user",
                "content": [
                    {"type": "image", "image": ruta_imagen},
                    {"type": "text", "text": prompt},
                ],
            }]

            print("El modelo local está leyendo la imagen...")
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
        print(f"Error durante la inferencia del modelo: {e}")
        return None

    return "\n\n".join(texto_total)


async def lector_docs(model_vision, processor_vision):
    print("\n[Asistente]: Por favor, sube la foto de tu documento.")
    await generar_voz("Por favor, sube la foto de tu documento.")

    await asyncio.sleep(5)
    subido = files.upload()
    await asyncio.sleep(5)

    if subido:
        nombre_archivo = list(subido.keys())[0]

        print("--- Analizando documento... ---")
        datos_extraidos = analizar_documento(nombre_archivo, model_vision, processor_vision)

        if datos_extraidos:
            await generar_voz(datos_extraidos)

            if os.path.exists(nombre_archivo):
                os.remove(nombre_archivo)
                print(f"Archivo temporal '{nombre_archivo}' eliminado.")
            return
        else:
            confirmacion = "Lo siento, el documento estaba vacío o no tenía el formato adecuado."
            print(f"\n[Asistente]: {confirmacion}")
            await generar_voz(confirmacion)

            if os.path.exists(nombre_archivo):
                os.remove(nombre_archivo)
                print(f"Archivo temporal '{nombre_archivo}' eliminado.")
    else:
        conf = "Lo siento, no se ha podido cargar el documento."
        print(conf)



# =====================================================================
# 12. OPCIÓN 6: MENÚ DE AJUSTES + FUNCIONES DE CAMBIO DE NOMBRE Y BORRADO DE HISTORIAL
# =====================================================================
import re
import torch
import json
import asyncio

async def cambiar_nombre(memoria, model_whisper, model_texto, tokenizer_texto):
    texto_bienvenida = "¿Por qué nombre quieres que te llame?"
    print(texto_bienvenida)
    await generar_voz(texto_bienvenida)

    # Pausa para que termine de hablar antes de grabar
    await asyncio.sleep(3)

    # Grabamos al usuario
    archivo_wav = grabar_audio(segundos=5)

    # 1. Transcribimos el audio con Whisper (usando el parámetro)
    resultado = model_whisper.transcribe(archivo_wav, language="es")
    texto_bruto = resultado["text"].strip()
    print(f"Has dicho: '{texto_bruto}'")

    # 2. PROCESAMOS EL NOMBRE CON QWEN (usando los parámetros)
    print("Procesando tu nombre...")

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

    print(f"Nombre extraído: '{nombre_limpio}'")
    # ========================================================

    # Guardamos el nombre limpio en memoria
    memoria["nombre"] = nombre_limpio
    guardar_memoria(memoria)

    texto_confirmacion = f"¡Perfecto, {memoria['nombre']}! Ya he cambiado tu nombre."
    print(f"¡Perfecto, {memoria['nombre']}! Ya he cambiado tu nombre. 🤗")
    await generar_voz(texto_confirmacion)

    # RETORNAMOS LA MEMORIA ACTUALIZADA
    return memoria


async def borrar_historial(memoria, model_whisper):
    texto = """
    ¿Seguro que quieres eliminar tu historial?
    Si sigues adelante borraré todo tu registro de medicamento y esta acción es irreversible.
    ¿Quieres seguir adelante?
    """
    print(texto)
    await generar_voz(texto)
    await asyncio.sleep(12)

    archivo_audio = grabar_audio(segundos=5)
    
    # Transcribimos con Whisper (usando el parámetro)
    resultado = model_whisper.transcribe(archivo_audio, language="es")
    confirmacion = resultado["text"].lower()

    if any(p in confirmacion for p in ["sí", "si", "vale", "correcto"]):
        # Mantenemos el nombre pero borramos el resto
        perfil_vacio = {"nombre": memoria['nombre'], "medicinas": [], "ultimas_adiciones": []}
        with open("memoria_salud.json", "w") as f:
            json.dump(perfil_vacio, f, indent=4)
            
        memoria = perfil_vacio
        print("Historial borrado correctamente.")
        await generar_voz("He borrado todo tu historial correctamente.")
        await asyncio.sleep(5)
        return memoria

    else:
        print("No se ha realizado ningún cambio.")
        await generar_voz("No se ha realizado ningún cambio.")
        await asyncio.sleep(3)

    return memoria


async def menu_ajustes(model_whisper, model_texto, tokenizer_texto):
    print("\n" + " · "*10)
    print("           AJUSTES 🔧")
    print(" · "*10)
    # Texto para pantalla y para la voz
    menu_texto = (
        "Puedes hacer las siguientes acciones: \n"
        "1. Cambiar el nombre\n"
        "2. Borrar tu historial\n"
        "3. Volver al menú principal\n"
        "Elige un número válido\n"
    )
    print(f"[Asistente]: {menu_texto}")
    await generar_voz(menu_texto)

    await asyncio.sleep(20)

    # Escuchar respuesta
    archivo_audio = grabar_audio(segundos=5)
    print("Transcribiendo...")
    resultado = model_whisper.transcribe(archivo_audio, language="es")
    eleccion_texto = resultado["text"].strip().lower()
    print(f"Has dicho: '{eleccion_texto}'")

    # Convertir respuesta a número de opción (1 al 3)
    prompt_normalizar = f"""
    El usuario ha dicho: "{eleccion_texto}"

    Devuelve solo un número del 1 al 3 que corresponde a la opción correcta:
    1 → Cambiar el nombre
    2 → Borrar el historial (o eliminar...)
    3 → Volver al menú principal

    Responde SOLO con el número, nada más. Si el usuario dice algo distinto a un número que esté entre el 1 y el 3, responde SOLO con None.
    """

    # Preparar input para Qwen de texto
    messages = [
        {"role": "system", "content": "Eres un asistente que convierte la intención del usuario en un número de opción del 1 al 6."},
        {"role": "user", "content": prompt_normalizar}
    ]

    text_input = tokenizer_texto.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer_texto(text_input, return_tensors="pt").to(model_texto.device)

    print("Interpretando tu elección...")
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
        print(f"⚠️ {error_msg}")
        await generar_voz(error_msg)
        await asyncio.sleep(5)
        return await menu_ajustes(model_whisper, model_texto, tokenizer_texto) # Llamada recursiva con los parámetros



# =====================================================================
# 13. MENÚ PRINCIPAL
# =====================================================================
import asyncio
import re
import torch

async def mostrar_menu_voz(model_whisper, model_texto, tokenizer_texto):
    print("\n" + " · "*10)
    print("        MENÚ PRINCIPAL 🩺")
    print(" · "*10)

    # Texto para pantalla y para la voz
    menu_texto = (
        "Tienes las siguientes opciones:\n"
        "1. Registrar medicamentos mediante imágenes\n"
        "2. Modificar o eliminar un medicamento\n"
        "3. Ver la tabla resumen de tus tratamientos\n"
        "4. Hacer preguntas por voz\n"
        "5. Usar el lector de documentos\n"
        "6. Ajustes\n"
        "7. Salir del asistente\n"
        "Di un número de opción válido."
    )
    print(f"[Asistente]: {menu_texto}")
    await generar_voz(menu_texto)

    # Esperar unos segundos para que termine de hablar (ajustado a ~16 segundos porque el menú es largo)
    await asyncio.sleep(30)

    # Escuchar respuesta
    archivo_audio = grabar_audio(segundos=5)
    print("Transcribiendo...")
    resultado = model_whisper.transcribe(archivo_audio, language="es")
    eleccion_texto = resultado["text"].strip().lower()
    print(f"Has dicho: '{eleccion_texto}'")

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
        {"role": "system", "content": "Eres un asistente que convierte la intención del usuario en un número de opción del 1 al 6."},
        {"role": "user", "content": prompt_normalizar}
    ]

    text_input = tokenizer_texto.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer_texto(text_input, return_tensors="pt").to(model_texto.device)

    print("Interpretando tu elección...")
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
        print(f"⚠️ {error_msg}")
        await generar_voz(error_msg)
        await asyncio.sleep(5)
        return await mostrar_menu_voz(model_whisper, model_texto, tokenizer_texto) # Llamada recursiva con los parámetros
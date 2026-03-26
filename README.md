# 🩺 Asistente Multimodal de Salud 

Un asistente virtual de salud impulsado por Inteligencia Artificial, diseñado con un enfoque especial en personas mayores. Este sistema permite interactuar íntegramente por voz, registrar medicamentos mediante fotografías de recetas, leer informes médicos en PDF y gestionar un historial de tratamientos de forma conversacional e intuitiva.

## ✨ Características Principales

* **🗣️ Interacción 100% por voz:** Integración de reconocimiento de voz (Whisper) y síntesis de voz (Edge-TTS) para una comunicación natural sin necesidad de teclear.
* **👁️ Visión Artificial:** Capacidad de leer recetas médicas físicas o cajas de medicamentos usando la cámara/imágenes para extraer automáticamente el nombre, dosis y duración del tratamiento.
* **📄 Lector de Informes (PDF):** Procesamiento de documentos e informes médicos complejos para resumirlos y extraer información clave.
* **🧠 Razonamiento Local:** Uso de modelos LLM Open Source (familia Qwen) para interpretar las peticiones del usuario, clasificar intenciones y responder dudas de salud basándose en el historial médico del paciente.
* **💻 Interfaz de Chat (Colab):** Sistema de burbujas de chat renderizadas en HTML/CSS directamente dentro del cuaderno de Jupyter para un seguimiento visual claro de la conversación.

## 🛠️ Tecnologías y Modelos Utilizados

* **Audio a Texto (STT):** [OpenAI Whisper](https://github.com/openai/whisper) (modelo `small`).
* **Texto a Audio (TTS):** `edge-tts` (Voz neuronal de Microsoft).
* **Motor Lógico y NLP:** [Qwen2.5-3B-Instruct](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct) (Cuantizado a 4-bits).
* **Visión y OCR:** [Qwen2-VL-2B-Instruct](https://huggingface.co/Qwen/Qwen2-VL-2B-Instruct).
* **Entorno de Ejecución:** Diseñado para funcionar sobre Google Colab (con soporte GPU).

## 📁 Estructura del Repositorio

El repositorio está organizado de la siguiente manera:

* `ProyectoAP`/ : Documento principal que contiene la memoria, explicación teórica, objetivos y conclusiones del proyecto.
* `funciones_salud.py` : Script de funciones definidas que contiene toda la lógica de backend, llamadas a los modelos, gestión de la memoria (JSON) y renderizado de la interfaz HTML.
* `Prueba_asistente.ipynb` : Cuaderno de Jupyter principal preparado para cargar `funciones_salud.py` y ejecutar el bucle del asistente final.
* `Fase A.ipynb` / `Fase B.ipynb` : Archivos de trabajo y experimentación donde se desarrollaron y testearon los distintos módulos (audio, visión, prompts) por separado y se definieron y probaron las diferentes funciones aisladamente antes de su integración final.
* * `datos` : Carpeta con ejemplos de recetas (pdf/imagenes) y otros archivos empleados durante el desarrollo y la prueba del asistente.

## 🚀 Cómo ejecutar el proyecto 

Este proyecto está optimizado para ejecutarse en **Google Colab** aprovechando su entorno de GPU gratuita.

1. Sube el archivo `Prueba_asistente.ipynb` a Google Colab.
2. Asegúrate de tener seleccionado un entorno de ejecución con **GPU** (*Entorno de ejecución > Cambiar tipo de entorno de ejecución > T4 GPU*).
3. Configura tu Token de Hugging Face (no es estrictamente necesario pero los modelos se cargarán más rápido):
   * Ve al panel izquierdo de Colab (icono de la 🔑 "Secretos").
   * Añade un nuevo secreto llamado `HF_TOKEN` con tu token de [Hugging Face](https://huggingface.co/).
   * Activa el acceso al cuaderno.
4. Ejecuta la celda de instalación de dependencias (`pip install...`).
5. Sube el archivo `funciones_salud.py` al almacenamiento de sesión o ejecuta la celda correspondiente para cargarlo dinámicamente.
6. Ejecuta la celda de calentamiento del micrófono para otorgar los permisos de grabación en el navegador.
7. Arranca el asistente y empieza a interactuar con él.

## ⚠️ Aviso Legal
*Este asistente es únicamente un proyecto de desarrollo tecnológico e investigación. Las respuestas generadas por los modelos de lenguaje no sustituyen en ningún caso el consejo, diagnóstico o tratamiento de un profesional médico colegiado.*

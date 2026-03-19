import os
import json
import random
import time
import requests
import urllib.parse
from dotenv import load_dotenv
from groq import Groq

# Cargar variables de entorno (para pruebas en local)
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
FB_PAGE_ID = os.getenv("FB_PAGE_ID")
FB_ACCESS_TOKEN = os.getenv("FB_ACCESS_TOKEN")

def generate_content():
    print("[1/4] Generando contenido con Groq...")
    try:
        client = Groq(api_key=GROQ_API_KEY)
        
        
        temas = [
            "datos curiosos de mascotas",
            "tips de cuidados de mascotas",
            "consejos de tenencia responsable",
            "consejos de salud para mascotas",
            "datos de importancia sobre mascotas",
            "humor y situaciones divertidas típicas de los dueños de mascotas",
            "mitos vs realidades de las mascotas"
        ]
        tema_elegido = random.choice(temas)
        print(f" -> Tema elegido para esta publicación: {tema_elegido}")

        prompt = f"""
        Actúa como un experto creador de contenido para una página de Facebook sobre mascotas.
        El objetivo principal de tu texto es generar ALTA INTERACCIÓN (que la gente comente y comparta masivamente).
        El tema principal de este post debe ser estrictamente sobre: {tema_elegido}.
        Genera un post de Facebook amigable, atractivo, con emojis y hashtags.
        INSTRUCCIÓN OBLIGATORIA: Al final del post, SIEMPRE incluye un "Llamado a la acción" (CTA). Por ejemplo, haz una pregunta abierta, pide que etiqueten a un amigo que ame a las mascotas, o diles "¡Sube una foto de tu mascota en los comentarios y dinos cómo se llama!".
        Además, genera un 'image_prompt' en inglés de máximo 150 caracteres para generar una imagen tierna o realista de este tema.
        
        Devuelve estrictamente un objeto JSON con dos claves:
        - "post": El texto del post de Facebook.
        - "image_prompt": El prompt en inglés para la imagen.
        """

        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a helpful assistant that outputs JSON."},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.3-70b-versatile",
            response_format={"type": "json_object"},
            temperature=0.7
        )
        
        content = json.loads(response.choices[0].message.content)
        print(" -> Contenido generado exitosamente.")
        return content["post"], content["image_prompt"]
    except Exception as e:
        print(f"[Error] Falló la generación de contenido: {e}")
        raise

def get_fallback_image(filename="temp_image.jpg"):
    print(" -> [Plan B] Obteniendo una imagen real de mascota como respaldo...")
    
    for attempt in range(1, 4): # Intentar hasta 3 veces en el Plan B
        try:
            animal = random.choice(["perro", "gato"])
            if animal == "perro":
                response = requests.get("https://dog.ceo/api/breeds/image/random", timeout=15)
                response.raise_for_status() # Verifica que la petición fue exitosa (200 OK)
                img_url = response.json()["message"]
            else:
                response = requests.get("https://api.thecatapi.com/v1/images/search", timeout=15)
                response.raise_for_status()
                img_url = response.json()[0]["url"]
                
            img_response = requests.get(img_url, timeout=15)
            img_response.raise_for_status()
            with open(filename, 'wb') as f:
                f.write(img_response.content)
            print(f" -> ¡Plan B exitoso en el intento {attempt}! Imagen guardada localmente como {filename}.")
            return filename
        except Exception as e:
            print(f" -> [Aviso Plan B] Falló el intento {attempt}: {e}")
            time.sleep(2)
            
    raise Exception("Todas las APIs de imágenes (Plan A y Plan B) fallaron.")

def generate_image(prompt, filename="temp_image.jpg", max_retries=3):
    print("[2/4] Generando imagen con Pollinations.ai...")
    encoded_prompt = urllib.parse.quote(prompt)
    
    for attempt in range(1, max_retries + 1):
        try:
            # Añadir un seed aleatorio para obtener imágenes variadas y evitar cache
            seed = random.randint(1, 1000000)
            # Agregamos el parámetro model=flux para buscar un servidor más estable
            image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true&seed={seed}&model=flux"
            
            print(f" -> Intento {attempt} de {max_retries}...")
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()
            
            with open(filename, 'wb') as f:
                f.write(response.content)
            print(f" -> Imagen guardada localmente como {filename}.")
            return filename
        except Exception as e:
            print(f" -> [Advertencia] Falló el intento {attempt}: {e}")
            if attempt == max_retries:
                print("[Aviso] Pollinations.ai está caído. Activando Plan B...")
                return get_fallback_image(filename)
            espera = 5 * attempt # Espera de 5s, 10s...
            print(f" -> Esperando {espera} segundos...")
            time.sleep(espera)

def publish_to_facebook(post_text, image_path):
    print("[3/4] Publicando en Facebook...")
    try:
        url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/photos"
        payload = {
            'message': post_text,
            'access_token': FB_ACCESS_TOKEN
        }
        
        with open(image_path, 'rb') as img:
            files = {'source': img}
            response = requests.post(url, data=payload, files=files)
        
        result = response.json()
        if 'id' in result:
            print(f" -> ¡Publicación exitosa! ID de post/foto: {result['id']}")
        else:
            print(f" -> [Error Facebook API]: {result}")
    except Exception as e:
        print(f"[Error] Falló la publicación en Facebook: {e}")
        raise

def main():
    print("=== Iniciando Bot de Mascotas ===")
    if not all([GROQ_API_KEY, FB_PAGE_ID, FB_ACCESS_TOKEN]):
        print("[Error] Faltan variables de entorno. Verifica tus secrets o .env.")
        return

    image_file = "post_image.jpg"
    try:
        # Paso 1: Generar texto y prompt para la imagen
        post_text, image_prompt = generate_content()
        
        # Paso 2: Generar y descargar la imagen
        generate_image(image_prompt, image_file)
        
        # Paso 3: Publicar en Facebook
        publish_to_facebook(post_text, image_file)
        
        print("[4/4] Proceso finalizado correctamente.")
    except Exception as e:
        print(f"\n[Error Crítico] El bot se detuvo por una excepción: {e}")
    finally:
        # Paso 4: Limpiar archivo local para no ocupar espacio en el runner
        if os.path.exists(image_file):
            os.remove(image_file)
            print(f" -> Limpieza: Archivo temporal {image_file} eliminado.")

if __name__ == "__main__":
    main()
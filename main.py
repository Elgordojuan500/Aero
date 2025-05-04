import discord
from discord.ext import commands
from discord import app_commands
import requests
import os
import textwrap # Para dividir mensajes largos de Gemini
import google.generativeai as genai # Para la API de Gemini
import dotenv # Necesaria para cargar .env en desarrollo local
import random # Para funciones aleatorias
import datetime # Para formatear fechas

# --- Cargar variables de entorno ---
# Esto carga variables desde un archivo .env si existe, ÚTIL PARA DESARROLLO LOCAL.
# En hosting de producción, las variables se configuran directamente en el entorno.
if os.path.exists('.env'):
    print("Cargando variables desde archivo .env")
    dotenv.load_dotenv()

# --- Tu Información Secreta y de Configuración (Versión SEGURA para Open Source) ---

# ¡¡¡IMPORTANTE: Las variables de entorno deben estar configuradas en tu sistema o hosting!!!
# NUNCA pongas tus claves secretas directamente en este archivo.

# Lee el Token de Discord desde la variable de entorno llamada 'DISCORD_BOT_TOKEN'
# Si la variable no existe, os.getenv() retornará None.
TOKEN = os.getenv('DISCORD_BOT_TOKEN')

# PHRASE_API_URL - Lee la URL de la API de frases. Se incluye un default si usas ZenQuotes.
# Si usas otra API, se recomienda configurar la variable de entorno 'PHRASE_API_URL'.
PHRASE_API_URL = os.getenv('PHRASE_API_URL', 'https://zenquotes.io/api/random')
# PHRASE_API_KEY - Si tu API de frases requiere clave, lee la variable de entorno 'PHRASE_API_KEY'.
# # PHRASE_API_KEY = os.getenv('PHRASE_API_KEY')


# GEMINI_API_KEY - Lee la Clave API de Google Generative AI desde la variable de entorno 'GEMINI_API_KEY'.
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# --- Configurar la API de Gemini ---
# Verifica si la clave API está configurada (leída desde el entorno) antes de configurar la librería
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        # Define el modelo. 'gemini-pro' es un modelo general.
        # Asegúrate de que el modelo especificado sea accesible con tu clave API.
        gemini_model = genai.GenerativeModel('gemini-pro') # O el modelo que sepas que funciona
        print("Modelo de Gemini configurado.")
    except Exception as e:
        print(f"Error al configurar la API de Gemini con la clave proporcionada: {e}")
        print("El comando /pregunta no funcionará correctamente.")
        gemini_model = None # Aseguramos que el modelo es None si falla
else:
    # Este mensaje se mostrará si la variable de entorno GEMINI_API_KEY no fue configurada.
    print("Advertencia: GEMINI_API_KEY no configurada.")
    print("Configura la variable de entorno 'GEMINI_API_KEY' para usar el comando /pregunta.")
    gemini_model = None


# --- Preparar el Bot ---
# Necesitamos intents para interactuar con miembros y obtener info del servidor.
intents = discord.Intents.default()
intents.members = True # Necesario para /userinfo y /serverinfo

bot = commands.Bot(command_prefix='!', intents=intents)


# --- Función para obtener frase motivadora ---
# Esta función usa PHRASE_API_URL y opcionalmente PHRASE_API_KEY (leídas del entorno).
def get_phrase():
    """Obtiene una frase motivadora usando una API (Ej: ZenQuotes)."""
    frase_texto = "Una frase motivadora del día."
    # Solo intentar si la URL está configurada en el entorno o se usó el default.
    if PHRASE_API_URL:
        try:
            # Si tu API de frases necesita clave (y la leíste de la variable de entorno PHRASE_API_KEY), úsala aquí.
            # phrase_api_key_val = os.getenv('PHRASE_API_KEY')
            # if phrase_api_key_val:
            #     headers = {"Authorization": f"Bearer {phrase_api_key_val}"} # Ejemplo si la clave va en headers
            #     respuesta_frase = requests.get(PHRASE_API_URL, headers=headers)
            # else:
            #     respuesta_frase = requests.get(PHRASE_API_URL)

            respuesta_frase = requests.get(PHRASE_API_URL) # Llamada simple sin clave en headers/URL

            datos_frase = respuesta_frase.json()

            if respuesta_frase.status_code == 200 and datos_frase:
                # Adapta esto según la ESTRUCTURA JSON de tu API de Frases
                # Este bloque es para APIs que devuelven una lista de dicts (como ZenQuotes)
                if isinstance(datos_frase, list) and len(datos_frase) > 0:
                    frase = datos_frase[0].get('q', 'Una frase motivadora.')
                    autor = datos_frase[0].get('a', 'Desconocido')
                    autor = autor.replace(', type.fit', '')
                    frase_texto = f"Frase del día: \"{frase}\" - {autor}"
                # Este bloque es para APIs que devuelven un solo diccionario
                elif isinstance(datos_frase, dict):
                    # Adapta 'frase' y 'autor' según las claves de tu API si no es ZenQuotes
                    frase = datos_frase.get('frase', 'Una frase motivadora.')
                    autor = datos_frase.get('autor', 'Desconocido')
                    frase_texto = f"Frase del día: \"{frase}\" - {autor}"
                else:
                     print(f"API Frase devolvió respuesta inesperada: {datos_frase}")
                     frase_texto = "No pude obtener una frase motivadora en este momento." # Mensaje genérico si la API falla o responde raro

            else:
                 print(f"Error API Frase ({respuesta_frase.status_code}): {datos_frase}")
                 frase_texto = "No pude obtener una frase motivadora en este momento." # Mensaje genérico si la API falla

        except Exception as e:
            print(f"Error al llamar API Frase: {e}")
            frase_texto = "Ocurrió un error al obtener la frase motivadora." # Mensaje genérico si falla la llamada

    else:
         print("Advertencia: URL de API de Frases no configurada.")
         frase_texto = "La API de frases no está configurada." # Mensaje genérico si la URL falta
    return frase_texto


# --- Evento cuando el bot se conecta ---
@bot.event
async def on_ready():
    """Se ejecuta una vez cuando el bot se conecta."""
    # Verifica que el TOKEN de Discord esté configurado ANTES de intentar conectar.
    # En esta versión segura, TOKEN será None si la variable de entorno no está.
    if TOKEN is None:
        print("Error Crítico: La variable de entorno DISCORD_BOT_TOKEN no está configurada.")
        print("El bot no puede iniciar sin su token. Configúrala.")
        # No salir aquí, el bot ya se conectó si on_ready se llamó.
        # Pero no se sincronizarán comandos y el bot no funcionará correctamente.
        # Idealmente, esta verificación debería estar antes de bot.run().
        # La verificación en __main__ es la importante para evitar bot.run().
        pass # La verificación principal está en __main__

    print(f'¡Bot conectado como {bot.user.name}!')
    print('------')
    print("Sincronizando comandos slash...")
    try:
        # Sincroniza los comandos slash globalmente.
        # Puede tardar hasta 1 hora en aparecer para todos.
        # Para sincronizar solo en un servidor de prueba para velocidad:
        # guild_id = 123456789012345678 # Reemplazar con ID de servidor de prueba
        # guild = discord.Object(id=guild_id)
        # await bot.tree.sync(guild=guild)
        await bot.tree.sync()
        print("Comandos slash sincronizados globalmente.")
    except Exception as e:
        print(f"Error al sincronizar comandos slash: {e}")

# --- Definición de Comandos Slash ---

# Comando /frasemotivadora
@bot.tree.command(name='frasemotivadora', description='Muestra una frase motivadora del día.')
async def frase_command(interaction: discord.Interaction):
    """Responde al comando /frasemotivadora con una frase."""
    await interaction.response.defer() # Indicar que la respuesta está en proceso

    frase_info = get_phrase() # Llama a la función que obtiene la frase

    await interaction.followup.send(frase_info) # Envía el resultado
    print(f"Comando /frasemotivadora ejecutado por {interaction.user.name}") # Usamos .name

# Comando /pregunta
@bot.tree.command(name='pregunta', description='Haz una pregunta a Gemini.')
@app_commands.describe(pregunta='La pregunta que quieres hacerle a Gemini.')
async def pregunta_command(interaction: discord.Interaction, pregunta: str):
    """Responde al comando /pregunta usando la API de Gemini."""
    await interaction.response.defer() # Indicar que la respuesta está en proceso

    print(f"Comando /pregunta '{pregunta}' ejecutado por {interaction.user.name}") # Usamos .name

    # Verifica si el modelo de Gemini se pudo configurar (si la clave API estaba bien)
    if gemini_model is None:
        await interaction.followup.send("Error: La API de Gemini no está configurada correctamente. No puedo responder preguntas.")
        return # Salir si el modelo no está listo

    try:
        # Envía la pregunta a la API de Gemini (versión síncrona)
        response = gemini_model.generate_content(pregunta)

        # Obtiene el texto de la respuesta
        response_text = response.text
        # Reemplazamos el mensaje de easter egg por uno genérico para open source
        if not response_text:
             response_text = "No pude generar una respuesta a eso, o el contenido fue bloqueado por seguridad por la API."
             print(f"Advertencia: Respuesta vacía o bloqueada para la pregunta: '{pregunta}'")

        # Discord tiene un límite de 2000 caracteres por mensaje.
        # Dividimos la respuesta si es más larga.
        if len(response_text) > 2000:
            response_parts = textwrap.wrap(response_text, width=1900, break_long_words=True, replace_whitespace=False)
            await interaction.followup.send("La respuesta es larga, aquí está en partes:")
            for i, part in enumerate(response_parts):
                 await interaction.followup.send(part)
        else:
            await interaction.followup.send(response_text)

    except Exception as e:
        # Captura errores que puedan ocurrir al llamar a la API de Gemini
        print(f"Error al llamar a la API de Gemini: {e}")
        await interaction.followup.send("Ocurrió un error al intentar obtener la respuesta de Gemini.")

# Comando /ping
@bot.tree.command(name='ping', description='Muestra la latencia del bot.')
async def ping_command(interaction: discord.Interaction):
    """Responde al comando /ping con la latencia del bot."""
    latency_ms = round(bot.latency * 1000, 2)
    await interaction.response.send_message(f"Pong! 🏓 Latencia: {latency_ms}ms")
    print(f"Comando /ping ejecutado por {interaction.user.name}")


# Comando /serverinfo
@bot.tree.command(name='serverinfo', description='Muestra información sobre el servidor.')
async def serverinfo_command(interaction: discord.Interaction):
    """Responde al comando /serverinfo con información del servidor."""
    if interaction.guild is None:
        await interaction.response.send_message("Este comando solo funciona en un servidor.", ephemeral=True)
        return

    guild = interaction.guild
    embed = discord.Embed(title=f"Información del Servidor: {guild.name}", color=discord.Color.blue())
    embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
    embed.add_field(name="ID del Servidor", value=guild.id, inline=True)
    embed.add_field(name="Propietario", value=guild.owner.mention if guild.owner else "Desconocido", inline=True)
    embed.add_field(name="Miembros", value=guild.member_count, inline=True)
    embed.add_field(name="Canales", value=f"{len(guild.text_channels)} Texto | {len(guild.voice_channels)} Voz", inline=True)
    embed.add_field(name="Roles", value=len(guild.roles), inline=True)
    embed.add_field(name="Fecha de Creación", value=guild.created_at.strftime("%d/%m/%Y %H:%M:%S"), inline=True)
    embed.add_field(name="Nivel de Boost", value=f"Nivel {guild.premium_tier} ({guild.premium_subscription_count} boosts)", inline=True)

    await interaction.response.send_message(embed=embed)
    print(f"Comando /serverinfo ejecutado por {interaction.user.name}")


# Comando /userinfo
@bot.tree.command(name='userinfo', description='Muestra información sobre un usuario.')
@app_commands.describe(member='El usuario (opcional) para obtener información.')
async def userinfo_command(interaction: discord.Interaction, member: discord.Member = None):
    """Responde al comando /userinfo con información sobre un usuario."""
    user = member or interaction.user

    embed = discord.Embed(title=f"Información del Usuario: {user.name}", color=discord.Color.green())
    embed.set_thumbnail(url=user.display_avatar.url if user.display_avatar else None)
    embed.add_field(name="ID del Usuario", value=user.id, inline=True)
    embed.add_field(name="Nombre en Discord", value=user.global_name if user.global_name else user.name, inline=True)
    embed.add_field(name="Bot?", value=user.bot, inline=True)
    embed.add_field(name="Fecha de Creación de Cuenta", value=user.created_at.strftime("%d/%m/%Y %H:%M:%S"), inline=True)
    if isinstance(user, discord.Member):
         embed.add_field(name="Fecha de Unión al Servidor", value=user.joined_at.strftime("%d/%m/%Y %H:%M:%S"), inline=True)
         roles = [role.name for role in user.roles if role.name != "@everyone"]
         embed.add_field(name=f"Roles ({len(roles)})", value=", ".join(roles) if roles else "Ninguno", inline=False)

    await interaction.response.send_message(embed=embed)
    print(f"Comando /userinfo ejecutado por {interaction.user.name} (sobre {user.name})")


# Comando /dado
@bot.tree.command(name='dado', description='Lanza un dado con un número especificado de caras.')
@app_commands.describe(caras='Número de caras del dado (ej: 6, 20).')
async def dado_command(interaction: discord.Interaction, caras: int):
    """Responde al comando /dado lanzando un dado."""
    if caras < 1:
        await interaction.response.send_message("El número de caras debe ser al menos 1.", ephemeral=True)
        return
    if caras > 1000:
         await interaction.response.send_message("El número de caras es demasiado grande (máx 1000).", ephemeral=True)
         return

    resultado = random.randint(1, caras)
    await interaction.response.send_message(f"Lanzaste un dado de {caras} caras. ¡El resultado es: **{resultado}**!")
    print(f"Comando /dado {caras} ejecutado por {interaction.user.name}. Resultado: {resultado}")


# Comando /elegir
@bot.tree.command(name='elegir', description='Elige una opción al azar de una lista.')
@app_commands.describe(opciones='Opciones separadas por comas (ej: opcion1, opcion2, "opcion 3").')
async def elegir_command(interaction: discord.Interaction, opciones: str):
    """Responde al comando /elegir eligiendo una opción al azar."""
    options_list = [opt.strip() for opt in opciones.split(',') if opt.strip()]

    if len(options_list) < 2:
        await interaction.response.send_message("Necesito al menos dos opciones para elegir.", ephemeral=True)
        return

    eleccion = random.choice(options_list)
    await interaction.response.send_message(f"De las opciones: {', '.join(options_list)}\nMi elección es: **{eleccion}**")
    print(f"Comando /elegir '{opciones}' ejecutado por {interaction.user.name}. Elección: {eleccion}")


# --- Iniciar el Bot ---
if __name__ == "__main__":
    # Verifica que el TOKEN de Discord esté configurado antes de intentar conectar.
    # En esta versión segura, TOKEN será None si la variable de entorno no está.
    if TOKEN is None:
        print("Error: La variable de entorno DISCORD_BOT_TOKEN no está configurada.")
        print("El bot no puede iniciar sin su token. Configura la variable de entorno 'DISCORD_BOT_TOKEN'.")
        exit() # Salir si el token no está configurado.

    # La verificación de GEMINI_API_KEY y PHRASE_API_URL se hace al configurar el modelo/usar el comando.
    # El bot iniciará incluso si esas claves faltan, pero los comandos correspondientes no funcionarán.

    try:
        # Intenta conectar el bot a Discord usando el TOKEN leído del entorno.
        bot.run(TOKEN)
    except discord.errors.LoginFailure:
        print("Error: Token de bot inválido. Verifica que la variable de entorno DISCORD_BOT_TOKEN sea correcta y actual.")
    except Exception as e:
        print(f"Ocurrió un error inesperado al iniciar el bot: {e}")
        print("Asegúrate de que tu hosting tiene conexión a internet y que el bot tiene permisos de Gateway (Intents) correctos.")

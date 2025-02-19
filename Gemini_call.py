import google.generativeai as genai
import google.genai.types as types
from google.ai import generativelanguage as glm
from google.genai.types import FunctionDeclaration, Tool, GenerateContentConfig
from dotenv import load_dotenv
import wave
import pyaudio
import os
from datetime import datetime

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

audio_name_list = ["Salomlashuv.wav", "Suhbat boshlash.wav", "Nima haqida gapirmoqchiligini so'rash.wav", "Rezyume so'rash.wav", "Hozirgi ish.wav", "Ish tajribasi so'rash.wav", "Xayrlashuv.wav"]
currently_playing_audio = None

def play_audio(file_name):
    global currently_playing_audio

    """Berilgan audio faylni ijro etish"""
    file_path = f"D:/Projects/LLMs/HRRecordedAudios/{file_name}"
    if not os.path.exists(file_path):
        print(f"{file_path} doesn't exist!")

    try:
        wf = wave.open(file_path, 'rb')

        p = pyaudio.PyAudio()

        stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                channels=wf.getnchannels(),
                rate=wf.getframerate(),
                output=True)
        currently_playing_audio = file_path
        
        chunk = 1024  # Har safar o'qiladigan audio hajmi
        data = wf.readframes(chunk)

        while data:
            stream.write(data)
            data = wf.readframes(chunk)

    finally:
        stream.close()
        p.terminate()
        wf.close()
        return {"status": "error", "message": "Audio fayl topilmadi"}
    
function_declarations = [
    {
        "name": "play_audio",
        "description": "Nomi berilgan audio faylni topib ijro etadi",
        "parameters": {
            "type": "object",
            "properties": {
                "audio_file": {
                    "type": "string",
                    "description": "Ijro etiladigan audio nomi"
                }
            },
            "required": ["audio_file"]
        }
    }
]

def gemini_chat():
    initial_template = f"""
        You are an AI assistant that plays given audio. Available audio: {', '.join(audio_name_list)}
        Key rules:
        1. Call 'play_audio(audio_file="file_path")' for appropriate files
        2. Don't play same audio twice
        3. Only text response if no audio is available
        4. Company info: brief (1-2 sentences) about 'AI is Future' LLC
    """
    
    genai.configure(api_key=api_key)

    generation_config = {
        "temperature": 1,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 8192,
        "response_mime_type": "text/plain",
    }
    
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash",
        generation_config=generation_config,
        tools=[function_declarations],
        system_instruction={"role": "cache_control", "parts": {"caching_enabled": True}}
    )
    
    cache_manager = model.cached_content
    
    # Dastlabki xabarni tiizm xabari sifatida berish
    chat_session = model.start_chat(history=[
        {"role": "user", "parts": [{"text": "Salom, men sizdan yordam so'ramoqchiman."}]},
        {"role": "model", "parts": [{"text": initial_template}]}
    ])
    
    while True:
        user_input = input("Siz: ")
        
        if not user_input.strip():
            print("Iltimos, xabar kiriting!")
            continue
            
        if user_input.lower() in ["chiqish", "exit", "tugatish"]:
            print("Suhbat tugadi!")
            break
        
        before = datetime.now()
        
        try:
            response = chat_session.send_message(user_input, stream=True)
            then = datetime.now()
            
            print(f"Javob vaqti: {then - before}")
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                print(response.usage_metadata)
            
            response_content = ""
            has_function_call = False
            
            for chunk in response:
                if hasattr(chunk.candidates[0].content.parts[0], 'function_call') and chunk.candidates[0].content.parts[0].function_call:
                    function_call = chunk.candidates[0].content.parts[0].function_call
                    audio_file = function_call.args["audio_file"]
                    play_audio(audio_file)
                    has_function_call = True
                else:
                    content = chunk.text if hasattr(chunk, 'text') else ''
                    response_content += content
                    print(content, end='')
            # print(chat_session.history)
            
            if response_content and not has_function_call:
                print()  # Yangi qatorga o'tish
                
        except Exception as e:
            print(f"Xatolik yuz berdi: {e}")

if __name__ == "__main__":
    gemini_chat()
    

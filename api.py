##Vibecoded eng ver that returns audio from http://127.0.0.1:8000/synthesize as binary blob
#https://github.com/index-tts/index-tts/pull/131
#orig auth https://github.com/itltf512116
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, Body, Query, Request # Import Request
from fastapi.responses import FileResponse, JSONResponse, Response
import os
import time
# import uvicorn # No longer needed if using command line uvicorn
from indextts.infer import IndexTTS
import tempfile
import hashlib
from typing import Dict
# import base64 # Not used in this version
from pydantic import BaseModel

app = FastAPI(title="IndexTTS API")

# Initialize the TTS model
# Only initialize once when the app starts
tts = IndexTTS(model_dir="checkpoints", cfg_path="checkpoints/config.yaml")


# Ensure the 'prompts' directory exists
prompts_dir = "prompts" # Define the directory for stored prompts
os.makedirs(prompts_dir, exist_ok=True)

# Helper to generate a deterministic filename hash for caching
def generate_cache_filename(ref_audio_path: str, text: str) -> str:
    """Generates a deterministic filename hash based on prompt and text."""
    # Create a unique string from prompt filename and text
    unique_string = f"{ref_audio_path}_{text}"
    # Hash the string
    hash_object = hashlib.md5(unique_string.encode())
    return f"synthesized-{hash_object.hexdigest()}.wav"

@app.api_route("/tts", methods=["GET", "POST"]) # Accept both GET and POST
async def synthesize_speech(request: Request): # Use Request object to access parameters
    """
    Synthesize speech from text using a pre-stored audio prompt file.
    Accepts GET or POST requests with 'ref_audio_path' and 'text' parameters.
    Returns audio as a binary WAV response.
    """
    # Extract parameters from either query (GET) or form (POST)
    if request.method == "POST":
        form_data = await request.form()
        ref_audio_path = form_data.get("ref_audio_path")
        text = form_data.get("text")
    else: # GET
        ref_audio_path = request.query_params.get("ref_audio_path")
        text = request.query_params.get("text")

    # Validate required parameters
    if not ref_audio_path:
        return JSONResponse(status_code=400, content={"message": "'ref_audio_path' parameter is required."})
    if not text:
        return JSONResponse(status_code=400, content={"message": "'text' parameter is required."})
    
    # Construct the full path to the prompt file
    prompt_path = os.path.join(prompts_dir, ref_audio_path)

    # Basic security check: ensure the file exists and is within the prompts directory
    if not os.path.exists(prompt_path):
        return JSONResponse(status_code=404, content={"message": f"Prompt file not found: {ref_audio_path}"})

    # Optional but recommended: further validation to prevent directory traversal attacks
    try:
        if not os.path.realpath(prompt_path).startswith(os.path.realpath(prompts_dir)):
             return JSONResponse(status_code=400, content={"message": "Invalid prompt filename provided."})
    except Exception as e:
        print(f"Path validation error: {e}")
        return JSONResponse(status_code=500, content={"message": "Internal path validation error."})

    # --- Caching Logic ---
    cache_filename = generate_cache_filename(ref_audio_path, text)
    cached_output_path = os.path.join(tmp_dir, cache_filename)

    # Check if cached file exists and is reasonably recent (e.g., within 1 hour)
    cache_duration_seconds = 3600 # 1 hour
    if os.path.exists(cached_output_path):
        mod_time = os.path.getmtime(cached_output_path)
        if time.time() - mod_time < cache_duration_seconds:
            print(f"Returning cached file: {cached_output_path}")
            # Use FileResponse for direct file sending, which is often more efficient
            return FileResponse(cached_output_path, media_type="audio/wav")
        else:
            # Cache is old, remove it
            try:
                os.unlink(cached_output_path)
                print(f"Expired cache file removed: {cached_output_path}")
            except Exception as e:
                 print(f"Error removing expired cache file {cached_output_path}: {e}")

    # --- Synthesis if not cached ---
    temp_output_file = None
    try:
        # Use the cache path directly as the output path for synthesis
        # This saves a copy operation later
        output_path = cached_output_path
        # Ensure the tmp directory exists
        os.makedirs(tmp_dir, exist_ok=True)


        # Perform inference
        print(f"Synthesizing text: '{text[:50]}...' with prompt file: {prompt_path}")
        # Using infer_fast for potentially better performance on longer texts
        # Pass the constructed prompt_path and the cache path as output_path
        tts.infer_fast(audio_prompt=prompt_path, text=text, output_path=output_path)
        print(f"Synthesis complete. Output saved to: {output_path}")

        # Return the audio as a file response directly from the saved file
        return FileResponse(output_path, media_type="audio/wav")

    except Exception as e:
        print(f"An error occurred during synthesis: {e}")
        # Attempt to clean up the failed output file
        if os.path.exists(output_path):
             try:
                 os.unlink(output_path)
                 print(f"Cleaned up failed output file: {output_path}")
             except Exception as cleanup_e:
                 print(f"Error cleaning up failed output file {output_path}: {cleanup_e}")
        return JSONResponse(status_code=500, content={"message": f"Internal server error: {e}"})
    # Note: No 'finally' cleanup needed for the output file when using FileResponse
    # FastAPI handles sending the file and the OS manages temporary files if they were truly temporary.
    # Here, we're saving to a semi-permanent cache path, so explicit cleanup is handled by the cache logic or a separate process if needed.

# Ensure the tmp directory exists for caching
tmp_dir = Path(f'{os.path.dirname(__file__)}/tmp').as_posix() # Define tmp_dir relative to the script
os.makedirs(tmp_dir, exist_ok=True)


if __name__ == "__main__":
    import uvicorn
    host = "127.0.0.1"
    port = 8000
    print(f'\n启动api: http://{host}:{port}\n')
    uvicorn.run(app, host=host, port=port)
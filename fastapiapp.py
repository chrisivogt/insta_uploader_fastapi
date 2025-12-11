from fastapi import FastAPI, File, Form, UploadFile, HTTPException, Depends
from dataclasses import dataclass
import subprocess
import sys
from insta import login_user
from pydantic import BaseModel
import shutil
import uuid
from pathlib import Path
from tempfile import NamedTemporaryFile
from moviepy import *

app = FastAPI()

# --- 1. Global Storage ---
# This dictionary will hold the live client objects.
# Structure: { "username": client_object }
active_sessions = {}

class LoginRequest(BaseModel):
    username: str

class UploadRequest(BaseModel):
    username: str
    filepath: str
    caption: str

@dataclass
class UploadForm:
    caption: str = Form(...) # This maps to 'text'
    image: UploadFile = File(...) # This maps to 'image'
    username: str = Form(...) # This maps to 'text'

class LikeRequest(BaseModel):
    username: str
    n: int

@app.post("/login")
def login(data: LoginRequest):
    cl = login_user(data.username)
    print(f"Logged in successfully. User ID: {cl.user_id}")
    active_sessions[data.username] = cl
    return {"status": "success", "user_id": cl.user_id}


@app.post("/upload_image")
async def upload_image(form_data: UploadForm = Depends()):
    cl = active_sessions.get(form_data.username)
    with NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
        # Efficiently copy the upload stream to the temp file
        shutil.copyfileobj(form_data.image.file, tmp)
        tmp_path = Path(tmp.name)

    try:
        # Call the clients upload method
        cl.photo_upload(path=tmp_path, caption=form_data.caption, location=None)
        print(form_data.caption)
        return {"status": "success", "message": "Image uploaded to instagram"}
    except Exception as e:
        # Handle library errors gracefully
        raise HTTPException(status_code=500, details=str(e))

    finally:
        # CLEANUP: Vital step
        # Delete the temp file to prevent disk space leaks
        tmp_path.unlink(missing_ok=True)


@app.post("/like_top_posts")
def like_top_posts(data: LikeRequest):
    cl = active_sessions.get(data.username)

    if not cl:
        pass

    # Implement like via cl
    
    return {"status": "likes_performed", "for_user": cl.user_id}


@app.post("/logout")
def logout(data: LoginRequest):
    if data.username in active_sessions:
        del active_sessions[data.username]
        return {"status": "logout", "message": f"Sessions for {data.username} removed."}

    return {"status": "not_found", "message": "No active session found to close"}


@app.post("/generate_reel")
async def generate_reel(
    image: UploadFile = File(...), 
    audio: UploadFile = File(...)
):
    """
    Receives an Image and Audio file.
    Creates a Reel.
    Saves it locally to disk.
    Returns the file path.
    """
    UPLOAD_DIR = "temp_uploads"
    OUTPUT_DIR = "completed_reels"
    # Ensure directories exist
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 1. Create unique filenames to avoid collision
    request_id = str(uuid.uuid4())
    image_ext = image.filename.split(".")[-1]
    audio_ext = audio.filename.split(".")[-1]
    
    local_image_path = os.path.join(UPLOAD_DIR, f"{request_id}.{image_ext}")
    local_audio_path = os.path.join(UPLOAD_DIR, f"{request_id}.{audio_ext}")
    local_output_path = os.path.join(OUTPUT_DIR, f"reel_{request_id}.mp4")

    try:
        # 2. Save incoming files to disk
        with open(local_image_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
            
        with open(local_audio_path, "wb") as buffer:
            shutil.copyfileobj(audio.file, buffer)

        # 3. MoviePy Processing Logic
        print(f"Processing reel {request_id}...")
        
        # Load Audio
        audio_clip = AudioFileClip(local_audio_path)
        
        # Load Image & Set Duration
        image_clip = ImageClip(local_image_path).with_duration(audio_clip.duration)
        
        # Resize logic (1080x1920)
        # Resize height to 1920, maintaining aspect ratio
        final_clip = image_clip.resized(height=1920)
        # Center the image
        final_clip = final_clip.with_position("center")
        # Crop width to 1080
        final_clip = final_clip.cropped(x1=final_clip.w/2 - 540, 
                                        y1=0, 
                                        width=1080, 
                                        height=1920)
        
        # Combine
        final_video = final_clip.with_audio(audio_clip)
        
        # Write File
        # preset='ultrafast' creates the video faster (good for APIs)
        final_video.write_videofile(
            local_output_path, 
            fps=24, 
            codec="libx264", 
            audio_codec="aac",
            preset="ultrafast",
            logger=None # Silence the progress bar logs
        )
        
        # 4. Clean up input files (Optional)
        os.remove(local_image_path)
        os.remove(local_audio_path)

        return {
            "status": "success", 
            "message": "Reel created successfully",
            "file_path": os.path.abspath(local_output_path)
        }

    except Exception as e:
        # Clean up if something failed
        if os.path.exists(local_image_path): os.remove(local_image_path)
        if os.path.exists(local_audio_path): os.remove(local_audio_path)
        raise HTTPException(status_code=500, detail=str(e))

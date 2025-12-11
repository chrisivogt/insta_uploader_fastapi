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

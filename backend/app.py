from fastapi import FastAPI, UploadFile, File, Form, HTTPException,Request, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, HTMLResponse
import shutil
import os
import json
from datetime import datetime
from typing import List, Optional
import uuid
from pydantic import BaseModel
from fastapi.templating import Jinja2Templates


from utils import transcribe_audio, process_image
from llm import generate_event_metadata, generate_post, edit_post

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)


# Mount static files
app.mount("/static", StaticFiles(directory="../frontend/static"), name="static")
app.mount("/css", StaticFiles(directory="../frontend/css"), name="css")
app.mount("/js", StaticFiles(directory="../frontend/js"), name="js")
app.mount("/event_data", StaticFiles(directory="../backend/event_data"), name="event_data")
# Ensure the event_data directory exists
os.makedirs("event_data", exist_ok=True)

class ChatMessage(BaseModel):
    content: str
    role: str = "user"

class PostEditRequest(BaseModel):
    event_id: str
    messages: List[ChatMessage]
    
class GeneratePostRequest(BaseModel):
    event_id: str

@app.get("/events")
async def get_events():
    """Retrieve all events"""
    events = []
    
    if os.path.exists("event_data"):
        for event_dir in os.listdir("event_data"):
            event_path = os.path.join("event_data", event_dir)
            if os.path.isdir(event_path):
                metadata_path = os.path.join(event_path, "metadata.json")
                if os.path.exists(metadata_path):
                    with open(metadata_path, "r") as f:
                        metadata = json.load(f)
                        events.append({
                            "id": event_dir,
                            "topic": metadata.get("topic", "Untitled Event"),
                            "description": metadata.get("description", "No description"),
                            "date": metadata.get("date", "Unknown date")
                        })
    
    # Sort events by date (newest first)
    events.sort(key=lambda x: x.get("date", ""), reverse=True)
    return events

@app.get("/events/{event_id}")
async def get_event(event_id: str):
    """Retrieve a specific event by ID"""
    event_path = os.path.join("event_data", event_id)
    
    if not os.path.exists(event_path):
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Load metadata
    metadata_path = os.path.join(event_path, "metadata.json")
    if not os.path.exists(metadata_path):
        raise HTTPException(status_code=404, detail="Event metadata not found")
    
    with open(metadata_path, "r") as f:
        metadata = json.load(f)
    
    # Load notes
    notes_path = os.path.join(event_path, "notes.txt")
    notes = ""
    if os.path.exists(notes_path):
        with open(notes_path, "r", encoding="utf-8") as f:
            notes = f.read()
    
    # Load transcriptions
    transcriptions_path = os.path.join(event_path, "transcriptions.txt")
    transcriptions = ""
    if os.path.exists(transcriptions_path):
        with open(transcriptions_path, "r",encoding="utf-8") as f:
            transcriptions = f.read()

    # Get image paths
    image_dir = os.path.join(event_path, "images")
    images = []
    if os.path.exists(image_dir):
        images = [f"/event_data/{event_id}/images/{img}" for img in os.listdir(image_dir) if img.endswith((".jpg", ".jpeg", ".png"))]
    
    # Load generated post if available
    post_path = os.path.join(event_path, "generated_post.txt")
    generated_post = ""
    if os.path.exists(post_path):
        with open(post_path, "r",encoding="utf-8") as f:
            generated_post = f.read()
    return {
        "id": event_id,
        "metadata": metadata,
        "notes": notes,
        "transcriptions": transcriptions,
        "images": images,
        "generated_post": generated_post
    }

@app.post("/events/new")
async def create_event(
    notes: str = Form(""),
    audio_files: List[UploadFile] = File([]),
    images: List[UploadFile] = File([])
):
    """Create a new event with notes, audio transcription, and images"""
    try:
        # Generate a unique ID for the event
        event_id = str(uuid.uuid4())
        event_dir = os.path.join("event_data", event_id)
        os.makedirs(event_dir, exist_ok=True)
        
        # Save notes
        notes_path = os.path.join(event_dir, "notes.txt")
        with open(notes_path, "w", encoding='utf-8') as f:
            f.write(notes)
        
        # Process audio files if provided 
        transcriptions = []
        if audio_files:
            audio_dir = os.path.join(event_dir, "audio")
            os.makedirs(audio_dir, exist_ok=True)
            
            for i, audio in enumerate(audio_files):
                audio_path = os.path.join(audio_dir, f"audio_{i}.wav")
                with open(audio_path, "wb") as f:
                    shutil.copyfileobj(audio.file, f)
                
                transcription = transcribe_audio(audio_path)
                transcriptions.append(f"Recording {i+1}:\n{transcription}\n")
        
        transcriptions_text = "\n".join(transcriptions)
        if transcriptions:
            transcription_path = os.path.join(event_dir, "transcriptions.txt")
            with open(transcription_path, "w", encoding='utf-8') as f:
                f.write(transcriptions_text)
        
        # Process images
        if images:
            image_dir = os.path.join(event_dir, "images")
            os.makedirs(image_dir, exist_ok=True)
            
            for i, image in enumerate(images):
                image_path = os.path.join(image_dir, f"image_{i}.{image.filename.split('.')[-1]}")
                with open(image_path, "wb") as f:
                    shutil.copyfileobj(image.file, f)
                process_image(image_path)

        print("LLM processing started...")
        content = f"Notes: {notes}\nTranscriptions:\n{transcriptions_text}"
        
        try:
            metadata = await generate_event_metadata(content)
            if not isinstance(metadata, dict):
                metadata = {"topic": "Untitled Event", "description": "No description"}
        except Exception as e:
            print(f"Error in LLM processing: {e}")
            metadata = {"topic": "Untitled Event", "description": "No description"}

        metadata["date"] = datetime.now().strftime("%Y-%m-%d")
        
        metadata_path = os.path.join(event_dir, "metadata.json")
        with open(metadata_path, "w") as f:
            json.dump(metadata, f)
        
        print("LLM processing completed...")
        
        response_data = {
            "id": event_id,
            "topic": metadata.get("topic", "Untitled Event"),
            "description": metadata.get("description", "No description"),
            "date": metadata.get("date")
        }
        
        return JSONResponse(
            content=response_data,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Content-Type": "application/json"
            }
        )
        
    except Exception as e:
        print(f"Error creating event: {e}")
        return JSONResponse(
            content={"detail": str(e)},
            status_code=500,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Content-Type": "application/json"
            }
        )

@app.post("/events/generate-post")
async def generate_post_endpoint(request: GeneratePostRequest):
    """Generate a LinkedIn post for an event"""
    event_id = request.event_id
    event_path = os.path.join("event_data", event_id)
    
    if not os.path.exists(event_path):
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Load metadata
    metadata_path = os.path.join(event_path, "metadata.json")
    with open(metadata_path, "r") as f:
        metadata = json.load(f)
    
    # Load notes
    notes_path = os.path.join(event_path, "notes.txt")
    notes = ""
    if os.path.exists(notes_path):
        with open(notes_path, "r") as f:
            notes = f.read()
    
    # Load transcriptions
    transcriptions_path = os.path.join(event_path, "transcriptions.txt")
    transcriptions = ""
    if os.path.exists(transcriptions_path):
        with open(transcriptions_path, "r") as f:
            transcriptions = f.read()
    
    # Generate post using llm
    post_content = await generate_post(metadata, notes, transcriptions)
    
    # Save generated post
    post_path = os.path.join(event_path, "generated_post.txt")
    with open(post_path, "w", encoding="utf-8") as f:
        f.write(post_content)
    
    return JSONResponse(
        content={"content": post_content},
        status_code=200
    )

@app.post("/events/edit-post")
async def edit_post_endpoint(request: PostEditRequest):
    """Edit a LinkedIn post based on user feedback"""
    event_id = request.event_id
    messages = request.messages
    
    event_path = os.path.join("event_data", event_id)
    if not os.path.exists(event_path):
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Load generated post if exists
    post_path = os.path.join(event_path, "generated_post.txt")
    current_post = ""
    if os.path.exists(post_path):
        with open(post_path, "r", encoding="utf-8") as f:
            current_post = f.read()
    
    # Load metadata
    metadata_path = os.path.join(event_path, "metadata.json")
    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)
    
    # Edit post (use async version)
    edited_post = await edit_post(current_post, metadata, messages)
    
    # Save edited post
    with open(post_path, "w",encoding="utf-8") as f:
        f.write(edited_post)
    
    return {"content": edited_post}

@app.post("/events/save-post")
async def save_post(event_id: str = Body(...), content: str = Body(...)):
    """Save manually edited post content"""
    event_path = os.path.join("event_data", event_id)
    
    if not os.path.exists(event_path):
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Save post content
    post_path = os.path.join(event_path, "generated_post.txt")
    with open(post_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    return {"success": True}

# @app.post("/upload-audio")
# async def upload_audio(file: UploadFile = File(...)):
#     """Endpoint to handle audio uploads and return transcription"""
#     # Create temp directory if it doesn't exist
#     os.makedirs("temp", exist_ok=True)
    
#     # Save the uploaded file
#     file_path = os.path.join("temp", file.filename)
#     with open(file_path, "wb") as f:
#         shutil.copyfileobj(file.file, f)
    
#     # Transcribe audio
#     transcription = transcribe_audio(file_path)
    
#     # Clean up
#     os.remove(file_path)
#     print("Transcription:", transcription)
#     return {"transcription": transcription}

# Serve static files for event images
app.mount("/event_data", StaticFiles(directory="event_data"), name="event_data")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, port=8000)  # host="0.0.0.0",
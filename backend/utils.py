import os
from typing import Optional
from PIL import Image
import io
from faster_whisper import WhisperModel
import torch

# Set device to GPU or CPU
device = "cuda" if torch.cuda.is_available() else "cpu"
compute_type = "float16" if device == "cuda" else "int8"

# Initialize the Whisper model for transcription
model_size = "large-v3"
whisper_model = WhisperModel(model_size, device=device, compute_type="float16")

def transcribe_audio(audio_path: str) -> str:
    """
    Transcribe audio file using faster-whisper
    
    Args:
        audio_path: Path to the audio file
        
    Returns:
        Transcribed text
    """
    try:
        segments, _ = whisper_model.transcribe(audio_path, beam_size=5)
        
        # Collect all segments
        transcription = ""
        for segment in segments:
            transcription += segment.text + " "
        
        return transcription.strip()
    except Exception as e:
        print(f"Error transcribing audio: {e}")
        return f"Error transcribing audio: {str(e)}"

def process_image(image_path: str, max_size: int = 1200) -> None:
    """
    Process image file (resize if needed)
    
    Args:
        image_path: Path to the image file
        max_size: Maximum dimension (width or height)
    """
    try:
        with Image.open(image_path) as img:
            # Resize if any dimension exceeds max_size
            if img.width > max_size or img.height > max_size:
                # Calculate aspect ratio
                aspect_ratio = img.width / img.height
                
                if img.width > img.height:
                    new_width = max_size
                    new_height = int(max_size / aspect_ratio)
                else:
                    new_height = max_size
                    new_width = int(max_size * aspect_ratio)
                
                # Resize image
                resized_img = img.resize((new_width, new_height), Image.LANCZOS)
                
                # Save resized image
                resized_img.save(image_path)
    except Exception as e:
        print(f"Error processing image: {e}")

def get_file_extension(filename: str) -> str:
    """Get file extension from filename"""
    return os.path.splitext(filename)[1].lower()

def is_valid_image(file_extension: str) -> bool:
    """Check if file extension is a valid image format"""
    valid_extensions = ['.jpg', '.jpeg', '.png', '.gif']
    return file_extension in valid_extensions

def is_valid_audio(file_extension: str) -> bool:
    """Check if file extension is a valid audio format"""
    valid_extensions = ['.mp3', '.wav', '.m4a', '.ogg']
    return file_extension in valid_extensions
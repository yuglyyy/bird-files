# Import libraries
import gradio as gr
import os
import shutil
import io
import sys
from ultralytics import YOLO
import pandas as pd
import librosa
import matplotlib.pyplot as plt
import numpy as np
from pydub import AudioSegment
from PIL import Image, ImageDraw, ImageFont
import zipfile

def save_spectrogram_from_audio(audio_file):
    """
    Generate a spectrogram image from an audio file and save it to the Images folder."
    """

    y, sr = librosa.load(audio_file, sr=16000)
    
    # Create the output path for the image
    output_image_path = audio_file.replace('Audios', 'Images').replace(".WAV", ".PNG")
    
    # Ensure the output folder exists
    os.makedirs(os.path.dirname(output_image_path), exist_ok=True)
    
    # Define the frequency range
    fmin = 1
    fmax = 16000

    fig, ax = plt.subplots(figsize=(12, 6))  # Set the background color to black
    D = librosa.amplitude_to_db(librosa.stft(y), ref=np.max)
    librosa.display.specshow(D, sr=sr, x_axis="time", y_axis="log", fmin=fmin, fmax=fmax, ax=ax)  # Specify frequency range
    ax.axis('off')  # Remove axes

    # Save the figure using the output_image_path
    fig.savefig(output_image_path, bbox_inches='tight', pad_inches=0, transparent=True)
    
    # Close the figure to release memory resources
    plt.close(fig)

    return output_image_path

def transform_coordinates_to_seconds(audio_path, prediccion_txt_path):
    image_path = audio_path.replace('Audios', 'Images').replace(".WAV", ".PNG")

    # Read image size
    with Image.open(image_path) as img:
        WIDTH, HEIGHT = img.size
    
    # Read predictions file
    with open(prediccion_txt_path, 'r') as file:
        predictions = file.readlines()
    
    # Load original audio
    audio = AudioSegment.from_wav(audio_path)
    
    # Audio duration in ms
    audio_duration_ms = len(audio)
    # To seconds
    audio_duration_sec = audio_duration_ms / 1000

    df = pd.DataFrame(columns=["x_center", "width", "IMG_WIDTH", "IMG_HEIGHT", "Start Time", "End Time", "Score"])
    
    # Process each prediction
    for i, line in enumerate(predictions):
        _, x_center, _, width, _, score = map(float, line.split())
        
        # Denormalize coordinates
        x_center_desnorm = x_center * WIDTH
        width_desnorm = width * WIDTH

        # Convert image coordinates to audio seconds
        start_sec = (x_center_desnorm - width_desnorm / 2) * 60 / WIDTH
        end_sec = (x_center_desnorm + width_desnorm / 2) * 60 / WIDTH
        
        # Ensure the segment is within the audio duration
        start_sec = max(0, min(start_sec, audio_duration_sec))
        end_sec = max(0, min(end_sec, audio_duration_sec))

        df.loc[i] = [x_center, width, WIDTH, HEIGHT, start_sec, end_sec, score]

    return df

def draw_bounding_boxes(image_path, df):
    with Image.open(image_path) as img:
        draw = ImageDraw.Draw(img)
        font = ImageFont.load_default()

        for _, row in df.iterrows():
            x_center = row['x_center'] * img.width
            width = row['width'] * img.width
            x1 = x_center - width / 2
            x2 = x_center + width / 2
            y1 = 0
            y2 = img.height

            draw.rectangle([x1, y1, x2, y2], outline="red", width=3)
            draw.text((x1, y1), f"{row['Score']:.2f}", fill="red", font=font, stroke_fill="black", stroke_width=1)

        output_image_path = image_path.replace(".PNG", "_bbox.PNG")
        img.save(output_image_path)

    return output_image_path

def capture_console_output(func, *args, **kwargs):
    """Captures the console output of a function call and returns it as a string."""
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    
    try:
        func(*args, **kwargs)
        output = sys.stdout.getvalue()
    finally:
        sys.stdout = old_stdout
    
    return output

def process_audio(audio_path):
    """Processes an uploaded audio file for bird song detection and returns the console output."""
    # Load YOLO model
    model = YOLO("Models/Bird Song Detector/weights/best.pt")
    
    # Clean output folder
    shutil.rmtree('runs', ignore_errors=True)
    
    # Convert audio to spectrogram image
    image_path = save_spectrogram_from_audio(audio_path)
    
    # Perform detection
    model(image_path, save_txt=True, save_conf=True)
    
    # Extract predictions
    audio_name = os.path.basename(audio_path).replace(".WAV", "")
    predictions_txt = f"runs/detect/predict/labels/{audio_name}.txt"
    
    if os.path.exists(predictions_txt):
        df = transform_coordinates_to_seconds(audio_path, predictions_txt)
        output_text = ""
        for i, row in df.iterrows():
            output_text += f"Detection {i+1}: From {row['Start Time']:.2f} to {row['End Time']:.2f} seconds (Score: {row['Score']:.2f})\n"
        df.to_csv(f"runs/detect/predict/labels/{audio_name}_segments.csv", index=False)
        
        # Draw bounding boxes on the spectrogram
        bbox_image_path = draw_bounding_boxes(image_path, df)
        
        return output_text, bbox_image_path
    else:
        return "No detections found.", None

def create_and_download_segments(audio_path):
    audio_name = os.path.basename(audio_path).replace(".WAV", "")
    segments_csv = f"runs/detect/predict/labels/{audio_name}_segments.csv"
    if not os.path.exists(segments_csv):
        return None

    df = pd.read_csv(segments_csv)
    audio = AudioSegment.from_wav(audio_path)
    segment_paths = []

    for i, row in df.iterrows():
        start_ms = row['Start Time'] * 1000
        end_ms = row['End Time'] * 1000
        segment = audio[start_ms:end_ms]
        segment_path = f"runs/detect/predict/segments/{audio_name}_{row['Start Time']:.2f}_{row['End Time']:.2f}_{row['Score']:.2f}.wav"
        os.makedirs(os.path.dirname(segment_path), exist_ok=True)
        segment.export(segment_path, format="wav")
        segment_paths.append(segment_path)

    zip_path = f"runs/detect/predict/{audio_name}_segments.zip"
    with zipfile.ZipFile(zip_path, 'w') as zipf:  # Use zipfile.ZipFile
        for segment_path in segment_paths:
            zipf.write(segment_path, os.path.basename(segment_path))

    return zip_path

# Create Gradio Interface
demo = gr.Blocks()

with demo:
    gr.Markdown("# Bird Song Detector")
    gr.Markdown("Upload an audio file (WAV format) to detect bird songs using the Bird Song Detector from BIRDeep model.")
    
    with gr.Row():
        audio_input = gr.File(label="Upload WAV File")
        output_text = gr.Textbox(label="Detection Results")
    
    spectrogram_output = gr.Image(label="Spectrogram with Detections")
    
    with gr.Row():
        detect_button = gr.Button("Detect Bird Songs", variant="primary")
        detect_button.click(process_audio, inputs=audio_input, outputs=[output_text, spectrogram_output])
        
        download_button = gr.Button("Generate Segments")

    download_output = gr.File()
    download_button.click(create_and_download_segments, inputs=audio_input, outputs=download_output)

if __name__ == "__main__":
    demo.launch(share=True)

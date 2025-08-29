# Bird-Song-Detector

This repository provides a pipeline to detect bird vocalizations from audio recordings using a YOLOv8-based spectrogram detector.

## Setup Instructions

1. **Clone the repository**

   ```bash
   git clone https://github.com/mohrsalt/Bird-Song-Detector.git
   cd Bird-Song-Detector
   ```

2. **Create and activate the Conda environment**

   ```bash
   conda env create -f birdsongenv.yml
   conda activate birdsongenv
   ```

## Running Inference on a Single Audio File

Run the following command to perform inference on one audio file:

```bash
python3 /home/FYP/mohor001/Bird-Song-Detector/Code/predict_on_audio.py
```

> ** Note:**  
> - Edit `Code/predict_on_audio.py` to update paths.  
> - Use `Ctrl + F` to search for occurrences of `"mohor001"` and replace them with your local path.  
> - Ensure that both the model checkpoint and input audio file paths are correctly set.

## Directory Overview

- **Model Checkpoint:**  
  `Bird-Song-Detector/Models/Bird Song Detector/weights/best.pt`

- **Audio Samples:**  
  `Bird-Song-Detector/Data/Audios/`

## Output

The script generates predictions including detected bounding boxes and class scores, as well as segmented audio clips packaged into a zip file. All outputs are formed in the Bird-Song-Detector/Code/runs folder.

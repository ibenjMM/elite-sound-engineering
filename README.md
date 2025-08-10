# Simple Audio Loudness Normalizer

This is a simple web-based tool to normalize the loudness of audio files. It uses Flask for the web framework, pydub for audio manipulation, and pyloudnorm for loudness measurement.

The application normalizes uploaded `.wav` files to a target of -14 LUFS (Loudness Units Full Scale), a common standard for streaming platforms.

## Features

- Web interface for uploading audio files.
- Loudness normalization to -14 LUFS.
- Download the processed audio file.
- Supports `.wav` file format.

## Setup and Installation

Follow these steps to set up and run the project on your local machine.

### 1. Clone the repository (or download the source code)

If you have git installed, you can clone the repository:
```bash
git clone <repository-url>
cd <repository-name>
```
Otherwise, just download and extract the source code into a directory.

### 2. Create a Virtual Environment

It is highly recommended to use a virtual environment to keep the project dependencies isolated.

**On macOS and Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**On Windows:**
```bash
python -m venv venv
.\venv\Scripts\activate
```

### 3. Install Dependencies

Install all the required Python packages using pip and the `requirements.txt` file.

```bash
pip install -r requirements.txt
```

This will install Flask, pydub, pyloudnorm, numpy, and soundfile.

**Note on pydub:** `pydub` requires an audio playback library like `ffplay` or `simpleaudio`, and for audio processing it requires `ffmpeg`. If you don't have `ffmpeg` installed, you may need to install it for full functionality, especially on systems where it's not pre-installed. You can download it from the [official ffmpeg website](https://ffmpeg.org/download.html).

## How to Run the Application

Once the setup is complete, you can run the Flask application with a single command:

```bash
python main.py
```

You should see output indicating that the Flask development server is running, typically on `http://127.0.0.1:5000/`.

```
 * Serving Flask app 'main'
 * Debug mode: on
 * Running on http://127.0.0.1:5000
Press CTRL+C to quit
```

## How to Use the Tool

1.  **Open your web browser** and navigate to the address provided by Flask (e.g., `http://127.0.0.1:5000/`).

2.  You will see a web page with several sections. First, **upload your track** using the "Your Track" file input.

3.  (Optional) **Upload a reference track**. If you have a commercial song whose loudness and general sound you want to emulate, upload it using the "Reference Track" file input. If you use this, the tool will automatically use the reference track's loudness as the target for your track. If you leave it blank, it will default to -14 LUFS.

4.  **Adjust the EQ settings** using the sliders for Lows, Mids, and Highs.
5.  **Adjust the Compressor settings** for the full-band compressor.
6.  **Adjust the Multi-band Compressor settings**, including the crossover frequencies and the individual settings for the Low, Mid, and High bands.

7.  Once you have selected a file and set your desired parameters, **click the "Upload and Process"** button.

8.  The application will process the audio through a chain of effects.

9.  After a moment, you will be taken to a results page. This page will show you the original loudness of your file and all the settings you applied.

10. Click the **"Download Processed File"** link to save the final audio file to your computer.

11. You can then click "Process Another File" to return to the main page.

### Producer Signature Presets

To get started quickly, you can select a Producer Signature Preset from the dropdown menu. This will automatically adjust all the EQ and compression settings to a starting point inspired by the sound of a famous producer. You can then fine-tune the settings manually.

- **Dr. Dre Bass Emphasis**: Aims for a powerful, clean low-end and a crisp high-end, typical of modern hip-hop. Expect heavy bass compression and a "scooped" mid-range EQ.
- **Rick Rubin Minimal Punch**: Focuses on a very aggressive, punchy single-band compressor to maximize impact, with minimal EQ or multi-band processing. Designed for a raw, in-your-face sound.
- **George Martin Warmth**: Uses gentle, "glue" style compression and a warm EQ curve to bring a sense of classic, analog warmth and cohesion to the track.

### Note on Processing Order

The processing chain is as follows:
1.  **Loudness Normalization**: The uploaded audio is first normalized to -14 LUFS.
2.  **3-Band EQ**: The EQ is applied.
3.  **EQ Normalization**: The audio is normalized to a peak of 0 dBFS to prevent clipping from EQ boosts.
4.  **Single-Band Compression**: A full-band dynamic range compressor is applied.
5.  **Multi-band Compression**: The audio is split into three bands, each is compressed individually, and then they are recombined.
6.  **Final Normalization**: The final output is normalized to a peak of 0 dBFS to prevent any clipping from the multi-band compression stage.

The final loudness (LUFS) of the downloaded file will vary depending on the EQ and compression settings you choose.

## Analysis Report

After processing, a detailed analysis report is displayed on the results page. If you uploaded a reference track, the report will show a side-by-side comparison of your original track, the reference track, and your final processed track. This allows you to see how your track's characteristics measure up to a commercial release and how your processing has affected the sound.

### Visual Plots
- **Waveform**: A visual representation of the audio's amplitude over time. The "before" and "after" plots help you see changes in the overall signal level and dynamics.
- **Frequency Spectrum**: Shows which frequencies are present in the audio. This plot helps you visualize the tonal balance and see the effect of the EQ settings. It is plotted on a logarithmic scale to better represent human hearing.

### Numeric Metrics
- **Crest Factor**: The ratio of the peak amplitude to the RMS (average) level. It's another way to measure dynamic range. A lower crest factor often indicates a more compressed, "denser" sound.
- **Stereo Correlation**: A value from -1.0 to 1.0 that indicates the similarity between the left and right channels.
    - **1.0**: The channels are identical (mono).
    - **0.0**: The channels are completely different (very wide stereo).
    - **-1.0**: The channels are perfectly out of phase (which can cause problems on mono playback systems).

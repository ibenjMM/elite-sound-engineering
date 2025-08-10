import numpy as np
import soundfile as sf
import matplotlib.pyplot as plt
from scipy.fft import rfft, rfftfreq
import pyloudnorm as pyln
from pydub import AudioSegment

# Configure matplotlib for non-interactive backend
plt.switch_backend('Agg')

def plot_waveform(audio_path, output_path):
    """
    Generates and saves a waveform plot of an audio file.
    """
    try:
        data, rate = sf.read(audio_path)

        # If stereo, take the mean of the channels for plotting
        if data.ndim > 1:
            data = data.mean(axis=1)

        time = np.linspace(0., len(data) / rate, len(data))

        fig, ax = plt.subplots(figsize=(10, 3))
        ax.plot(time, data, lw=0.5)
        ax.set_title("Waveform")
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Amplitude")
        ax.grid(True, linestyle='--', alpha=0.6)
        plt.tight_layout()
        plt.savefig(output_path)
        plt.close(fig)
        return True
    except Exception as e:
        print(f"Error plotting waveform: {e}")
        return False

def plot_spectrum(audio_path, output_path):
    """
    Generates and saves a frequency spectrum plot of an audio file.
    """
    try:
        data, rate = sf.read(audio_path)

        if data.ndim > 1:
            data = data.mean(axis=1)

        N = len(data)
        yf = rfft(data)
        xf = rfftfreq(N, 1 / rate)

        fig, ax = plt.subplots(figsize=(10, 3))
        ax.plot(xf, np.abs(yf))
        ax.set_title("Frequency Spectrum")
        ax.set_xlabel("Frequency (Hz)")
        ax.set_ylabel("Magnitude")
        ax.set_xscale('log')
        ax.grid(True, linestyle='--', alpha=0.6)
        plt.tight_layout()
        plt.savefig(output_path)
        plt.close(fig)
        return True
    except Exception as e:
        print(f"Error plotting spectrum: {e}")
        return False

def calculate_dynamics(audio_path):
    """
    Calculates dynamic range metrics for an audio file.
    Returns a dictionary with LRA and Crest Factor.
    """
    try:
        # Crest Factor with pydub
        sound = AudioSegment.from_file(audio_path)
        if sound.rms == 0:
            crest_factor = 0
        else:
            peak_amplitude = sound.max / sound.max_possible_amplitude
            rms_amplitude = sound.rms / sound.max_possible_amplitude
            crest_factor = peak_amplitude / rms_amplitude if rms_amplitude > 0 else 0

        return {
            "crest_factor": round(crest_factor, 2)
        }
    except Exception as e:
        print(f"Error calculating dynamics: {e}")
        return {"crest_factor": "N/A"}

def calculate_stereo_correlation(audio_path):
    """
    Calculates the stereo correlation of an audio file.
    Returns a value between -1.0 and 1.0.
    Returns 1.0 for mono files.
    """
    try:
        data, rate = sf.read(audio_path)

        if data.ndim < 2:
            return 1.0 # Mono

        left_channel = data[:, 0]
        right_channel = data[:, 1]

        correlation_matrix = np.corrcoef(left_channel, right_channel)
        correlation = correlation_matrix[0, 1]

        return round(correlation, 2)
    except Exception as e:
        print(f"Error calculating stereo correlation: {e}")
        return "N/A"

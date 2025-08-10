import os
import uuid
from flask import Flask, request, render_template, send_from_directory, flash, redirect, url_for
from werkzeug.utils import secure_filename
import numpy as np
import analysis
import soundfile as sf
import pyloudnorm as pyln
from pydub import AudioSegment
from pydub.effects import compress_dynamic_range

# Define the upload folder and allowed extensions
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'wav'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SECRET_KEY'] = 'supersecretkey' # Needed for flashing messages

# Function to check for allowed file extensions
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def apply_3_band_eq(sound, low_gain, mid_gain, high_gain):
    """
    Applies a basic 3-band EQ to an AudioSegment.
    Note: This is a simplified EQ and not a professional-grade filter.
    """
    if low_gain == 0 and mid_gain == 0 and high_gain == 0:
        return sound

    # Crossover frequencies
    low_crossover = 400  # Hz
    high_crossover = 3000 # Hz

    # Filter the audio into three bands
    low_band = sound.low_pass_filter(low_crossover)
    mid_band = sound.high_pass_filter(low_crossover).low_pass_filter(high_crossover)
    high_band = sound.high_pass_filter(high_crossover)

    # Apply gain to each band
    if low_gain != 0:
        low_band += low_gain
    if mid_gain != 0:
        mid_band += mid_gain
    if high_gain != 0:
        high_band += high_gain

    # Recombine the bands by overlaying them.
    # This is a simple approach and may not be perfectly transparent when gains are zero.
    # Start with a silent audio segment and overlay each band.
    # This prevents doubling up the audio.
    output = AudioSegment.silent(duration=len(sound))
    output = output.overlay(low_band)
    output = output.overlay(mid_band)
    output = output.overlay(high_band)

    # Normalizing the output to prevent clipping after EQ boosts.
    # This means the final LUFS value may not be exactly -14 if significant EQ is applied.
    return output.normalize()


def apply_multiband_compression(sound, params):
    """
    Applies multi-band compression to an AudioSegment.
    """
    # Check if the compressor is set to default/off values
    is_default = (
        params['low_band_threshold'] == 0 and params['low_band_ratio'] == 1 and
        params['mid_band_threshold'] == 0 and params['mid_band_ratio'] == 1 and
        params['high_band_threshold'] == 0 and params['high_band_ratio'] == 1
    )
    if is_default:
        return sound

    lxo = params['lxo']
    hxo = params['hxo']

    # Split into three bands
    low_band = sound.low_pass_filter(lxo)
    mid_band = sound.high_pass_filter(lxo).low_pass_filter(hxo)
    high_band = sound.high_pass_filter(hxo)

    # Compress each band
    low_band_compressed = compress_dynamic_range(low_band,
                                                 threshold=params['low_band_threshold'],
                                                 ratio=params['low_band_ratio'],
                                                 attack=params['low_band_attack'],
                                                 release=params['low_band_release'])

    mid_band_compressed = compress_dynamic_range(mid_band,
                                                 threshold=params['mid_band_threshold'],
                                                 ratio=params['mid_band_ratio'],
                                                 attack=params['mid_band_attack'],
                                                 release=params['mid_band_release'])

    high_band_compressed = compress_dynamic_range(high_band,
                                                  threshold=params['high_band_threshold'],
                                                  ratio=params['high_band_ratio'],
                                                  attack=params['high_band_attack'],
                                                  release=params['high_band_release'])

    # Recombine the bands
    output = AudioSegment.silent(duration=len(sound))
    output = output.overlay(low_band_compressed)
    output = output.overlay(mid_band_compressed)
    output = output.overlay(high_band_compressed)

    return output.normalize()


@app.route('/', methods=['GET'])
def index():
    """Render the main page with the file upload form."""
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process_audio():
    """Handle file upload and audio processing."""
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)

    file = request.files['file']

    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(upload_path)

        try:
            # --- Reference Track Handling ---
            target_lufs = -14.0  # Default target
            analysis_results = {'reference': None}
            job_id = str(uuid.uuid4())

            if 'reference_file' in request.files:
                reference_file = request.files['reference_file']
                if reference_file.filename != '':
                    ref_filename = secure_filename(reference_file.filename)
                    ref_path = os.path.join(app.config['UPLOAD_FOLDER'], ref_filename)
                    reference_file.save(ref_path)

                    # Analyze reference track
                    ref_analysis = {}
                    ref_data, ref_rate = sf.read(ref_path)
                    ref_meter = pyln.Meter(ref_rate)
                    target_lufs = ref_meter.integrated_loudness(ref_data) # Set target LUFS from reference

                    ref_analysis['dynamics'] = analysis.calculate_dynamics(ref_path)
                    ref_analysis['correlation'] = analysis.calculate_stereo_correlation(ref_path)

                    ref_waveform_rel_path = f"plots/{job_id}_ref_waveform.png"
                    analysis.plot_waveform(ref_path, f"static/{ref_waveform_rel_path}")
                    ref_analysis['waveform_url'] = ref_waveform_rel_path

                    ref_spectrum_rel_path = f"plots/{job_id}_ref_spectrum.png"
                    analysis.plot_spectrum(ref_path, f"static/{ref_spectrum_rel_path}")
                    ref_analysis['spectrum_url'] = ref_spectrum_rel_path

                    analysis_results['reference'] = ref_analysis

            # 1. Load audio data and rate using soundfile
            data, rate = sf.read(upload_path)

            # 2. Measure loudness using pyloudnorm
            meter = pyln.Meter(rate) # create BS.1770 meter
            loudness = meter.integrated_loudness(data) # measure loudness

            # 3. Normalize loudness to target

            # Use pydub for reliable gain application
            sound = AudioSegment.from_file(upload_path, "wav")

            # 3a. Normalize the audio data to the target loudness
            # This is more accurate than simple dB gain
            normalized_data = pyln.normalize.loudness(data, loudness, target_lufs)

            # 3b. Convert the normalized numpy array back to a pydub AudioSegment
            # We need to ensure the data is in the correct format (16-bit integer for WAV)
            normalized_sound = AudioSegment(
                np.int16(normalized_data * 32767).tobytes(),
                frame_rate=rate,
                sample_width=sound.sample_width,
                channels=sound.channels
            )

            # Get EQ settings from the form
            low_gain = float(request.form.get('low_gain', 0))
            mid_gain = float(request.form.get('mid_gain', 0))
            high_gain = float(request.form.get('high_gain', 0))

            # Apply 3-band EQ to the normalized sound
            eq_sound = apply_3_band_eq(normalized_sound, low_gain, mid_gain, high_gain)

            # Get Compressor settings from the form
            threshold = float(request.form.get('threshold', -20.0))
            ratio = float(request.form.get('ratio', 4.0))
            attack = float(request.form.get('attack', 5.0))
            release = float(request.form.get('release', 50.0))

            # Apply compression
            compressed_sound = compress_dynamic_range(eq_sound,
                                                      threshold=threshold,
                                                      ratio=ratio,
                                                      attack=attack,
                                                      release=release)

            # Get Multi-band Compressor settings
            mb_params = {
                'lxo': float(request.form.get('lxo', 250.0)),
                'hxo': float(request.form.get('hxo', 4000.0)),
                'low_band_threshold': float(request.form.get('low_band_threshold', -20.0)),
                'low_band_ratio': float(request.form.get('low_band_ratio', 4.0)),
                'low_band_attack': float(request.form.get('low_band_attack', 5.0)),
                'low_band_release': float(request.form.get('low_band_release', 50.0)),
                'mid_band_threshold': float(request.form.get('mid_band_threshold', -20.0)),
                'mid_band_ratio': float(request.form.get('mid_band_ratio', 4.0)),
                'mid_band_attack': float(request.form.get('mid_band_attack', 5.0)),
                'mid_band_release': float(request.form.get('mid_band_release', 50.0)),
                'high_band_threshold': float(request.form.get('high_band_threshold', -20.0)),
                'high_band_ratio': float(request.form.get('high_band_ratio', 4.0)),
                'high_band_attack': float(request.form.get('high_band_attack', 5.0)),
                'high_band_release': float(request.form.get('high_band_release', 50.0)),
            }

            # Apply multi-band compression
            final_sound = apply_multiband_compression(compressed_sound, mb_params)

            # --- Analysis ---
            # 1. Analyze Original File
            original_analysis = {}
            original_analysis['dynamics'] = analysis.calculate_dynamics(upload_path)
            original_analysis['correlation'] = analysis.calculate_stereo_correlation(upload_path)

            orig_waveform_rel_path = f"plots/{job_id}_orig_waveform.png"
            analysis.plot_waveform(upload_path, f"static/{orig_waveform_rel_path}")
            original_analysis['waveform_url'] = orig_waveform_rel_path

            orig_spectrum_rel_path = f"plots/{job_id}_orig_spectrum.png"
            analysis.plot_spectrum(upload_path, f"static/{orig_spectrum_rel_path}")
            original_analysis['spectrum_url'] = orig_spectrum_rel_path
            analysis_results['original'] = original_analysis

            # Define processed filename and path
            processed_filename = f"processed_{filename}"
            processed_path = os.path.join(app.config['UPLOAD_FOLDER'], processed_filename)

            # Export the final processed file
            final_sound.export(processed_path, format="wav")

            # 2. Analyze Processed File
            processed_analysis = {}
            processed_analysis['dynamics'] = analysis.calculate_dynamics(processed_path)
            processed_analysis['correlation'] = analysis.calculate_stereo_correlation(processed_path)

            proc_waveform_rel_path = f"plots/{job_id}_proc_waveform.png"
            analysis.plot_waveform(processed_path, f"static/{proc_waveform_rel_path}")
            processed_analysis['waveform_url'] = proc_waveform_rel_path

            proc_spectrum_rel_path = f"plots/{job_id}_proc_spectrum.png"
            analysis.plot_spectrum(processed_path, f"static/{proc_spectrum_rel_path}")
            processed_analysis['spectrum_url'] = proc_spectrum_rel_path
            analysis_results['processed'] = processed_analysis

            # 5. Return a link to the processed file
            return render_template('result.html',
                                   original_file=filename,
                                   processed_file=processed_filename,
                                   original_loudness=round(loudness, 2),
                                   target_loudness=target_lufs,
                                   low_gain=low_gain,
                                   mid_gain=mid_gain,
                                   high_gain=high_gain,
                                   threshold=threshold,
                                   ratio=ratio,
                                   attack=attack,
                                   release=release,
                                   analysis=analysis_results,
                                   **mb_params)

        except Exception as e:
            flash(f'Error processing file: {e}')
            return redirect(url_for('index'))
    else:
        flash('Invalid file type. Please upload a WAV file.')
        return redirect(request.url)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Serve uploaded files."""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


if __name__ == '__main__':
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    if not os.path.exists('static/plots'):
        os.makedirs('static/plots')
    app.run(debug=True)

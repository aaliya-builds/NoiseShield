# NoiseShield

A Windows desktop application designed to reduce background noise from your microphone in real time and route clear audio to communication apps.

**Version:** 0.1.0 Development Build

## Features

- Real-time noise suppression
- Noise suppression ON/OFF control
- Adjustable noise reduction level
- Microphone and output device selection
- Live Activity monitoring
- Activity logs and event counters
- Dark, Light, and System appearance modes
- Remember Preferences option
- Graceful application shutdown

## Technologies Used

- Python
- CustomTkinter
- NumPy
- SoundDevice
- DeepFilterNet
- pywebrtc_audio
- VB-Audio Virtual Cable

## Requirements

- Windows (developed and tested on Windows 11)
- Python 3.12
- VB-Audio Virtual Cable

## Installation

1. Clone or download this repository.
2. Create a virtual environment:

   ```bash
   python -m venv deepfilter-venv
   ```

3. Activate the environment:

   ```powershell
   .\deepfilter-venv\Scripts\Activate.ps1
   ```

4. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

5. Install VB-Audio Virtual Cable separately.

## Run the Application

```bash
python main_clean.py
```

## Audio Routing

1. Select your physical microphone as the NoiseShield input.
2. Select CABLE Input as the NoiseShield output.
3. Select CABLE Output as the microphone in your meeting application.
4. Start Noise Protection.

## Project Status

NoiseShield is currently under development.

More improvements and testing are planned.

## License

License not yet selected.
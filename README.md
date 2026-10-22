# ZeroMQ-Walkie-Talkie 🎙️📻

A real-time, bidirectional audio intercom and Walkie-Talkie system built with **ZeroMQ (ØMQ)**, **SoundDevice/PyAudio**, **Flask**, and **Python**. This repository demonstrates how to combine **ZeroMQ PAIR** for full-duplex low-latency audio streaming with **ZeroMQ REQ/REP** for runtime control (mute/unmute, volume adjustments) via a web dashboard.

---

## 🏗️ Architecture Overview

```
                      +-----------------------------+
                      |     Web Dashboard (Flask)   |
                      |   http://localhost:5000     |
                      +--------------+--------------+
                                     |
                                     | ZeroMQ REQ/REP (Control - Port 5559)
                                     v
                      +-----------------------------+
                      |      Walkie-Talkie Engine   |
                      |    (walkie_talkie_node.py)  |
                      +--------------+--------------+
                                     |
                                     | ZeroMQ PAIR (Audio Stream - Port 5555)
                                     v
                      +-----------------------------+
                      |        Peer Node 2          |
                      |  (walkie_talkie_node.py)    |
                      +-----------------------------+
```

1. **Audio Streaming Channel (`ZeroMQ PAIR`):**
   * Establishes a full-duplex 1-to-1 connection between two audio nodes.
   * Transmits raw PCM audio packets captured from the microphone in real time.
   * Applies local volume scaling and mute rules before playback.

2. **Control Channel (`ZeroMQ REQ/REP`):**
   * Runs a local control server inside the audio engine.
   * Handles asynchronous commands such as toggling Mute state (`SET_MUTE:true`) or adjusting master volume (`SET_VOLUME:75`).

3. **Web Control Interface (`web_app.py`):**
   * Provides an intuitive web dashboard built with Flask.
   * Allows users to trigger Mute controls and adjust volume via sliders in real time.

---

## ⚙️ Installation & Prerequisites

```bash
pip install pyzmq sounddevice numpy flask
```

On Linux systems:
```bash
sudo apt-get update
sudo apt-get install libportaudio2 libzmq3-dev
```

---

## 🚀 How to Run

### Single Machine Test (Use headphones to avoid feedback!)

1. **Start Node 1 (Host/Server mode):**
   ```bash
   python walkie_talkie_node.py --mode bind --audio-port 5555 --control-port 5559
   ```

2. **Start Node 2 (Client mode):**
   ```bash
   python walkie_talkie_node.py --mode connect --target-ip localhost --audio-port 5555 --control-port 5560
   ```

3. **Start the Web Dashboard for Node 1:**
   ```bash
   python web_app.py --control-port 5559 --web-port 5000
   ```
   Open `http://localhost:5000` in your web browser.

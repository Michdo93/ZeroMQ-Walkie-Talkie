import argparse
from flask import Flask, render_template_string, jsonify, request
import zmq

app = Flask(__name__)
CONTROL_PORT = 5559

def send_control_command(cmd_str):
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.setsockopt(zmq.RCVTIMEO, 1000)
    socket.connect(f"tcp://localhost:{CONTROL_PORT}")

    try:
        socket.send_string(cmd_str)
        response = socket.recv_string()
        return response
    except zmq.Again:
        return "ERROR: Timeout - Node not responding"
    finally:
        socket.close()
        context.term()

HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ZeroMQ Walkie-Talkie Dashboard</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #121212;
            color: #ffffff;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
        }
        .card {
            background: #1e1e1e;
            border-radius: 16px;
            padding: 32px;
            width: 360px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.5);
            text-align: center;
        }
        h1 { margin-bottom: 8px; font-size: 1.6rem; color: #00e676; }
        p.subtitle { color: #888; font-size: 0.9rem; margin-bottom: 24px; }
        .btn {
            background: #2979ff;
            color: white;
            border: none;
            padding: 16px 32px;
            font-size: 1.1rem;
            font-weight: bold;
            border-radius: 30px;
            cursor: pointer;
            width: 100%;
            transition: all 0.2s ease;
            margin-bottom: 20px;
        }
        .btn.muted { background: #ff1744; }
        .btn:hover { opacity: 0.9; transform: scale(1.02); }
        .slider-container { margin-top: 20px; text-align: left; }
        label { display: block; font-size: 0.9rem; color: #aaa; margin-bottom: 8px; }
        input[type=range] { width: 100%; accent-color: #00e676; }
        .status { margin-top: 24px; font-size: 0.85rem; color: #777; background: #2a2a2a; padding: 10px; border-radius: 8px; }
    </style>
</head>
<body>
    <div class="card">
        <h1>🎙️ Walkie-Talkie</h1>
        <p class="subtitle">ZeroMQ Full-Duplex Intercom</p>

        <button id="muteBtn" class="btn" onclick="toggleMute()">Microphone: ON</button>

        <div class="slider-container">
            <label for="volRange">Master Volume: <span id="volVal">100%</span></label>
            <input type="range" id="volRange" min="0" max="150" value="100" onchange="updateVolume(this.value)">
        </div>

        <div class="status" id="statusBox">Connecting to Node...</div>
    </div>

    <script>
        let isMuted = false;

        function fetchStatus() {
            fetch('/api/status')
                .then(r => r.json())
                .then(data => {
                    document.getElementById('statusBox').innerText = data.response;
                    if (data.response.includes('muted=True')) {
                        isMuted = true;
                        updateMuteUI();
                    } else if (data.response.includes('muted=False')) {
                        isMuted = false;
                        updateMuteUI();
                    }
                });
        }

        function updateMuteUI() {
            const btn = document.getElementById('muteBtn');
            if (isMuted) {
                btn.innerText = "Microphone: MUTED 🔇";
                btn.classList.add('muted');
            } else {
                btn.innerText = "Microphone: ON 🎙️";
                btn.classList.remove('muted');
            }
        }

        function toggleMute() {
            isMuted = !isMuted;
            fetch('/api/mute?state=' + isMuted)
                .then(r => r.json())
                .then(data => {
                    updateMuteUI();
                    document.getElementById('statusBox').innerText = data.response;
                });
        }

        function updateVolume(val) {
            document.getElementById('volVal').innerText = val + '%';
            fetch('/api/volume?val=' + val)
                .then(r => r.json())
                .then(data => {
                    document.getElementById('statusBox').innerText = data.response;
                });
        }

        setInterval(fetchStatus, 3000);
        fetchStatus();
    </script>
</body>
</html>'''

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route("/api/status")
def api_status():
    resp = send_control_command("GET_STATUS")
    return jsonify({"response": resp})

@app.route("/api/mute")
def api_mute():
    state = request.args.get("state", "false")
    resp = send_control_command(f"SET_MUTE:{state}")
    return jsonify({"response": resp})

@app.route("/api/volume")
def api_volume():
    val = request.args.get("val", "100")
    resp = send_control_command(f"SET_VOLUME:{val}")
    return jsonify({"response": resp})

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Walkie-Talkie Web Control Dashboard")
    parser.add_argument("--control-port", type=int, default=5559, help="ZeroMQ REP control port of node")
    parser.add_argument("--web-port", type=int, default=5000, help="Web Dashboard HTTP Port")

    args = parser.parse_args()
    CONTROL_PORT = args.control_port
    print(f"Starting Web Control Dashboard on http://localhost:{args.web_port} (Connecting to node control port {CONTROL_PORT})...")
    app.run(host="0.0.0.0", port=args.web_port, debug=False)

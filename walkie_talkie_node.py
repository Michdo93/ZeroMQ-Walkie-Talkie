import argparse
import time
import threading
import numpy as np
import sounddevice as sd
import zmq

SAMPLERATE = 16000
CHANNELS = 1
BLOCKSIZE = 1024

class WalkieTalkieNode:
    def __init__(self, mode, target_ip, audio_port, control_port):
        self.mode = mode
        self.target_ip = target_ip
        self.audio_port = audio_port
        self.control_port = control_port

        self.muted = False
        self.volume = 1.0  # 0.0 to 2.0
        self.running = True

        self.context = zmq.Context()

        # Audio Stream Socket (PAIR)
        self.audio_socket = self.context.socket(zmq.PAIR)
        if self.mode == "bind":
            self.audio_socket.bind(f"tcp://*:{self.audio_port}")
            print(f"[Audio] Bound PAIR socket to tcp://*:{self.audio_port}")
        else:
            self.audio_socket.connect(f"tcp://{self.target_ip}:{self.audio_port}")
            print(f"[Audio] Connected PAIR socket to tcp://{self.target_ip}:{self.audio_port}")

        # Control Server Socket (REP)
        self.rep_socket = self.context.socket(zmq.REP)
        self.rep_socket.bind(f"tcp://*:{self.control_port}")
        print(f"[Control] Bound REP socket to tcp://*:{self.control_port}")

    def audio_callback(self, indata, frames, time_info, status):
        if status:
            print(f"[Audio Status Warning] {status}")

        if not self.muted:
            scaled_data = (indata * self.volume).astype(np.float32)
            try:
                self.audio_socket.send(scaled_data.tobytes(), flags=zmq.NOBLOCK)
            except zmq.Again:
                pass
        else:
            silent = np.zeros_like(indata, dtype=np.float32)
            try:
                self.audio_socket.send(silent.tobytes(), flags=zmq.NOBLOCK)
            except zmq.Again:
                pass

    def receive_audio_loop(self):
        with sd.OutputStream(samplerate=SAMPLERATE, channels=CHANNELS, dtype='float32') as out_stream:
            while self.running:
                try:
                    raw_bytes = self.audio_socket.recv(flags=zmq.NOBLOCK)
                    audio_data = np.frombuffer(raw_bytes, dtype=np.float32).reshape(-1, CHANNELS)
                    out_stream.write(audio_data)
                except zmq.Again:
                    time.sleep(0.005)
                except Exception as e:
                    if self.running:
                        print(f"[Receive Error] {e}")

    def control_loop(self):
        while self.running:
            try:
                msg = self.rep_socket.recv_string(flags=zmq.NOBLOCK)
                print(f"[Control REQ] {msg}")

                if msg == "GET_STATUS":
                    resp = f"STATUS: muted={self.muted}, volume={int(self.volume * 100)}"
                elif msg.startswith("SET_MUTE:"):
                    state = msg.split(":", 1)[1].strip().lower()
                    self.muted = (state == "true")
                    resp = f"OK: muted={self.muted}"
                elif msg.startswith("SET_VOLUME:"):
                    try:
                        vol = int(msg.split(":", 1)[1])
                        self.volume = max(0.0, min(2.0, vol / 100.0))
                        resp = f"OK: volume={int(self.volume * 100)}"
                    except ValueError:
                        resp = "ERROR: Invalid volume"
                else:
                    resp = f"ERROR: Unknown command '{msg}'"

                self.rep_socket.send_string(resp)
            except zmq.Again:
                time.sleep(0.05)

    def start(self):
        rx_thread = threading.Thread(target=self.receive_audio_loop, daemon=True)
        ctrl_thread = threading.Thread(target=self.control_loop, daemon=True)

        rx_thread.start()
        ctrl_thread.start()

        print("Walkie-Talkie Node active. Press Ctrl+C to stop.")

        try:
            with sd.InputStream(samplerate=SAMPLERATE, channels=CHANNELS, blocksize=BLOCKSIZE, callback=self.audio_callback):
                while self.running:
                    time.sleep(0.5)
        except KeyboardInterrupt:
            print("
Shutting down Walkie-Talkie Node...")
        finally:
            self.running = False
            self.audio_socket.close()
            self.rep_socket.close()
            self.context.term()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ZeroMQ Walkie-Talkie Node")
    parser.add_argument("--mode", choices=["bind", "connect"], default="bind", help="PAIR socket mode")
    parser.add_argument("--target-ip", default="localhost", help="IP address when mode=connect")
    parser.add_argument("--audio-port", type=int, default=5555, help="Port for PAIR audio socket")
    parser.add_argument("--control-port", type=int, default=5559, help="Port for REP control socket")

    args = parser.parse_args()
    node = WalkieTalkieNode(args.mode, args.target_ip, args.audio_port, args.control_port)
    node.start()

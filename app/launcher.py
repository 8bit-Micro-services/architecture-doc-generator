"""Start the local workboard and open it in the default browser."""
from __future__ import annotations

import argparse
import socket
import threading
import time
import webbrowser

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local SDLC Workboard")
    parser.add_argument("--port", type=int, default=0, help="Local port (default: choose an available port)")
    args = parser.parse_args()
    if args.port < 0 or args.port > 65535:
        parser.error("port must be between 0 and 65535")

    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(("127.0.0.1", args.port))
    listener.listen(128)
    port = listener.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config("app.main:app", host="127.0.0.1", port=port))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
    url = f"http://127.0.0.1:{port}"
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started and thread.is_alive() and time.monotonic() < deadline:
            time.sleep(0.05)
        if not server.started:
            raise RuntimeError("Workboard server did not start")
        print(f"SDLC Workboard running at {url} (press Ctrl+C to stop)")
        webbrowser.open(url)
        thread.join()
    except KeyboardInterrupt:
        server.should_exit = True
        thread.join(timeout=5)
    finally:
        listener.close()


if __name__ == "__main__":
    main()

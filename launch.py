"""Local desktop launcher; opens the browser only after the app is responding."""

import threading
import time
import urllib.request
import webbrowser

import uvicorn


def open_when_ready():
    for _ in range(40):
        try:
            with urllib.request.urlopen("http://127.0.0.1:8000/api/status", timeout=1) as response:
                if response.status == 200:
                    webbrowser.open("http://127.0.0.1:8000")
                    return
        except OSError:
            time.sleep(0.5)


if __name__ == "__main__":
    threading.Thread(target=open_when_ready, daemon=True).start()
    uvicorn.run("assistant_app.main:app", host="127.0.0.1", port=8000)

from mitmproxy import http
from google.cloud import vision
import os

def response(flow: http.HTTPFlow) -> None:
    # Prüfen, ob es sich um ein Bild handelt
    content_type = flow.response.headers.get("Content-Type", "")
    if content_type.startswith("image/"):
        content_size = len(flow.response.content)
        if content_size > 200:
            check_image(flow)


def check_image(flow):
    url = flow.request.pretty_url

    analyze_image(flow.response.content)
    if 0:
        print(f"[BLOCKIERT] Bild auf {url}")

        # Hier ersetzen wir das Bild durch ein leeres 1x1 PNG
        BLANK_PNG = (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
            b'\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89'
            b'\x00\x00\x00\nIDATx\xdac\xf8\x0f\x00\x01\x01\x01\x00'
            b'\x18\xdd\xdc\xea\x00\x00\x00\x00IEND\xaeB`\x82'
        )
        flow.response.content = BLANK_PNG
        flow.response.headers["Content-Length"] = str(len(BLANK_PNG))
        flow.response.headers["Content-Type"] = "image/png"

    else:
        print(f"[ERLAUBT] -> Bild")


# Pfad zur JSON-Datei mit deinem Google-Service-Account
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "vision_key.json"

# Vision Client einmal erstellen (global)
client = vision.ImageAnnotatorClient()

def analyze_image(image_bytes: bytes):
    image = vision.Image(content=image_bytes)

    # Beispiel: Labels erkennen lassen
    response = client.label_detection(image=image)
    labels = response.label_annotations

    print("\n🔍 Google Vision-Erkennung:")
    for label in labels:
        print(f"- {label.description} (score: {label.score:.2f})")

    if response.error.message:
        print(f"❌ Fehler von der Vision API: {response.error.message}")
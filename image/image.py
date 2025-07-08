from mitmproxy import http
import os
import requests
import json
import ast
from mitmproxy import http
import re
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

token = "qr8psfemsn68qud85sb7dj4ufg"
model = "NSFW-classification"  # "General-classification", "Places-classification", "NSFW-classification" or "Object-detection"
headers = {"X-Auth-token": token, "Content-Type": "application/json"}

def response(flow: http.HTTPFlow) -> None:
    # Prüfen, ob es sich um ein Bild handelt
    content_type = flow.response.headers.get("Content-Type", "")
    
	# Überprüfen, ob der Inhalt IMAGEs enthält
    if content_type.startswith("image/"):
        content_size = len(flow.response.content)
        if content_size > 200:
            check_image(flow)


def check_image(flow):
    url = flow.request.pretty_url

    if detect_nsfw_uri(url, 70):
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


def detect_nsfw_uri(image_uri, thres):
	"""Detects unsafe imagees on the Web."""

	# image_url = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcS6BjYozZloyQtA6_M_Qxs7KhyV2caxRdCYug&s"

	payload = json.dumps({
		"url": image_uri
	})

	r = requests.post('https://platform.sentisight.ai/api/pm-predict/{}/'.format(model), headers=headers, data=payload)

	if r.status_code == 200:
		return (1 if ast.literal_eval(r.text)[0]['score'] > thres else 0)
	else:
		print('Error occured with REST API.')
		print('Status code: {}'.format(r.status_code))
		print('Error message: ' + r.text)
		return (1)
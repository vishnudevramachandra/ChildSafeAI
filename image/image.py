from mitmproxy import http

def response(flow: http.HTTPFlow) -> None:
    # Prüfen, ob es sich um ein Bild handelt
    content_type = flow.response.headers.get("Content-Type", "")
    if content_type.startswith("image/"):
        url = flow.request.pretty_url
        content_length = len(flow.response.content)
        

        # Beispiel: Nur blockieren, wenn das Bild größer als 50 KB ist
        if content_length > 50 * 1024:
            print(f"[BLOCKIERT] Großes Bild auf {url} ({content_length} Bytes)")

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
            print(f"[ERLAUBT] Bild auf {url} ({content_length} Bytes)")

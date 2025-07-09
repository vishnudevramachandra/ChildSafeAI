from mitmproxy import http
import re
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit
import os

# === Load JS snippet from file ===
BASE_DIR = os.path.dirname(__file__)
with open(os.path.join(BASE_DIR, "blur_script.js"), encoding="utf-8") as f:
    JS_SNIPPET = f"<script>{f.read()}</script>"

INAPPROPRIATE_WORDS = [
    "Mac",
    "iphone",
    "MacBook",
    "Post",
    "Metall",
    "Leaker"
]


def blur_word(word: str) -> str:
    print(f"[mitmproxy] Blurring word: {word}")
    if len(word) <= 1:
        return "*"
    return word[0] + "*" * (len(word) - 1)

def blur_inappropriate(content: str) -> str:
    pattern = re.compile('(' + '|'.join(map(re.escape, INAPPROPRIATE_WORDS)) + ')', re.IGNORECASE)

    def _replacer(match):
        matched = match.group()
        print(f"[mitmproxy] Match found in content: {matched}")
        return blur_word(matched)

    return pattern.sub(_replacer, content)


def request(flow: http.HTTPFlow):
    url_parts = urlsplit(flow.request.url)
    query_params = parse_qs(url_parts.query)
    modified = False

    for key, values in query_params.items():
        new_values = []
        for value in values:
            new_value = blur_inappropriate(value)
            if new_value != value:
                modified = True
            new_values.append(new_value)
        query_params[key] = new_values

    if modified:
        new_query = urlencode(query_params, doseq=True)
        new_url = urlunsplit((url_parts.scheme, url_parts.netloc, url_parts.path, new_query, url_parts.fragment))
        print(f"[mitmproxy] Modified URL: {new_url}")
        flow.request.url = new_url

    if flow.request.method in ["POST", "PUT"] and flow.request.raw_content:
        try:
            content_type = flow.request.headers.get("Content-Type", "")
            if "application/x-www-form-urlencoded" in content_type:
                form_data = parse_qs(flow.request.get_text())
                for key in form_data:
                    form_data[key] = [blur_inappropriate(v) for v in form_data[key]]
                print("[mitmproxy] Modified form data in request body.")
                flow.request.set_text(urlencode(form_data, doseq=True))
            else:
                body_text = flow.request.get_text()
                flow.request.set_text(blur_inappropriate(body_text))
                print("[mitmproxy] Modified raw request body.")
        except Exception as e:
            print(f"[mitmproxy ERROR] Request body processing failed: {e}")
            flow.response = http.Response.make(
                500,
                f"Error processing request body: {str(e)}".encode(),
                {"Content-Type": "text/plain"}
            )


def response(flow: http.HTTPFlow):
    content_type = flow.response.headers.get("Content-Type", "")
    if "text/html" in content_type:
        try:
            html = flow.response.get_text()
            print("[mitmproxy] Original HTML length:", len(html))

            if "</body>" in html:
                html = html.replace("</body>", JS_SNIPPET + "</body>")
            elif "</html>" in html:
                html = html.replace("</html>", JS_SNIPPET + "</html>")
            else:
                html += JS_SNIPPET

            flow.response.set_text(html)
            print("[mitmproxy] Injected JavaScript into HTML response.")
        except Exception as e:
            print(f"[mitmproxy ERROR] Failed to modify response: {e}")

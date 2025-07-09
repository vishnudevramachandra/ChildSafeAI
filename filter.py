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


# Liste von Wörtern, die ersetzt/blurren werden sollen
def load_words_from_file(file_path):
    with open(file_path, 'r') as file:
        words = [line.strip() for line in file.readlines() if line.strip()]  # Strip Leerzeichen und leere Zeilen
    return words

# Lade die Wörter aus der Textdatei
words_to_blur = load_words_from_file('words_to_blur.txt')

# Liste von Wörtern, die ersetzt/blurren werden sollen
#words_to_blur = ["airpods", "metall", "iphone", "Eisen", "ipad", "watch"]

js_words_to_blur = "const inappropriate = [\n"
for word in words_to_blur:
    js_words_to_blur += f'  /\\b{word}\\b/gi,\n'
js_words_to_blur += "];"


def response(flow: http.HTTPFlow) -> None:
    # Prüfen, ob es sich um ein Bild handelt
    content_type = flow.response.headers.get("Content-Type", "")
    
    # Überprüfen den Text
    check_text(flow)

	# Überprüfen, ob der Inhalt IMAGEs enthält
    if content_type.startswith("image/"):
        url = flow.request.pretty_url
        content_size = len(flow.response.content)
        is_logo = any(kw in url for kw in ["logo", "icon", "favicon", "sprite"])
        is_small = content_size < 5 * 1024

        try:
            img = Image.open(BytesIO(flow.response.content))
            width, height = img.size
            is_tiny = max(width, height) < 100
        except Exception:
            width = height = 0
            is_tiny = False
        if is_logo or is_small or is_tiny:
            print(f"[Logo/Icon?] {url} ({width}x{height}, {content_size/1024} KB)")
        else:
            print(f"[Content-Bild] {url} ({width}x{height}, {content_size/1024} KB)")
            check_image(flow)
        # if content_size > 100:
        #   check_image(flow)
            


def check_image(flow):
    url = flow.request.pretty_url

    if detect_nsfw_uri(url, 50):
        print(f"[BLOCKIERT] Image URL: {url}")

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
        print(f"[ALLOW] -> Image")


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



def check_text(flow):
    content_type = flow.response.headers.get("Content-Type", "")

    if "text/html" in content_type:
        try:
            # Antworte Body-Text als String extrahieren
            content = flow.response.get_text()
            # Blurren des Textes
            blurred_content = blur_text(content)
            # Den Body der Antwort mit dem bearbeiteten Text überschreiben
            flow.response.text = blurred_content
            html = flow.response.get_text()
            print("[HTML blur]")

            # Only inject JavaScript – no server-side HTML modification
            if "</body>" in html:
                html = html.replace("</body>", JS_SNIPPET + "</body>")
            elif "</html>" in html:
                html = html.replace("</html>", JS_SNIPPET + "</html>")
            else:
                html += JS_SNIPPET

            flow.response.set_text(html)
            print("[Injected JavaScript]")
        except Exception as e:
            print(f"[mitmproxy ERROR] Failed to modify response: {e}")


# Funktion zum Ersetzen der Wörter
def blur_text(text):
    for word in words_to_blur:
        text = re.sub(rf'\b{re.escape(word)}\b', '*****', text, flags=re.IGNORECASE)
    return text


# JavaScript censorship logic, runs in browser
JS_SNIPPET = """
<script>
document.addEventListener("DOMContentLoaded", function() {
  console.log("[mitmproxy JS] censorship script injected");

  // Show a red banner to confirm injection worked
  const banner = document.createElement("div");
  banner.style = "position:fixed;top:0;left:0;width:100%;background:red;color:white;padding:5px;z-index:99999";
  document.body.appendChild(banner);

  // Define patterns to blur
  const inappropriate = """ + js_words_to_blur + """

function blurText(node) {
  if (node.nodeType === Node.TEXT_NODE) {
    let text = node.nodeValue;
    inappropriate.forEach(pattern => {
      if (pattern.test(text)) {
        text = text.replace(pattern, match =>
          match[0] + "*".repeat(match.length - 1)
        );
      }
    });
    node.nodeValue = text;
  }

  else if (node.nodeType === Node.ELEMENT_NODE) {
    // Blur <a> href attribute
    if (node.tagName === "A" && node.href) {
      inappropriate.forEach(pattern => {
        if (pattern.test(node.href)) {
          console.log("[mitmproxy JS] Blurring match in href:", node.href);
          node.href = node.href.replace(pattern, match =>
            match[0] + "*".repeat(match.length - 1)
          );
        }
      });
    }

    // Blur innerText of <a> (and any element)
    if (node.childNodes.length === 0 && node.innerText) {
      inappropriate.forEach(pattern => {
        if (pattern.test(node.innerText)) {
          node.innerText = node.innerText.replace(pattern, match =>
            match[0] + "*".repeat(match.length - 1)
          );
        }
      });
    }

    // Traverse all children
    node.childNodes.forEach(blurText);
  }
}

  // Initial blur
  blurText(document.body);

  // Replace SVGs with white rectangles
  document.querySelectorAll("span.globalnav-link-text-container svg").forEach(el => {
    const whiteSvg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    whiteSvg.setAttribute("width", el.getAttribute("width") || "30");
    whiteSvg.setAttribute("height", el.getAttribute("height") || "30");
    whiteSvg.innerHTML = '<rect width="100%" height="100%" fill="white" />';
    el.parentNode.replaceChild(whiteSvg, el);
  });

  // Observe future changes
  const observer = new MutationObserver((mutations) => {
    for (const mutation of mutations) {
      mutation.addedNodes.forEach(blurText);
      mutation.addedNodes.forEach(node => {
        if (node.nodeType === 1 && node.querySelectorAll) {
          node.querySelectorAll("span.globalnav-link-text-container svg").forEach(el => {
            const whiteSvg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
            whiteSvg.setAttribute("width", el.getAttribute("width") || "30");
            whiteSvg.setAttribute("height", el.getAttribute("height") || "30");
            whiteSvg.innerHTML = '<rect width="100%" height="100%" fill="white" />';
            el.parentNode.replaceChild(whiteSvg, el);
          });
        }
      });
    }
  });
  observer.observe(document.body, { childList: true, subtree: true });
});
</script>
"""

from mitmproxy import http
import re
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit


# Liste von Wörtern, die ersetzt/blurren werden sollen
words_to_blur = ["example", "metall", "iphone", "Eisen", "ipad", "watch"]

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
  const inappropriate = [
    /\\biPhone\\b/gi,
    /\\bStore\\b/gi,
    /\\biPad\\b/gi,
    /\\bEisen\\b/gi
    /\\bwatch\\b/gi
  ];

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



def response(flow: http.HTTPFlow):
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
            print("[mitmproxy] Original HTML length:", len(html))


            # Only inject JavaScript – no server-side HTML modification
            if "</body>" in html:
                html = html.replace("</body>", JS_SNIPPET + "</body>")
            elif "</html>" in html:
                html = html.replace("</html>", JS_SNIPPET + "</html>")
            else:
                html += JS_SNIPPET

            flow.response.set_text(html)
            print("[mitmproxy] Injected JavaScript only, no HTML blur.")
        except Exception as e:
            print(f"[mitmproxy ERROR] Failed to modify response: {e}")

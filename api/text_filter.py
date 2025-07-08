from mitmproxy import http
import re
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

# Words to censor in plain HTML/text (optional server-side URL/body blur)
INAPPROPRIATE_WORDS = [
    "iPhone",  # This doesn't match real words unless obfuscated
    "Laserangriff"
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
    /\\bMac\\b/gi
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

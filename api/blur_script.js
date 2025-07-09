
document.addEventListener("DOMContentLoaded", function()
{
  const patterns = [
    /\bStore\b/gi,
    /\Iphone\b/gi,
    /\Metall\b/gi
  ];

  function blurText(node)
  {
    if (node.nodeType === Node.TEXT_NODE)
    {
      let text = node.nodeValue;
      patterns.forEach(pattern =>
      {
        text = text.replace(pattern, match => match[0] + "*".repeat(match.length - 1));
      });
      node.nodeValue = text;
    }
    else if (node.nodeType === Node.ELEMENT_NODE)
    {
      node.childNodes.forEach(blurText);
    }
  }

  // Blur current text
  blurText(document.body);

  // Observe future changes
  new MutationObserver(mutations =>
  {
    mutations.forEach(m => m.addedNodes.forEach(blurText));
  }).observe(document.body, { childList: true, subtree: true });
});

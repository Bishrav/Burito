// Build DOM nodes from trusted syntax and untrusted text. Raw HTML and images are text.
function element(tag, text) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  return node;
}

function inline(parent, content) {
  const pattern = /`([^`]+)`|\*\*([^*]+)\*\*|\*([^*]+)\*|\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g;
  let cursor = 0;
  for (const match of content.matchAll(pattern)) {
    parent.append(content.slice(cursor, match.index));
    const [, code, strong, emphasis, label, url] = match;
    if (url) {
      const link = element('a', label);
      link.href = url;
      link.target = '_blank';
      link.rel = 'noreferrer noopener';
      parent.append(link);
    } else {
      parent.append(element(code ? 'code' : strong ? 'strong' : 'em', code || strong || emphasis));
    }
    cursor = match.index + match[0].length;
  }
  parent.append(content.slice(cursor));
}

export function copyButton(label, text) {
  const button = element('button', label);
  button.type = 'button';
  button.className = 'copy-text';
  button.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(text);
      button.textContent = 'Copied';
    } catch {
      button.textContent = 'Copy failed';
    }
  });
  return button;
}

function codeBlock(parent, source) {
  const pre = element('pre');
  const code = element('code');
  const tokens = /("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'|\/\/[^\n]*|#[^\n]*|\b(?:async|await|break|class|const|continue|def|else|export|False|for|from|function|if|import|in|let|None|null|return|SELECT|FROM|WHERE|throw|True|try|var|while|yield)\b)/g;
  let cursor = 0;
  for (const match of source.matchAll(tokens)) {
    code.append(source.slice(cursor, match.index));
    const token = match[0];
    const part = element('span', token);
    const kind = token.startsWith('#') || token.startsWith('//') ? 'comment'
      : token.startsWith('"') || token.startsWith("'") ? 'string' : 'keyword';
    part.className = `token-${kind}`;
    code.append(part);
    cursor = match.index + token.length;
  }
  code.append(source.slice(cursor));
  pre.append(code);
  parent.append(pre, copyButton('Copy code', source));
}

export function renderMarkdown(parent, source) {
  parent.replaceChildren();
  const lines = source.split('\n');
  let paragraph = [];
  let list;
  function flush() {
    if (paragraph.length) {
      const node = element('p');
      inline(node, paragraph.join('\n'));
      parent.append(node);
      paragraph = [];
    }
    list = undefined;
  }
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (/^\s*```/.test(line)) {
      flush();
      const code = [];
      while (++i < lines.length && !/^\s*```/.test(lines[i])) code.push(lines[i]);
      codeBlock(parent, code.join('\n'));
      continue;
    }
    const item = /^\s*([-*]|\d+\.)\s+(.+)$/.exec(line);
    if (item) {
      if (!list) flush();
      const tag = item[1].endsWith('.') ? 'OL' : 'UL';
      if (list?.tagName !== tag) {
        list = element(tag);
        parent.append(list);
      }
      const li = element('li');
      inline(li, item[2]);
      list.append(li);
      continue;
    }
    if (/^#{1,6}\s|^>\s/.test(line)) {
      flush();
      const node = element(line.startsWith('>') ? 'blockquote' : 'h3');
      inline(node, line.replace(/^(?:#{1,6}|>)\s+/, ''));
      parent.append(node);
      continue;
    }
    if (!line.trim()) flush();
    else {
      list = undefined;
      paragraph.push(line);
    }
  }
  flush();
}

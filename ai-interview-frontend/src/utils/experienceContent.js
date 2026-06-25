import { marked } from 'marked'

marked.setOptions({
  breaks: true,
  gfm: true,
})

const ALLOWED_TAGS = new Set([
  'a', 'blockquote', 'br', 'code', 'em', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
  'hr', 'img', 'li', 'ol', 'p', 'pre', 'strong', 'table', 'tbody', 'td',
  'th', 'thead', 'tr', 'ul'
])

const ALLOWED_ATTRS = {
  a: new Set(['href', 'title', 'target', 'rel']),
  img: new Set(['src', 'alt', 'title']),
  td: new Set(['colspan', 'rowspan']),
  th: new Set(['colspan', 'rowspan']),
  code: new Set(['class'])
}

function sanitizeNode(node, documentRef) {
  if (node.nodeType === Node.TEXT_NODE) {
    return documentRef.createTextNode(node.textContent || '')
  }

  if (node.nodeType !== Node.ELEMENT_NODE) {
    return documentRef.createDocumentFragment()
  }

  const tag = node.tagName.toLowerCase()

  if (tag === 'script' || tag === 'style' || tag === 'svg' || tag === 'iframe') {
    return documentRef.createDocumentFragment()
  }

  const fragment = documentRef.createDocumentFragment()

  if (!ALLOWED_TAGS.has(tag)) {
    for (const child of Array.from(node.childNodes)) {
      fragment.appendChild(sanitizeNode(child, documentRef))
    }
    return fragment
  }

  const clean = documentRef.createElement(tag)
  const allowedAttrs = ALLOWED_ATTRS[tag] || new Set()

  for (const attr of Array.from(node.attributes)) {
    const name = attr.name.toLowerCase()
    const value = attr.value || ''

    if (!allowedAttrs.has(name)) continue
    if (name.startsWith('on')) continue
    if ((name === 'href' || name === 'src') && /^\s*javascript:/i.test(value)) continue

    clean.setAttribute(name, value)
  }

  if (tag === 'a') {
    const href = clean.getAttribute('href') || ''
    if (/^https?:\/\//i.test(href)) {
      clean.setAttribute('target', '_blank')
      clean.setAttribute('rel', 'noopener noreferrer nofollow')
    }
  }

  for (const child of Array.from(node.childNodes)) {
    clean.appendChild(sanitizeNode(child, documentRef))
  }

  return clean
}

export function renderExperienceContent(markdown) {
  const rawHtml = marked.parse(markdown || '')

  if (typeof window === 'undefined' || typeof DOMParser === 'undefined') {
    return rawHtml
  }

  const parser = new DOMParser()
  const parsed = parser.parseFromString(rawHtml, 'text/html')
  const container = document.createElement('div')

  for (const child of Array.from(parsed.body.childNodes)) {
    container.appendChild(sanitizeNode(child, document))
  }

  return container.innerHTML
}

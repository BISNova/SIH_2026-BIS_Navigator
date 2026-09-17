/**
 * P1's Gemini-generated answers come back with markdown syntax
 * (**bold**, "- " bullet lists, `code`, [links](url), # headers) - fine
 * for a markdown renderer, but shown raw in a plain chat bubble it just
 * looks like broken text full of asterisks and hashes. This strips
 * markdown syntax down to clean, readable plain text instead of
 * rendering it as rich HTML - simple on purpose: no markdown library,
 * no HTML injection risk, just readable text.
 */

export function markdownToPlainText(text) {
  if (!text) return text;

  let result = text;

  // Links: [label](url) -> "label (url)"
  result = result.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '$1 ($2)');

  // Bold / italic: **text**, __text__, *text*, _text_ -> text
  result = result.replace(/\*\*\*(.+?)\*\*\*/g, '$1');
  result = result.replace(/\*\*(.+?)\*\*/g, '$1');
  result = result.replace(/__(.+?)__/g, '$1');
  result = result.replace(/(?<!\w)\*(?!\s)(.+?)(?<!\s)\*(?!\w)/g, '$1');
  result = result.replace(/(?<!\w)_(?!\s)(.+?)(?<!\s)_(?!\w)/g, '$1');

  // Inline code / code fences: `code` or ```code``` -> code
  result = result.replace(/```([\s\S]*?)```/g, '$1');
  result = result.replace(/`([^`]+)`/g, '$1');

  // Headers: "## Heading" -> "Heading"
  result = result.replace(/^#{1,6}\s+(.+)$/gm, '$1');

  // Bullet lists: "- item" or "* item" -> "• item"
  result = result.replace(/^[ \t]*[-*][ \t]+(.+)$/gm, '• $1');

  // Blockquotes: "> text" -> "text"
  result = result.replace(/^>\s?(.+)$/gm, '$1');

  // Collapse 3+ blank lines down to a max of 2 (one visible blank line)
  result = result.replace(/\n{3,}/g, '\n\n');

  return result.trim();
}

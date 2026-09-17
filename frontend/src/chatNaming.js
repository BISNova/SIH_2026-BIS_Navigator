/**
 * Generates a chat title from the user's first message - no AI call,
 * no API, no cost. Pure string processing:
 *   1. Strip punctuation.
 *   2. Drop common filler words that carry no topical meaning.
 *   3. Take the first few remaining words, title-case them.
 *   4. Truncate if still too long for the sidebar.
 *
 * This mirrors the same "strip filler words, keep the meaningful
 * terms" approach product_intelligence/src/normalize.py uses for
 * product matching - same idea, applied to a different problem.
 */

const FILLER_WORDS = new Set([
  'i', 'we', 'am', 'is', 'are', 'the', 'a', 'an', 'of', 'for', 'to',
  'my', 'our', 'want', 'would', 'like', 'need', 'make', 'makes',
  'making', 'manufacture', 'manufacturing', 'please', 'help', 'with',
  'and', 'in', 'on', 'what', 'tell', 'me', 'about', 'you', 'your',
  'can', 'do', 'does', 'it', 'this', 'that', 'how',
]);

const MAX_TITLE_WORDS = 6;
const MAX_TITLE_LENGTH = 42;

export function generateChatTitle(firstMessage) {
  if (!firstMessage || !firstMessage.trim()) {
    return 'New Chat';
  }

  const rawWords = firstMessage
    .replace(/[^\w\s]/g, ' ')
    .split(/\s+/)
    .filter(Boolean);

  const meaningfulWords = rawWords.filter(
    (w) => !FILLER_WORDS.has(w.toLowerCase())
  );

  // If filtering removed everything (e.g. "what is this"), fall back to
  // the raw words rather than showing a blank/generic title.
  const words = (meaningfulWords.length > 0 ? meaningfulWords : rawWords)
    .slice(0, MAX_TITLE_WORDS);

  if (words.length === 0) {
    return 'New Chat';
  }

  const title = words
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');

  return title.length > MAX_TITLE_LENGTH
    ? title.slice(0, MAX_TITLE_LENGTH).trim() + '…'
    : title;
}

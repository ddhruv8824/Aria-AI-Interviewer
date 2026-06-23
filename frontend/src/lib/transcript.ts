/**
 * Merge streaming transcript fragments into one message.
 *
 * Gemini may send:
 *  - Cumulative text: "Hi" → "Hi Aria" → "Hi Aria, I'm…"
 *  - Incremental fragments: "Hi" → "Aria," → "I'm" → "and"
 */
export function mergeTranscriptText(existing: string, chunk: string): string {
  const prev = existing.trimEnd();
  const next = chunk.trim();
  if (!prev) return next;
  if (!next) return prev;

  // Cumulative: new chunk is the full text so far
  if (next.startsWith(prev)) return next;
  if (prev.startsWith(next)) return prev;

  // Exact duplicate
  if (prev === next) return prev;
  if (prev.endsWith(next)) return prev;

  // Overlap at boundary (e.g. prev="…inter" next="view today")
  const maxOverlap = Math.min(prev.length, next.length, 32);
  for (let i = maxOverlap; i > 0; i--) {
    if (prev.slice(-i) === next.slice(0, i)) {
      return prev + next.slice(i);
    }
  }

  // Punctuation attaches directly
  const prevLast = prev.slice(-1);
  const nextFirst = next[0];
  if (/^[.,!?;:%)\]}\]]/.test(nextFirst)) return prev + next;
  if (/[({[\-'"]$/.test(prevLast)) return prev + next;
  if (nextFirst === "'" || prevLast === "'") return prev + next;
  if (prevLast === "-" || nextFirst === "-") return prev + next;

  // Default: separate word fragments need a space
  return `${prev} ${next}`;
}

/**
 * Plain words on screen. The API names the confidence word "Strong match" and the baseline "word matching";
 * customers read "Confident" and "the current method". A trailing "a broker should confirm it" is dropped where the
 * "Needs a broker" badge already says so.
 */
export function plain(text: string | null | undefined): string {
  return (text ?? "")
    .replace(/\b([Aa]) Strong match\b/g, "$1 confident match")
    .replace(/\bStrong match\b/g, "Confident")
    .replace(/\bstrong match\b/g, "confident")
    .replace(/\bWord matching\b/g, "Current method")
    .replace(/\b([Bb]y |than |to |as good as )word matching\b/g, "$1the current method")
    .replace(/\bword matching\b/g, "the current method");
}

/** The verdict sentence without the broker clause the badge already carries. */
export function withoutBrokerClause(text: string): string {
  return text.replace(/[;,]\s*a (licensed )?broker should confirm[^.]*\./i, ".");
}

/**
 * Typewriter type primitives (DESIGN.md §0b). Headings are typed like a ruling letter in Courier Prime; the classes
 * live in styles/app.css (ty-letterhead, ty-caption, ty-title, ty-head, ty-sub, ty-law, ty-rule, ty-ruled).
 */

/** A typed rule line: a run of hyphens, or of equals signs for a double rule. Decorative. */
export function TypedRule(props: { double?: boolean; class?: string }) {
  return <span class={`ty-rule ${props.class ?? ""}`} data-double={props.double ? "" : undefined} aria-hidden="true" />;
}

/** "RE:" before a caption, as on a ruling letter's subject line. Hidden from screen readers. */
export function Re() {
  return (
    <span class="ty-re" aria-hidden="true">
      RE:
    </span>
  );
}

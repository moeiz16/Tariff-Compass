/**
 * Landed-cost helpers. Every duty line must carry a source and an effective date: the UI refuses to render a line
 * without them. Charges add on the same customs value; they don't compound.
 */
import type { LandedCostOut, LayerLineOut } from "./types";

export function renderableLines(lines: LayerLineOut[]): { shown: LayerLineOut[]; refused: LayerLineOut[] } {
  const shown: LayerLineOut[] = [];
  const refused: LayerLineOut[] = [];
  for (const l of lines) (l.source?.trim() && l.effectiveFrom ? shown : refused).push(l);
  return { shown, refused };
}

export interface StackSegment {
  key: string;
  kind: LayerLineOut["kind"] | "value";
  label: string;
  share: number; // 0..1 of the landed total
}

/** One horizontal bar from $0: the goods value, then each charge in order. */
export function stackSegments(cost: LandedCostOut): StackSegment[] {
  const { shown } = renderableLines(cost.lines);
  const value = Number(cost.value.amount);
  const total = value + shown.reduce((s, l) => s + Number(l.amount.amount), 0);
  if (!(total > 0)) return [];
  return [
    { key: "value", kind: "value", label: "Goods value", share: value / total },
    ...shown.map((l) => ({ key: l.letter, kind: l.kind, label: `${l.letter}. ${l.name}`, share: Number(l.amount.amount) / total })),
  ];
}

export function hasOpenLegalStatus(cost: LandedCostOut): boolean {
  return cost.lines.some((l) => l.legalStatusOpen);
}

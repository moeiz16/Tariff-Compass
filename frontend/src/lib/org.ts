/** Small shared lookups for signed-in pages: the organisation's broker name and an answer cache. */
import { createResource } from "solid-js";
import { org } from "./endpoints";
import type { AnswerOut } from "./types";

let brokerCache: Promise<string> | null = null;
export function brokerName(): Promise<string> {
  brokerCache ??= org
    .settings()
    .then((s) => s.brokerName?.split(" ")[0] ?? "your broker")
    .catch(() => {
      brokerCache = null;
      return "your broker";
    });
  return brokerCache;
}
export function useBrokerName() {
  const [name] = createResource(brokerName);
  return () => name() ?? "your broker";
}

const answers = new Map<string, AnswerOut>();
export const answerCache = {
  get: (id: string) => answers.get(id),
  put: (a: AnswerOut) => answers.set(a.id, a),
};

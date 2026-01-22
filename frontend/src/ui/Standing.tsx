import type { Standing } from "~/lib/types";
import { KindTag } from "./Status";

export function StandingTag(props: { standing: Standing; label: string }) {
  const t = () =>
    ({
      approved: { tone: "ok", icon: "ok" },
      in_review: { tone: "ink", icon: "ask" },
      needs_recheck: { tone: "warn", icon: "warn" },
      proposed: { tone: "muted", icon: undefined },
      withdrawn: { tone: "muted", icon: "revoked" },
    })[props.standing] as { tone: "ok" | "ink" | "warn" | "muted"; icon?: "ok" | "ask" | "warn" | "revoked" };
  return (
    <KindTag tone={t().tone} icon={t().icon}>
      {props.label}
    </KindTag>
  );
}

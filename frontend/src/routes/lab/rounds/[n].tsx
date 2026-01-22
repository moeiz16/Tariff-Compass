import { useParams } from "@solidjs/router";
import { LabPage } from "~/components/lab/LabPage";

export default function LabRound() {
  const params = useParams<{ n: string }>();
  return <LabPage n={Number(params.n)} />;
}

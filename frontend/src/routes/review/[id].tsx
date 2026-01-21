import { Navigate, useParams } from "@solidjs/router";

/** /review/<id> opens the docket with that row unfolded. */
export default function ReviewItem() {
  const params = useParams<{ id: string }>();
  return <Navigate href={`/review?open=${encodeURIComponent(params.id)}`} />;
}

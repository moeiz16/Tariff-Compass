import { Title } from "@solidjs/meta";
import { HttpStatusCode } from "@solidjs/start";

export default function NotFound() {
  return (
    <main class="mx-auto max-w-[var(--spacing-measure)] px-4 py-24">
      <Title>Not found · Tariff Compass</Title>
      <HttpStatusCode code={404} />
      <h1 class="text-2xl font-bold">We couldn't find that page.</h1>
    </main>
  );
}

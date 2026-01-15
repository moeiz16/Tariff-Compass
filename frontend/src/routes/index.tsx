import { Title } from "@solidjs/meta";

// Bare shell. The front page, results memo and every other screen are built from frontend/DESIGN.md.
export default function FrontPage() {
  return (
    <main class="mx-auto max-w-[var(--spacing-measure)] px-4 py-24">
      <Title>Tariff Compass</Title>
      <h1 class="text-4xl font-bold tracking-tight">Tariff Compass</h1>
      <p class="mt-4 text-lg text-ink-2">
        Describe a product. Get its US and Canadian tariff codes, the customs rulings that back them, and every duty
        it will carry.
      </p>
    </main>
  );
}

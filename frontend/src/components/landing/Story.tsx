/** Below the fold, like the news strip under a search box: Why now, Anatomy of an answer, For brokers, How we measure. */
import { A } from "@solidjs/router";
import { For, type JSX } from "solid-js";
import { CodeDigits } from "~/ui/Code";
import { button } from "~/ui/recipes";

function StoryRow(props: { n: string; label: string; id: string; title: JSX.Element; children: JSX.Element }) {
  return (
    <section id={props.id} aria-labelledby={`${props.id}-h`} class="gm border-t border-rule py-14 max-md:py-10">
      <p class="font-code text-[13px] text-muted max-[960px]:mb-3">
        {props.n} · {props.label}
      </p>
      <div class="gm-wide max-w-[1080px]">
        <h2 id={`${props.id}-h`} class="text-[clamp(30px,4vw,46px)] font-[800] leading-[1.08] tracking-[-0.02em]">
          {props.title}
        </h2>
        <div class="mt-6">{props.children}</div>
      </div>
    </section>
  );
}

const FACTS = [
  { date: "29 Aug 2025", text: "Duty-free de minimis ended for parcels from every country (EO 14324). Every parcel now needs a code, and pays on it." },
  { date: "19 U.S.C. 1484", text: "The importer of record must use reasonable care to classify. A broker helps; the duty to get it right stays with you." },
  { date: "Duties stack", text: "A base rate, trade remedies and emergency duties can all apply to the same value. Each has its own source and date." },
];

const ANATOMY = [
  { key: <CodeDigits code="9617.00.10.00" size="md" />, title: "The code, in both countries", text: "US HTSUS and Canada's Customs Tariff, ten digits each, with the heading text quoted." },
  { key: <span class="font-code text-[17px] font-[600]">GRI 1 → GRI 6</span>, title: "The path, step by step", text: "Section, chapter, heading, subheading, with the rule used at each step and the neighbour it set aside." },
  { key: <span class="font-code text-[17px] font-[600]">[1] [2] [3]</span>, title: "A ruling behind every sentence", text: "Real CBP rulings, each with its status: in force, modified, revoked or cited for contrast." },
  { key: <span class="font-code text-[17px] font-[600]">$3,458.93</span>, title: "Every duty, with its source", text: "A receipt of each charge with its rate, its source, its effective date and any open legal question." },
];

export function Story() {
  return (
    <div>
      <StoryRow n="01" label="Why now" id="why" title={<>Every parcel needs a code now, and the code is on you.</>}>
        <ul class="grid grid-cols-3 gap-8 max-lg:grid-cols-1">
          <For each={FACTS}>
            {(f) => (
              <li class="border-t-[1.5px] border-ink pt-3">
                <p class="font-code text-[13.5px] font-[600]">{f.date}</p>
                <p class="mt-1.5 text-[16.5px] leading-[1.55] text-ink-2">{f.text}</p>
              </li>
            )}
          </For>
        </ul>
      </StoryRow>
      <StoryRow n="02" label="Anatomy of an answer" id="anatomy" title={<>Written like a customs ruling, so a broker can check it in one read.</>}>
        <ul class="grid grid-cols-4 gap-8 max-lg:grid-cols-2 max-sm:grid-cols-1">
          <For each={ANATOMY}>
            {(a) => (
              <li class="border-t border-rule pt-3">
                <p class="h-8">{a.key}</p>
                <p class="mt-2 text-[16.5px] font-[700]">{a.title}</p>
                <p class="mt-1 text-[15.5px] leading-[1.55] text-ink-2">{a.text}</p>
              </li>
            )}
          </For>
        </ul>
      </StoryRow>
      <StoryRow n="03" label="For brokers" id="brokers" title={<>Correct one digit, give one reason, and the next round learns it.</>}>
        <div class="grid grid-cols-[minmax(0,1fr)_minmax(0,1fr)] gap-10 max-lg:grid-cols-1">
          <div class="font-code text-[clamp(24px,3vw,34px)] font-[600] leading-[1.5]">
            <p>
              <span class="text-muted">Proposed </span>
              <span class="strike-bad">9617</span>.00.<span class="strike-bad">10</span>.<span class="strike-bad">0</span>0
            </p>
            <p>
              <span class="text-muted">Broker&nbsp;&nbsp; </span>
              <span class="hl">7323</span>.<span class="hl">93</span>.00.<span class="hl">8</span>0
            </p>
          </div>
          <div>
            <p class="font-law text-[18px] leading-[1.55]">
              “Spec sheet says air-insulated, not vacuum-sealed. Without a vacuum this is stainless steel tableware, as in NY N321985.”
            </p>
            <p class="mt-3 text-[15.5px] text-ink-2">
              The broker's code goes on the entry and into the product's binder with their name and licence. The correction becomes a labelled example for
              the next training round.
            </p>
            <A href="/signin" class={button({ tone: "ghost", size: "md", class: "mt-5" })}>
              Broker sign-in
            </A>
          </div>
        </div>
      </StoryRow>
      <StoryRow n="04" label="How we measure" id="measure" title={<>Accuracy is measured on rulings it hasn't seen, and shown every round.</>}>
        <div class="grid grid-cols-3 gap-8 max-lg:grid-cols-1">
          <p class="text-[16.5px] leading-[1.55] text-ink-2">
            Each training round is tested on the newest customs rulings, issued after everything it learned from, at four depths: chapter, heading,
            subheading and the full ten digits.
          </p>
          <p class="text-[16.5px] leading-[1.55] text-ink-2">
            The confidence word is checked against what happened: when it says <b>Strong match</b>, the Lab reports how many times in a hundred it was right.
            No percentages are shown on an answer.
          </p>
          <p class="text-[16.5px] leading-[1.55] text-ink-2">
            A new round goes live only after five checks pass and two people sign: the compliance lead and a licensed broker.
          </p>
        </div>
      </StoryRow>
    </div>
  );
}

export function PublicFooter() {
  return (
    <footer class="border-t-[1.5px] border-ink px-8 py-10 max-md:px-4">
      <div class="mx-auto max-w-[1160px]">
        <p class="max-w-[860px] text-[14.5px] leading-[1.6] text-ink-2">
          Designed to support reasonable-care record keeping under 19 U.S.C. 1484 and 19 CFR Part 163, and CBSA advance ruling requests under Memorandum
          D11-11-3. Not legal advice; a licensed customs broker approves every code before it's used on an entry.
        </p>
        <p class="mt-2 text-[13.5px] text-muted">Sample answers use Northbound Goods Co., a sample importer. Rulings cited are real CBP rulings.</p>
        <div class="mt-5 flex flex-wrap gap-3">
          <a href="#top" class={button({ size: "md" })}>
            Classify a sample
          </a>
          <A href="/signin" class={button({ tone: "ghost", size: "md" })}>
            Broker sign-in
          </A>
        </div>
      </div>
    </footer>
  );
}

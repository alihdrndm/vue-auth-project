<script setup lang="ts">
// The public homepage (HANDOFF "Homepage", design "Eingang Homepage"): the hero, Act 1 (every
// format lands in one inbox), Act 2 (someone still has to say yes), the facts with their
// sources, and the sandbox. "Open the sandbox" calls POST /sandbox and goes to the inbox.
import { ref } from "vue";
import { useRouter } from "vue-router";

import { ApiError } from "../api/client";
import Button from "../components/ui/Button.vue";
import Icon from "../components/ui/Icon.vue";
import Stamp from "../components/ui/Stamp.vue";
import ActOne from "../features/homepage/ActOne.vue";
import ActTwo from "../features/homepage/ActTwo.vue";
import { useSeenOnce } from "../features/homepage/motion";
import { useSessionStore } from "../stores/session";

const GITHUB = "https://github.com/alihdrndm/eingang";
const EC_SOURCE =
  "https://ec.europa.eu/digital-building-blocks/sites/spaces/DIGITAL/pages/467108886/eInvoicing+in+Germany";

const session = useSessionStore();
const router = useRouter();

/** Shown once, for example after a sandbox expired. */
const notice = ref(session.takeNotice());
const error = ref<string | null>(null);
const opening = ref(false);

const actOne = ref<HTMLElement | null>(null);
const actTwo = ref<HTMLElement | null>(null);
const actOneSeen = useSeenOnce(actOne, 0.3);
const actTwoSeen = useSeenOnce(actTwo, 0.3);

/** Which call to action was pressed, so its message appears next to it. */
const pressedAt = ref<"top" | "close">("top");

async function openSandbox(at: "top" | "close" = "top"): Promise<void> {
  pressedAt.value = at;
  if (opening.value) return;
  opening.value = true;
  error.value = null;
  notice.value = null;
  try {
    await session.openSandbox();
    await router.push({ name: "inbox" });
  } catch (caught) {
    error.value =
      caught instanceof ApiError
        ? caught.detail || caught.title
        : "The sandbox could not be opened. Check your connection and try again.";
  } finally {
    opening.value = false;
  }
}
</script>

<template>
  <div class="home">
    <header class="top">
      <RouterLink to="/" class="brand" aria-label="Eingang, home">
        <Stamp size="mark" :mark-size="28" />
        <span>Eingang</span>
      </RouterLink>
      <nav class="top__nav" aria-label="Site">
        <a :href="GITHUB" rel="noopener">GitHub</a>
        <RouterLink :to="{ name: 'sign-in' }">Sign in</RouterLink>
        <Button
          variant="primary"
          size="sm"
          :loading="opening"
          @click="openSandbox('top')"
        >
          Open the sandbox
        </Button>
      </nav>
    </header>

    <main>
      <section class="hero" aria-labelledby="hero-title">
        <div class="hero__text">
          <h1 id="hero-title" class="hero__title">
            Some of our invoices are e-invoices. We couldn’t tell you which.
          </h1>
          <p class="hero__lede">
            Eingang puts every supplier invoice, XML or PDF, in one inbox and
            tells you which ones are valid e-invoices. It flags duplicates and
            changed bank accounts, and someone else approves before anything
            goes to the tax advisor.
          </p>
          <p v-if="notice" class="notice" role="status">{{ notice }}</p>
          <div class="cta">
            <Button
              variant="primary"
              size="lg"
              :loading="opening"
              @click="openSandbox('top')"
            >
              {{ opening ? "Opening the sandbox…" : "Open the sandbox" }}
            </Button>
            <RouterLink :to="{ name: 'sign-in' }" class="cta__link"
              >Sign in</RouterLink
            >
          </div>
          <p class="error" role="alert">
            {{ pressedAt === "top" ? error : null }}
          </p>
          <p class="small">Free and open source. No sign-up for the sandbox.</p>
        </div>
        <div class="hero__art" aria-hidden="true">
          <div class="sheet sheet--xml">
            <pre class="xml"><code>&lt;Invoice&gt;
  &lt;cbc:ID&gt;RE-2026-0413&lt;/cbc:ID&gt;
  &lt;cbc:IssueDate&gt;2026-10-08&lt;/…&gt;
  &lt;cbc:DueDate&gt;2026-10-22&lt;/…&gt;
  &lt;cac:AccountingSupplierParty&gt;
    &lt;cbc:Name&gt;Elektro Kessler&lt;/…&gt;
  &lt;cbc:PayableAmount&gt;<mark class="hl">238.00</mark>&lt;/…&gt;
&lt;/Invoice&gt;</code></pre>
          </div>
          <div class="sheet sheet--pdf">
            <p class="sheet__from">Druckerei Sommer GmbH</p>
            <p class="sheet__title">Rechnung 2026-1043</p>
            <p class="sheet__line">
              <span>Nettobetrag</span><span>1.300,00 €</span>
            </p>
            <p class="sheet__line">
              <span>USt. 19 %</span><span>247,00 €</span>
            </p>
            <p class="sheet__line sheet__line--total">
              <span>Gesamtbetrag</span><span>1.547,00 €</span>
            </p>
            <Stamp
              size="lg"
              date="2026-10-09"
              :rotate="-7"
              class="sheet__stamp"
            />
          </div>
          <span class="pen pen--hero">XML inside?</span>
        </div>
      </section>

      <section ref="actOne" class="act" aria-labelledby="act-one-title">
        <div class="act__intro">
          <h2 id="act-one-title" class="act__title">
            Every format lands in one inbox.
          </h2>
          <p>
            XRechnung, ZUGFeRD or a plain PDF: each one is stamped, checked
            against the official rules and given a verdict you can read. For
            plain PDFs, AI reads the fields and shows the text each one came
            from.
          </p>
        </div>
        <ActOne />
        <span
          class="pen pen--note"
          :class="{ 'pen--drawn': actOneSeen }"
          aria-hidden="true"
          >finally, someone tells me which ones count</span
        >
      </section>

      <section ref="actTwo" class="act" aria-labelledby="act-two-title">
        <div class="act__intro">
          <h2 id="act-two-title" class="act__title">
            Someone still has to say yes.
          </h2>
          <p>
            Anna resolves the check and marks the invoice reviewed. Jonas
            approves it on his phone. With four-eyes on, nobody approves an
            invoice they reviewed themselves.
          </p>
        </div>
        <ActTwo />
        <span
          class="pen pen--note"
          :class="{ 'pen--drawn': actTwoSeen }"
          aria-hidden="true"
          >this is how invoice fraud starts</span
        >
      </section>

      <section class="facts" aria-label="Facts">
        <article class="fact">
          <h2 class="fact__title">Receiving: since 1 Jan 2025</h2>
          <p>
            Every German business must be able to receive structured e-invoices
            (EN 16931).
          </p>
          <a :href="EC_SOURCE" rel="noopener">Source: European Commission</a>
        </article>
        <article class="fact">
          <h2 class="fact__title">Sending: from 2027 and 2028</h2>
          <p>
            Plain PDFs stop counting for domestic business invoices: from 2027
            above €800,000 turnover, from 2028 for every business. Invoices up
            to €250 stay exempt.
          </p>
          <a :href="EC_SOURCE" rel="noopener">Source: European Commission</a>
        </article>
        <article class="fact">
          <h2 class="fact__title">
            Checks the official EN 16931 and XRechnung rules
          </h2>
          <p>
            Every verdict names the rule it rests on and says in plain English
            what to do.
          </p>
        </article>
        <article class="fact">
          <h2 class="fact__title">AI shows where every value came from</h2>
          <p>
            For plain PDFs, each value comes with the text it was read from.
            Scans have no text, so those are typed in by hand.
          </p>
        </article>
        <article class="fact">
          <h2 class="fact__title">Open source, MIT</h2>
          <p>The code is on GitHub. Read it, check it, change it.</p>
          <a :href="GITHUB" rel="noopener">GitHub</a>
        </article>
      </section>

      <section class="close" aria-labelledby="close-title">
        <h2 id="close-title" class="act__title">
          The sandbox has all twelve sample invoices.
        </h2>
        <p>
          Stamp them, check them, approve them. Nothing in there is real, and it
          deletes itself.
        </p>
        <div class="cta">
          <Button
            variant="primary"
            size="lg"
            :loading="opening"
            @click="openSandbox('close')"
          >
            Open the sandbox
          </Button>
          <RouterLink :to="{ name: 'sign-in' }" class="cta__link"
            >Sign in</RouterLink
          >
        </div>
        <p class="error" role="alert">
          {{ pressedAt === "close" ? error : null }}
        </p>
        <p class="small">Free and open source. No sign-up for the sandbox.</p>
        <RouterLink :to="{ name: 'accuracy-public' }" class="accuracy">
          How accurate is it? Measured, with the method
          <Icon name="chevron-right" :size="16" />
        </RouterLink>
      </section>
    </main>

    <footer class="footer">
      <span class="brand"
        ><Stamp size="mark" :mark-size="24" /><span>Eingang</span></span
      >
      <span>Not tax advice. Eingang checks published technical rules.</span>
      <a :href="GITHUB" rel="noopener">GitHub</a>
    </footer>
  </div>
</template>

<style scoped>
.home {
  min-height: 100vh;
  overflow-x: clip; /* the tilted hero sheets may poke out; the page never scrolls sideways */
  background: var(--bar);
  color: var(--text);
  line-height: 1.6;
}

.top,
main,
.footer {
  max-width: 1280px;
  margin: 0 auto;
  padding-inline: var(--space-24);
}

.top {
  display: flex;
  gap: var(--space-16);
  align-items: center;
  justify-content: space-between;
  padding-block: var(--space-16);
}

.brand {
  display: inline-flex;
  gap: var(--space-8);
  align-items: center;
  color: var(--ink);
  font-family: var(--font-head);
  font-size: var(--fs-21);
  font-weight: 700;
  text-decoration: none;
}

.top__nav {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-16);
  align-items: center;
}

.top__nav a,
.cta__link,
.footer a {
  color: var(--ink);
}

.hero {
  display: grid;
  grid-template-columns: minmax(0, 6fr) minmax(0, 5fr);
  gap: var(--space-40);
  align-items: center;
  padding-block: var(--space-40) 72px;
}

.hero__title {
  margin: 0;
  color: var(--ink);
  font-family: var(--font-head);
  font-size: clamp(38px, 4.6vw, 66px);
  font-weight: 700;
  letter-spacing: -0.025em;
  line-height: 1.05;
  text-wrap: balance;
}

.hero__lede {
  max-width: 60ch;
  margin: var(--space-24) 0;
  font-size: 17px;
}

.cta {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-16);
  align-items: center;
}

.notice {
  padding: var(--space-8) var(--space-12);
  border-radius: var(--r-md);
  background: var(--stamp-soft);
  color: var(--stamp);
}

.error {
  min-height: 1lh;
  margin: var(--space-8) 0 0;
  color: var(--block);
}

.error:empty {
  min-height: 0;
}

.small {
  margin: var(--space-8) 0 0;
  color: var(--muted);
  font-size: var(--fs-13);
}

.hero__art {
  position: relative;
  min-height: 380px;
}

.sheet {
  position: absolute;
  border: 1px solid var(--line);
  border-radius: var(--r-sm);
  background: var(--paper);
  box-shadow: var(--shadow-sheet);
}

.sheet--xml {
  top: 0;
  left: 0;
  width: 68%;
  padding: var(--space-16);
  transform: rotate(-3deg);
}

.xml {
  margin: 0;
  font-family: var(--font-mono);
  font-size: var(--fs-12);
  white-space: pre;
  overflow: hidden;
}

.hl {
  background: var(--hl);
  color: inherit;
}

.sheet--pdf {
  top: 110px;
  right: 0;
  width: 62%;
  padding: var(--space-20);
  transform: rotate(2deg);
  font-size: var(--fs-13);
}

.sheet__from {
  margin: 0;
  font-weight: 600;
}

.sheet__title {
  margin: var(--space-12) 0;
  font-family: var(--font-head);
  font-weight: 700;
}

.sheet__line {
  display: flex;
  justify-content: space-between;
  margin: 0;
}

.sheet__line--total {
  margin-top: var(--space-8);
  font-weight: 600;
}

.sheet__stamp {
  position: absolute;
  right: -18px;
  bottom: -64px;
}

.pen {
  color: var(--pen);
  font-family: var(--font-hand);
  font-size: 28px;
  font-weight: 600;
  line-height: 1.1;
}

.pen--hero {
  position: absolute;
  top: 62%;
  left: 2%;
  transform: rotate(-6deg);
}

.pen--note {
  display: block;
  margin-top: var(--space-16);
  text-align: right;
  clip-path: inset(0 100% 0 0);
  transition: clip-path 400ms var(--ease-draw);
}

.pen--drawn {
  clip-path: inset(0 0 0 0);
}

.act {
  padding-block: 72px;
  border-top: 1px solid var(--line);
}

.act__intro {
  max-width: 62ch;
  margin-bottom: var(--space-40);
}

.act__title {
  margin: 0 0 var(--space-16);
  color: var(--ink);
  font-family: var(--font-head);
  font-size: clamp(28px, 2.6vw, 42px);
  font-weight: 700;
  line-height: 1.15;
}

.facts {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: var(--space-24);
  padding-block: 72px;
  border-top: 1px solid var(--line);
}

.fact__title {
  margin: 0 0 var(--space-8);
  color: var(--ink);
  font-family: var(--font-head);
  font-size: var(--fs-16);
  font-weight: 700;
}

.fact p {
  margin: 0 0 var(--space-8);
}

.fact a {
  color: var(--stamp);
  font-size: var(--fs-13);
}

.close {
  display: grid;
  justify-items: center;
  gap: var(--space-8);
  padding-block: 72px;
  border-top: 1px solid var(--line);
  text-align: center;
}

.close p {
  margin: 0;
}

.accuracy {
  display: inline-flex;
  gap: var(--space-4);
  align-items: center;
  margin-top: var(--space-16);
  color: var(--stamp);
}

.footer {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-16);
  align-items: center;
  justify-content: space-between;
  padding-block: var(--space-24);
  border-top: 1px solid var(--line);
  color: var(--muted);
  font-size: var(--fs-13);
}

@media (max-width: 1099px) {
  main,
  .top,
  .footer {
    max-width: 680px;
    padding-inline: var(--space-16);
  }

  .hero {
    grid-template-columns: 1fr;
    padding-block: var(--space-24) var(--space-40);
  }

  .hero__art {
    min-height: 300px;
  }

  .act,
  .facts,
  .close {
    padding-block: var(--space-40);
  }

  .act__title {
    font-size: 28px;
  }

  .top__nav :deep(button),
  .cta :deep(button) {
    min-height: 44px;
  }
}

@media (max-width: 480px) {
  .top__nav a:first-child {
    display: none;
  }
}

@media (prefers-reduced-motion: reduce) {
  .pen--note {
    clip-path: none;
    transition: none;
  }
}
</style>

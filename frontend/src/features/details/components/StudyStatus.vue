<script setup lang="ts">
import { computed } from "vue";
import BreakableText from "../../../components/common/BreakableText.vue";
import { externalUrl, type DetailRecord } from "../types";
const props = defineProps<{ study: DetailRecord }>();
const issueBase = "https://github.com/matthiaskoenig/pkdb_data/issues/";
const reviews: Record<string, string> = {
  draft: "Draft",
  in_review: "In review",
  approved: "Approved",
};
function string(value: unknown): string | undefined {
  return typeof value === "string" && value ? value : undefined;
}
const identifier = computed(() => string(props.study.sid));
const pkdbId = computed(() => string(props.study.pkdb_id));
const released = computed(() => string(props.study.release_date));
const issue = computed(() => {
  const number = props.study.issue;
  return typeof number === "number" && Number.isSafeInteger(number)
    ? { number, url: externalUrl(`${issueBase}${number}`) }
    : undefined;
});
const review = computed(() => {
  const status = string(props.study.review_status);
  if (!status) return undefined;
  const open = Number(props.study.open_review_items) || 0;
  return [
    reviews[status] ?? status,
    open === 0
      ? "no open items"
      : `${open} open ${open === 1 ? "item" : "items"}`,
  ].join(" · ");
});
const shown = computed(
  () =>
    identifier.value ||
    pkdbId.value ||
    released.value ||
    issue.value ||
    review.value,
);
</script>
<template>
  <section v-if="shown" class="study-status" aria-label="Study status">
    <dl>
      <div v-if="identifier" class="wide">
        <dt>Identifier</dt>
        <dd><BreakableText :text="identifier" /></dd>
      </div>
      <div v-if="pkdbId">
        <dt>PKDB identifier</dt>
        <dd>{{ pkdbId }}</dd>
      </div>
      <div v-if="released">
        <dt>Released</dt>
        <dd>{{ released }}</dd>
      </div>
      <div v-if="issue">
        <dt>Curation issue</dt>
        <dd>
          <a
            v-if="issue.url"
            :href="issue.url"
            target="_blank"
            rel="noopener noreferrer"
            >#{{ issue.number }}</a
          ><template v-else>#{{ issue.number }}</template>
        </dd>
      </div>
      <div v-if="review" class="wide">
        <dt>Review</dt>
        <dd>{{ review }}</dd>
      </div>
    </dl>
  </section>
</template>
<style scoped>
/* Two aligned columns on a phone, one wrapping row from tablet width. */
dl {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.75rem 1rem;
  margin: 0;
}
.wide {
  grid-column: 1 / -1;
}
dt {
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: rgba(var(--v-theme-on-surface), 0.7);
}
dd {
  margin: 0;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  overflow-wrap: break-word;
}
@media (min-width: 700px) {
  dl {
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem 2rem;
  }
}
</style>

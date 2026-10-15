<script setup lang="ts">
import { computed, onMounted, ref, useId } from "vue";
import { VCard, VCardItem, VCardText, VCardTitle, VChip } from "vuetify/components";
import { useStudyViews } from "../context";
import {
  identifierFacts,
  NEW_TAB,
  PROVENANCE_LABELS,
  provenanceFacts,
  referenceMatch,
  referenceView,
  type Fact,
} from "../metadataView";
import { issueUrl } from "../overview";
import { knownProfiles, profileOf, releaseLabel } from "../study";
import type { Profile } from "../types";

/**
 * The metadata of a study as text, read only, in the cards of the form of the curation app
 * (MetadataSection.vue): the reference with its identifiers, the people (the ratings of the
 * curators when the page has them), the licence, access and provenance, the issue and the
 * release, and the descriptions and comments. The issue and the match of reference.json show
 * with the curation; without it the card of the issue and the release is titled Release. What
 * cannot show names the files of the study only with `edit`. Every link opens in a new tab and
 * its name says what it opens.
 */
const views = useStudyViews();
const detail = views.data.detail;
const capabilities = views.capabilities;
const ids = { reference: useId(), people: useId(), access: useId(), release: useId(), notes: useId() };

const metadata = computed(() => detail.value?.metadata.value ?? null);

// Profiles: the curators that the page knows, and the people of the study who are not among them.
const roster = ref<Profile[]>([]);
onMounted(() => {
  views.data.curators().then(
    (profiles) => (roster.value = profiles),
    // Without the curators the comments show user names.
    () => undefined,
  );
});
const profiles = computed(() => knownProfiles(roster.value, detail.value?.people));
const nameOf = (user: string) => profileOf(profiles.value, user).display_name;

const reference = computed(() => referenceView(detail.value?.reference ?? null));
const invalidText = computed(() =>
  capabilities.value.edit ? "study.json is not valid, so its metadata cannot show." : "The metadata of this study cannot show.",
);
const untitled = computed(() => (capabilities.value.edit ? "No title in reference.json" : "No title"));
const referenceError = computed(() =>
  reference.value.kind === "error" && capabilities.value.edit ? reference.value.text : "The reference cannot show.",
);
const match = computed(() => referenceMatch(detail.value?.reference_match ?? null, capabilities.value.edit));
const identifiers = computed(() => identifierFacts(metadata.value?.reference));

const people = computed<Fact[]>(() => {
  const value = detail.value?.people;
  // The website sends the ratings only to readers who may write the study.
  const curators = (value?.curators ?? []).map(({ rating, profile }) =>
    typeof rating === "number" ? `${profile.display_name} (rating ${rating} of 5)` : profile.display_name,
  );
  const collaborators = value?.collaborators.length
    ? value.collaborators.map((person) => person.display_name)
    : (metadata.value?.collaborators ?? []);
  const creator = value?.creator?.display_name ?? (metadata.value?.creator ? nameOf(metadata.value.creator) : null);
  return [
    { name: "Creator", value: creator ?? "None" },
    { name: "Curators", value: curators.join(", ") || "None" },
    { name: "Collaborators", value: collaborators.join(", ") || "None" },
  ];
});

const access = computed<Fact[]>(() => {
  const value = metadata.value;
  if (!value) return [];
  return [
    { name: "Licence", value: value.licence === "open" ? "Open" : "Closed" },
    { name: "Access", value: value.access === "public" ? "Public" : "Private" },
    { name: "Provenance", value: PROVENANCE_LABELS[value.provenance.kind] },
    ...provenanceFacts(value.provenance),
  ];
});

const release = computed<Fact[]>(() => {
  const value = metadata.value;
  const facts: Fact[] = [];
  const shown = detail.value;
  if (capabilities.value.curation && shown) {
    const number = shown.issue?.number ?? value?.issue ?? null;
    if (number === null) facts.push({ name: "Issue", value: "No issue" });
    else {
      // The link goes to the issue that the card names, also when only study.json names it.
      const named = { issue: shown.issue, summary: { ...shown.summary, issue: number } };
      const href = issueUrl(named, views.data.repository.value);
      const link = href ? { href, label: `Issue #${number} on GitHub ${NEW_TAB}` } : {};
      facts.push({ name: "Issue", value: `#${number}`, ...link });
    }
  }
  facts.push({ name: "Release", value: value?.release ? releaseLabel(value.release) : "Not released" });
  return facts;
});

const cards = computed(() => [
  { id: ids.people, title: "People", facts: people.value },
  { id: ids.access, title: "Access and provenance", facts: access.value },
  // The public never sees an issue, so its card names the release alone.
  { id: ids.release, title: capabilities.value.curation ? "Issue and release" : "Release", facts: release.value },
]);
</script>

<template>
  <div class="metadata-view">
    <p v-if="!metadata" class="metadata-view-invalid">{{ invalidText }}</p>
    <div v-else class="metadata-view-cards">
      <VCard tag="section" border class="metadata-view-card" :aria-labelledby="ids.reference">
        <VCardItem class="metadata-view-head">
          <VCardTitle :id="ids.reference" tag="h3" class="metadata-view-title">Reference</VCardTitle>
        </VCardItem>
        <VCardText class="metadata-view-body">
          <VChip v-if="capabilities.curation" size="small" variant="tonal" :color="match.tone" class="status-chip reference-match">
            {{ match.label }}
          </VChip>
          <template v-if="reference.kind === 'reference'">
            <p class="reference-title" :class="{ 'reference-title--missing': !reference.title }">
              {{ reference.title || untitled }}
            </p>
            <p v-if="reference.authors" class="reference-line">{{ reference.authors }}</p>
            <p v-if="reference.source" class="reference-line reference-source">{{ reference.source }}</p>
          </template>
          <p v-else-if="reference.kind === 'error'" class="reference-line">{{ referenceError }}</p>
          <p v-else class="reference-line reference-source">No reference yet.</p>
          <dl v-if="identifiers.length" class="panel-facts">
            <template v-for="fact in identifiers" :key="fact.name">
              <dt>{{ fact.name }}</dt>
              <dd>
                <a :href="fact.href" :aria-label="fact.label" target="_blank" rel="noopener noreferrer">{{
                  fact.value
                }}</a>
              </dd>
            </template>
          </dl>
        </VCardText>
      </VCard>
      <VCard v-for="card in cards" :key="card.id" tag="section" border class="metadata-view-card" :aria-labelledby="card.id">
        <VCardItem class="metadata-view-head">
          <VCardTitle :id="card.id" tag="h3" class="metadata-view-title">{{ card.title }}</VCardTitle>
        </VCardItem>
        <VCardText class="metadata-view-body">
          <dl class="panel-facts">
            <template v-for="fact in card.facts" :key="fact.name">
              <dt>{{ fact.name }}</dt>
              <dd>
                <a
                  v-if="fact.href"
                  :href="fact.href"
                  :aria-label="fact.label"
                  target="_blank"
                  rel="noopener noreferrer"
                  >{{ fact.value }}</a
                >
                <template v-else>{{ fact.value }}</template>
              </dd>
            </template>
          </dl>
        </VCardText>
      </VCard>
      <VCard tag="section" border class="metadata-view-card" :aria-labelledby="ids.notes">
        <VCardItem class="metadata-view-head">
          <VCardTitle :id="ids.notes" tag="h3" class="metadata-view-title">Descriptions and comments</VCardTitle>
        </VCardItem>
        <VCardText class="metadata-view-body">
          <p v-for="(text, index) in metadata.descriptions" :key="`d${index}`" class="metadata-view-text">{{ text }}</p>
          <p v-for="(comment, index) in metadata.comments" :key="`c${index}`" class="metadata-view-text metadata-view-comment">
            <span class="metadata-view-author">{{ nameOf(comment.user) }}</span> <span>{{ comment.text }}</span>
          </p>
          <p v-if="!metadata.descriptions.length && !metadata.comments.length" class="field-empty">
            No descriptions or comments.
          </p>
        </VCardText>
      </VCard>
    </div>
  </div>
</template>

<style scoped>
/* The cards of the form of the curation app (MetadataSection.vue): side by side where two fit,
   from a window of about 1400px, as high as the higher one of their row. */
.metadata-view-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 36rem), 1fr));
  align-items: stretch;
  gap: 12px;
}
/* Five cards leave the last one alone in its row of two: it takes the whole row. */
.metadata-view-cards > .metadata-view-card:last-child:nth-child(odd) {
  grid-column: 1 / -1;
}
.metadata-view-head {
  padding-bottom: 0;
}
.metadata-view-title {
  font-size: 1rem;
  font-weight: 600;
  line-height: 1.5;
}
.metadata-view-body {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
}
.metadata-view-invalid,
.metadata-view-text,
.reference-title,
.reference-line {
  margin: 0;
  overflow-wrap: anywhere;
}
.reference-match {
  margin-bottom: 4px;
}
.reference-title {
  font-weight: 600;
}
.reference-title--missing {
  font-weight: 400;
  font-style: italic;
}
.reference-line {
  font-size: 0.875rem;
}
.reference-source {
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
.metadata-view-author {
  font-weight: 600;
}
</style>

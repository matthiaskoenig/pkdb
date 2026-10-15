<script setup lang="ts">
/**
 * The header of a study: its identity, release, issue and provenance, its title with what it is
 * doing, its PMID, sync state and problems, in one line. The page puts its actions into the slot
 * `actions`, at the end of the line, and what belongs to them below the line into the slot `after`.
 * Without the curation it shows no issue or problems, and without the jobs no sync state and not
 * what the study is doing; a reader of the curation who may not write sees the review status in
 * place of the actions, which show only with `edit`.
 */
import { computed } from "vue";
import { VChip } from "vuetify/components";
import type { StudyDetail } from "../types";
import { useStudyViews } from "../context";
import {
  activityLabel,
  issueUrl,
  problemLabels,
  REVIEW_LABELS,
  REVIEW_TONES,
  SYNC_LABELS,
  SYNC_TONES,
} from "../overview";
import { issueLabel, provenanceLabel, releaseLabel, studyName } from "../study";

const props = defineProps<{
  detail: StudyDetail;
}>();
defineSlots<{ actions?: () => unknown; after?: () => unknown }>();

const views = useStudyViews();
const capabilities = views.capabilities;

const substance = computed(() => props.detail.id.slice(0, props.detail.id.indexOf("/")));
const name = computed(() => studyName(props.detail));
const summary = computed(() => props.detail.summary);
const release = computed(() => (summary.value.release ? releaseLabel(summary.value.release) : null));
const issue = computed(() => {
  if (!capabilities.value.curation) return null;
  const label = issueLabel(props.detail.issue, summary.value.issue);
  if (label === null) return null;
  return { label, url: issueUrl(props.detail, views.data.repository.value) };
});
const provenance = computed(() => provenanceLabel(summary.value));
const pmid = computed(() => {
  const reference = props.detail.reference;
  const fromReference = reference && "pmid" in reference ? reference.pmid : null;
  return props.detail.metadata.value?.reference?.pmid ?? fromReference ?? null;
});
const problems = computed(() => (capabilities.value.curation ? problemLabels(props.detail) : []));
const activity = computed(() => (capabilities.value.jobs ? activityLabel(props.detail) : null));
const reviewStatus = computed(() => props.detail.review.value?.status ?? summary.value.review_status ?? null);
</script>

<template>
  <header class="study-header">
    <div class="study-header-line">
      <!-- A long identity wraps after the slash rather than inside a name. Its page may move the
           focus to it, as the website does when a study shows; it is no Tab stop. -->
      <h1 class="study-identity" tabindex="-1">{{ substance }}/<wbr />{{ name }}</h1>
      <template v-if="release || issue || provenance">
        <VChip
          v-if="release"
          size="x-small"
          variant="tonal"
          color="success"
          prepend-icon="fas fa-tag"
          class="status-chip release-chip"
        >
          {{ release }}
        </VChip>
        <template v-if="issue">
          <VChip
            v-if="issue.url"
            :href="issue.url"
            target="_blank"
            rel="noopener noreferrer"
            size="x-small"
            variant="outlined"
            prepend-icon="fas fa-circle-dot"
            class="header-chip issue-chip"
            :aria-label="`GitHub issue ${issue.label}`"
          >
            {{ issue.label }}
          </VChip>
          <VChip
            v-else
            size="x-small"
            variant="outlined"
            prepend-icon="fas fa-circle-dot"
            class="header-chip issue-chip"
          >
            {{ issue.label }}
          </VChip>
        </template>
        <VChip
          v-if="provenance"
          size="x-small"
          variant="outlined"
          prepend-icon="fas fa-robot"
          class="header-chip provenance-chip"
        >
          {{ provenance }}
        </VChip>
      </template>
      <!-- What the study is doing, such as Validating for a moment after every save, takes its
           room from the title, so that the line never wraps for it. -->
      <div class="study-title-box">
        <p
          class="study-title"
          :class="{ 'study-title--missing': !summary.title }"
          :title="summary.title || undefined"
        >
          {{ summary.title || "No reference title yet" }}
        </p>
        <template v-if="activity">
          <span class="study-title-dot" aria-hidden="true">·</span>
          <span class="fact-activity" :title="activity">{{ activity }}</span>
        </template>
      </div>
      <span v-if="pmid" class="fact-pmid">
        <span class="fact-name">PMID</span>
        <a :href="`https://pubmed.ncbi.nlm.nih.gov/${pmid}/`" target="_blank" rel="noopener noreferrer">{{ pmid }}</a>
      </span>
      <VChip
        v-if="capabilities.curation && !capabilities.edit && reviewStatus"
        size="x-small"
        variant="tonal"
        :color="REVIEW_TONES[reviewStatus]"
        class="status-chip fact-review"
      >
        {{ REVIEW_LABELS[reviewStatus] }}
      </VChip>
      <VChip
        v-if="capabilities.jobs"
        size="x-small"
        variant="tonal"
        :color="SYNC_TONES[detail.sync.status]"
        class="status-chip fact-sync"
      >
        {{ SYNC_LABELS[detail.sync.status] }}
      </VChip>
      <span v-if="problems.length" class="fact-problems">
        <VChip
          v-for="problem in problems"
          :key="problem.label"
          size="x-small"
          variant="tonal"
          :color="problem.tone"
          class="status-chip"
        >
          {{ problem.label }}
        </VChip>
      </span>
      <slot v-if="capabilities.edit" name="actions" />
    </div>
    <slot v-if="capabilities.edit" name="after" />
  </header>
</template>

<style scoped>
.study-header {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
/* One line where the parts fit, else they wrap onto more lines. The title gives way first, down
   to 8rem, before it wraps; the chips never shrink, so they keep their whole text. */
.study-header-line {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px 10px;
  min-height: 38px;
  /* 6 px above the first line, so that it stands as far below the app bar when the header wraps
     as when it is one line, and the focus ring of a chip (3 px at 3 px) is not hidden under the
     bar. */
  padding: 6px 0 4px;
}
.study-header-line > .v-chip {
  flex: none;
}
.study-identity {
  flex: 0 0 auto;
  max-width: 100%;
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  line-height: 1.3;
  overflow-wrap: anywhere;
}
/* The identity takes the focus when its page shows a study; it is no control, so it has no ring. */
.study-identity:focus {
  outline: none;
}
.header-chip {
  border-color: rgba(var(--v-theme-on-surface), 0.3);
}
/* The title and what the study is doing: the box gives way first, down to 8rem, before the line
   wraps, and keeps its width whatever it holds. In it the title gives way to the activity, down
   to 4rem. */
.study-title-box {
  display: flex;
  flex: 1 1 calc(8 * var(--study-rem, 1rem));
  align-items: baseline;
  gap: 6px;
  min-width: 0;
}
.study-title {
  flex: 0 1000 auto;
  min-width: min(calc(4 * var(--study-rem, 1rem)), 100%);
  margin: 0;
  overflow: hidden;
  font-size: 12.5px;
  line-height: 1.4;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.study-title-dot {
  flex: none;
  font-size: 12px;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
.fact-activity {
  flex: 0 1 auto;
  min-width: 0;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.study-title--missing {
  font-style: italic;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
.fact-pmid {
  display: inline-flex;
  flex: 0 0 auto;
  gap: 4px;
  font-size: 12px;
}
.fact-problems {
  display: inline-flex;
  flex: 0 0 auto;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px 6px;
}
.fact-name,
.fact-activity {
  font-size: 12px;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
</style>

<script setup lang="ts">
import { computed } from "vue";
import { useRouter } from "vue-router";
import { VAvatar, VBtn, VCheckboxBtn, VChip } from "vuetify/components";
import { formatTime, MODE_LABELS, REVIEW_LABELS, REVIEW_TONES, SYNC_LABELS, SYNC_TONES } from "../overview";
import { aiTitle, studyRoute, type RowItem } from "../studyTable";

/** One study of the study table of the overview. */
const props = defineProps<{
  item: RowItem;
  /** Whether the checkbox of the row is checked. */
  selected: boolean;
  /**
   * The position of the row for assistive technology, 2 for the first study after the header;
   * null for a hidden row that only sizes the columns (StudyTable.vue).
   */
  rowIndex: number | null;
}>();
const emit = defineEmits<{ toggle: []; retry: [] }>();

/** A sizer row: hidden, inert, without a checkbox, an identity or a place in the table. */
const sizer = computed(() => props.rowIndex === null);

const identity = computed(() => `${props.item.row.substance}/${props.item.row.name}`);

const router = useRouter();

/**
 * A click on a row opens its study, unless it hits a control of the row or the cell of its
 * checkbox, or ends a drag that selected text.
 */
function open(event: MouseEvent): void {
  if (props.item.row.duplicate) return;
  if (event.target instanceof Element && event.target.closest("a, button, input, label, .cell-select")) return;
  if (window.getSelection()?.toString()) return;
  void router.push(studyRoute(props.item.row));
}
</script>

<template>
  <tr
    :data-study="sizer || item.row.duplicate ? undefined : item.row.id"
    :aria-rowindex="rowIndex ?? undefined"
    :aria-hidden="sizer ? 'true' : undefined"
    :inert="sizer || undefined"
    :class="
      sizer ? 'study-sizer' : ['study-row', { 'study-row--link': !item.row.duplicate, 'study-row--selected': selected }]
    "
    @click="sizer || open($event)"
  >
    <td class="cell-select">
      <VCheckboxBtn
        v-if="!sizer"
        :model-value="selected"
        :disabled="item.row.duplicate"
        density="compact"
        :aria-label="`Select ${item.row.id}`"
        @update:model-value="emit('toggle')"
      />
    </td>
    <td class="cell-study">
      <div v-if="!sizer" class="study-row-line">
        <!-- The study keeps one line: the title after the identity is cut with an ellipsis first, the
             identity only when it alone is wider than its cell, as with a large font; the name of
             its link and the one tooltip of the table (StudyTable.vue), which also names the other
             substance folders that the tables of the study name, keep it whole. -->
        <span v-if="item.row.duplicate" class="study-identity" :data-tip="item.row.path">{{ identity }}</span>
        <RouterLink v-else :to="studyRoute(item.row)" class="study-identity" :data-tip="item.row.path">{{
          identity
        }}</RouterLink>
        <VChip
          v-if="item.row.duplicate"
          size="x-small"
          color="error"
          variant="tonal"
          class="status-chip"
          title="Two folders have this identity. Rename one of them."
        >
          Duplicate identity
        </VChip>
        <span v-if="item.row.duplicate" class="study-path" :title="item.row.path">{{ item.row.path }}</span>
        <span
          v-if="item.row.summary.title"
          class="study-row-title"
          :title="item.row.summary.title"
          >{{ item.row.summary.title }}</span
        >
        <span v-else class="study-row-title study-row-title--missing">No reference title yet</span>
      </div>
    </td>
    <td class="cell-review">
      <div class="cell-chips">
        <VChip
          v-if="item.row.summary.review_status"
          size="small"
          variant="tonal"
          :color="REVIEW_TONES[item.row.summary.review_status]"
          class="status-chip"
        >
          {{ REVIEW_LABELS[item.row.summary.review_status] }}
        </VChip>
        <span v-else class="cell-empty">-</span>
        <VChip v-if="item.row.summary.ai" size="small" variant="outlined" class="ai-marker" :title="aiTitle(item.row)">
          AI
        </VChip>
      </div>
    </td>
    <td class="cell-open">{{ item.row.summary.open_items ?? 0 }}</td>
    <td v-if="item.row.duplicate" class="cell-problems"><span class="cell-empty">-</span></td>
    <td v-else class="cell-problems">
      <div class="cell-chips">
        <VChip
          v-for="problem in item.problems"
          :key="problem.label"
          size="small"
          variant="tonal"
          :color="problem.tone"
          class="status-chip"
        >
          {{ problem.label }}
        </VChip>
        <span v-if="item.activity" class="cell-note" :title="item.activity">{{ item.activity }}</span>
        <span v-if="item.row.message" class="cell-message" :title="item.row.message">{{ item.row.message }}</span>
        <VBtn
          v-if="item.row.status === 'unknown'"
          size="x-small"
          variant="tonal"
          color="primary"
          prepend-icon="fas fa-triangle-exclamation"
          class="retry-button"
          :aria-label="`Review uncertain upload of ${item.row.id}`"
          @click="emit('retry')"
        >
          Review
        </VBtn>
      </div>
    </td>
    <td class="cell-sync">
      <VChip size="small" variant="tonal" :color="SYNC_TONES[item.row.sync.status]" class="status-chip">
        {{ SYNC_LABELS[item.row.sync.status] }}
      </VChip>
    </td>
    <td class="cell-release">
      <span v-if="item.row.summary.release" :title="`Released on ${item.row.summary.release.date}`">
        {{ item.row.summary.release.pkdb_id }}
      </span>
      <span v-else class="cell-empty">-</span>
    </td>
    <td class="cell-issue">
      <a
        v-if="item.issue"
        :href="item.issue.url"
        target="_blank"
        rel="noopener noreferrer"
        :aria-label="`GitHub issue #${item.issue.number}`"
      >
        #{{ item.issue.number }}
      </a>
      <span v-else class="cell-empty">-</span>
    </td>
    <td class="cell-curators">
      <div v-if="item.curators.length" class="curators">
        <VAvatar
          v-for="(person, index) in item.curators"
          :key="index"
          size="22"
          color="primary"
          variant="tonal"
          class="curator"
          :title="person.name"
        >
          <img v-if="person.avatar" :src="person.avatar" :alt="person.name" class="curator-photo" />
          <span v-else role="img" :aria-label="person.name" class="curator-initials">{{ person.initials }}</span>
        </VAvatar>
        <span v-if="item.hidden" role="img" class="curator-more" :aria-label="`And ${item.others}`" :title="item.others">
          +{{ item.hidden }}
        </span>
      </div>
      <span v-else class="cell-empty">-</span>
    </td>
    <td class="cell-mode">{{ MODE_LABELS[item.row.mode] }}</td>
    <td class="cell-upload">
      <a
        v-if="item.upload && item.row.last_upload"
        :href="item.upload"
        target="_blank"
        rel="noopener noreferrer"
        :title="`Open ${item.row.id} in PK-DB`"
      >
        {{ formatTime(item.row.last_upload.at) }}
      </a>
      <span v-else-if="item.row.last_upload">{{ formatTime(item.row.last_upload.at) }}</span>
      <span v-else class="cell-empty">-</span>
    </td>
  </tr>
</template>

<style scoped>
.study-row--link {
  cursor: pointer;
}
.study-row:hover {
  background: rgba(var(--v-theme-primary), 0.04);
}
.study-row.study-row--selected {
  background: rgba(var(--v-theme-primary), 0.08);
}
.v-chip {
  height: 20px;
}
td.cell-study {
  max-width: 0;
  overflow: hidden;
}
td.cell-open {
  text-align: end;
  font-variant-numeric: tabular-nums;
}
.study-row-line {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  height: 23px;
}
.study-identity {
  flex: 0 1 auto;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 600;
}
a.study-identity {
  text-decoration: none;
}
a.study-identity:hover {
  text-decoration: underline;
}
.study-path,
.study-row-title {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.8125rem;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
.study-row-title {
  flex: 1 1 0;
}
.study-path {
  flex: 0 1 auto;
}
.study-row-title--missing {
  font-style: italic;
}
.ai-marker {
  border-color: rgba(var(--v-theme-on-surface), 0.3);
}
.cell-chips {
  display: flex;
  align-items: center;
  gap: 4px;
  height: 23px;
}
/* The problems of a row stay on its line within a fixed measure, so that the table fits a window
   of 1280px: the chips and the button are never cut, while a long note or message is cut with an
   ellipsis. */
.cell-problems .cell-chips {
  flex-wrap: nowrap;
  max-width: 14rem;
}
.cell-problems .cell-chips > * {
  flex: none;
}
.cell-problems .cell-chips > .cell-note,
.cell-problems .cell-chips > .cell-message {
  flex: 0 1 auto;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 0.8125rem;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
.cell-release,
.cell-issue,
.cell-mode,
.cell-upload {
  line-height: 23px;
}
.cell-release,
.cell-upload {
  font-variant-numeric: tabular-nums;
}
.cell-empty {
  line-height: 23px;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
/* The avatars are taller than a line of the row; they center on the first line. */
.curators {
  display: flex;
  align-items: center;
}
/* Avatars overlap a little, each with a ring of the surface color. */
.curator {
  border: 1px solid rgb(var(--v-theme-surface));
  font-size: 0.6875rem;
  font-weight: 700;
}
.curator + .curator,
.curators .curator-more {
  margin-inline-start: -6px;
}
.curator-photo {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.curator-more {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 22px;
  height: 22px;
  padding: 0 4px;
  border: 1px solid rgb(var(--v-theme-surface));
  border-radius: 11px;
  background: rgba(var(--v-theme-on-surface), 0.08);
  font-size: 0.6875rem;
  font-weight: 700;
}
</style>

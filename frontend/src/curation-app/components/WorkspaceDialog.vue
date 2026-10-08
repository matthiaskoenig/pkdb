<script setup lang="ts">
import { computed, nextTick, ref, shallowRef, useId, watch } from "vue";
import {
  VAlert,
  VBtn,
  VCard,
  VCardActions,
  VCardItem,
  VCardText,
  VCardTitle,
  VChip,
  VDialog,
  VProgressLinear,
  VSpacer,
  VTextField,
} from "vuetify/components";
import type { Directories, FolderKind } from "../api/types";
import { useOverviewStore } from "../stores/overview";
import FolderPath from "./FolderPath.vue";
import RecentWorkspaces from "./RecentWorkspaces.vue";

const open = defineModel<boolean>({ default: false });

const overview = useOverviewStore();
const titleId = useId();
const pathId = useId();
const listing = shallowRef<Directories | null>(null);
const typed = ref("");
const loading = ref(false);
const busy = ref(false);
const error = ref<string | null>(null);
// Only the answer to the latest listing counts.
let request = 0;

/** The chips of the folders that are more than a folder: a repository and a study. */
const KIND_LABELS: Partial<Record<FolderKind, string>> = { repository: "Repository", study: "Study" };

function messageOf(caught: unknown): string {
  return caught instanceof Error ? caught.message : String(caught);
}

/** What the shown folder is: a repository, a study or a folder with subfolders. */
const summary = computed(() => {
  const shown = listing.value;
  if (shown === null) return "";
  if (shown.kind !== "folder") return `This folder is a ${shown.kind}.`;
  // An empty folder says so below the list.
  if (shown.entries.length === 0) return "";
  const count = `${shown.entries.length}${shown.truncated ? "+" : ""}`;
  return count === "1" ? "1 subfolder" : `${count} subfolders`;
});

/** Scroll the path field to the end of a long path, unless the curator is typing in it. */
function showPathEnd(): void {
  const input = document.getElementById(pathId);
  if (input instanceof HTMLInputElement && input !== document.activeElement) input.scrollLeft = input.scrollWidth;
}

/** List the folders of `path`, by default of the workspace; false when the server refused. */
async function browse(path?: string): Promise<boolean> {
  const current = ++request;
  loading.value = true;
  try {
    const result = path === undefined ? await overview.listDirectories() : await overview.listDirectories(path);
    if (current === request) {
      listing.value = result;
      typed.value = result.path;
      error.value = null;
      void nextTick(showPathEnd);
    }
    return true;
  } catch (caught) {
    if (current === request) error.value = messageOf(caught);
    return false;
  } finally {
    if (current === request) loading.value = false;
  }
}

/** Show the workspace, or the folder that the server offers when the workspace cannot be listed. */
async function start(): Promise<void> {
  listing.value = null;
  error.value = null;
  const workspace = overview.snapshot?.workspace ?? "";
  typed.value = workspace;
  if (workspace && (await browse(workspace))) return;
  const failure = error.value;
  if ((await browse()) && failure) error.value = failure;
}

function go(): void {
  const path = typed.value.trim();
  if (path) void browse(path);
}

async function run(action: () => Promise<unknown>, { close }: { close: boolean }): Promise<void> {
  busy.value = true;
  error.value = null;
  try {
    await action();
    if (close) open.value = false;
  } catch (caught) {
    error.value = messageOf(caught);
  } finally {
    busy.value = false;
  }
}

function select(path: string): Promise<void> {
  return run(() => overview.selectWorkspace(path), { close: true });
}

watch(
  open,
  (value) => {
    if (value) void start();
  },
  { immediate: true },
);
</script>

<template>
  <VDialog v-model="open" max-width="640" scrollable :aria-labelledby="titleId">
    <VCard class="workspace-dialog">
      <VCardItem>
        <VCardTitle :id="titleId" tag="h2">Choose workspace</VCardTitle>
      </VCardItem>
      <VCardText>
        <p class="dialog-intro">
          Browse to a repository, a substance folder or a study. The app does not change your source files.
        </p>
        <form class="folder-path" @submit.prevent="go">
          <VTextField
            :id="pathId"
            v-model="typed"
            label="Folder on this computer"
            placeholder="/path/to/pkdb_data"
            autocomplete="off"
            spellcheck="false"
            hide-details
          />
          <VBtn type="submit" variant="tonal" color="primary" :disabled="busy">Go</VBtn>
        </form>
        <div class="folder-nav">
          <VBtn
            variant="text"
            prepend-icon="fas fa-arrow-up"
            :disabled="busy || !listing?.parent"
            @click="listing?.parent && browse(listing.parent)"
          >
            Up
          </VBtn>
          <VBtn variant="text" prepend-icon="fas fa-house" :disabled="busy" @click="browse(listing?.home ?? '~')">
            Home
          </VBtn>
        </div>
        <VProgressLinear :active="loading" indeterminate color="primary" aria-label="Loading folders" />
        <VAlert v-if="error" type="error" variant="tonal" density="compact" class="status-alert">{{ error }}</VAlert>
        <template v-if="listing">
          <p class="folder-current">
            <FolderPath :path="listing.path" class="folder-current-path" />
            <span v-if="summary" class="folder-summary">{{ summary }}</span>
          </p>
          <ul class="folder-list" aria-label="Subfolders">
            <li v-for="entry in listing.entries" :key="entry.path" class="folder-row">
              <VBtn
                variant="text"
                prepend-icon="fas fa-folder"
                class="folder-browse"
                :title="entry.path"
                :disabled="busy"
                @click="browse(entry.path)"
              >
                <span class="folder-name">{{ entry.name }}</span>
              </VBtn>
              <VChip v-if="KIND_LABELS[entry.kind]" size="small" variant="tonal" class="folder-kind">
                {{ KIND_LABELS[entry.kind] }}
              </VChip>
              <VBtn
                variant="text"
                size="small"
                color="primary"
                :disabled="busy"
                :aria-label="`Open ${entry.name} as workspace`"
                @click="select(entry.path)"
              >
                Open
              </VBtn>
            </li>
          </ul>
          <p v-if="!listing.entries.length" class="panel-note">This folder has no subfolders.</p>
          <p v-if="listing.truncated" class="panel-note">More folders are not shown. Type a path to go there.</p>
        </template>
        <RecentWorkspaces
          v-if="overview.snapshot"
          :snapshot="overview.snapshot"
          :disabled="busy"
          @open="select"
          @remove="(path) => run(() => overview.forgetWorkspace(path), { close: false })"
        />
      </VCardText>
      <VCardActions class="dialog-actions">
        <VSpacer />
        <VBtn variant="text" @click="open = false">Cancel</VBtn>
        <VBtn
          variant="flat"
          color="primary"
          :disabled="!listing || loading"
          :loading="busy"
          @click="listing && select(listing.path)"
        >
          Open this folder
        </VBtn>
      </VCardActions>
    </VCard>
  </VDialog>
</template>

<style scoped>
.dialog-intro {
  margin: 0 0 16px;
}
.folder-path {
  display: flex;
  align-items: center;
  gap: 8px;
}
.folder-path .v-text-field {
  flex: 1 1 auto;
}
/* The icons of the text buttons line up with the field above. */
.folder-nav {
  display: flex;
  gap: 4px;
  margin: 8px 0 4px -16px;
}
/* The shown folder in caption size: its path, then what it holds. When the summary wraps
   below the path, its gap and weight keep it apart from the path. */
.folder-current {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px 16px;
  margin: 12px 0 8px;
  font-size: 0.8125rem;
  line-height: 1.4;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
.folder-summary {
  font-weight: 600;
  white-space: nowrap;
  color: rgba(var(--v-theme-on-surface), var(--v-high-emphasis-opacity));
}
.folder-list {
  max-height: 320px;
  margin: 0 0 8px;
  padding: 0;
  overflow-y: auto;
  list-style: none;
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
}
.folder-list:empty {
  display: none;
}
.folder-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 2px 8px 2px 4px;
}
.folder-row + .folder-row {
  border-top: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}
.folder-browse {
  flex: 1 1 auto;
  justify-content: flex-start;
  min-width: 0;
}
.folder-browse :deep(.v-btn__content) {
  min-width: 0;
}
.folder-name {
  overflow: hidden;
  text-overflow: ellipsis;
}
.folder-kind {
  flex-shrink: 0;
}
.recent-workspaces {
  margin-top: 16px;
}
</style>

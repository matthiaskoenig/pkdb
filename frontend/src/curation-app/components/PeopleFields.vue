<script setup lang="ts">
import { computed } from "vue";
import { VAutocomplete, VBtn, VCombobox, VListItem } from "vuetify/components";
import type { Profile } from "../api/types";
import { MARK_TEXT, type CuratorRow, type FieldMark } from "../metadata";
import PersonAvatar from "./PersonAvatar.vue";
import RatingStars from "./RatingStars.vue";

/** The creator, the curators with their ratings and the collaborators of study.json. */
const creator = defineModel<string>("creator", { required: true });
const curators = defineModel<CuratorRow[]>("curators", { required: true });
const collaborators = defineModel<string[]>("collaborators", { required: true });
const props = defineProps<{
  /** The profiles of the roster and of the people of the study, by user name. */
  profiles: ReadonlyMap<string, Profile>;
  /** The messages of a refused save, by field. */
  errors: ReadonlyMap<string, string[]>;
  /** The fields that changed on disk at the last reload. */
  marks: ReadonlyMap<string, FieldMark>;
}>();

interface Person {
  title: string;
  value: string;
  profile: Profile;
}

function profileOf(user: string): Profile {
  return (
    props.profiles.get(user) ?? { username: user, display_name: user, title: null, affiliation: null, avatar_url: null }
  );
}

/** The roster, and the people of the form who are not in it, so that the fields can show them. */
const people = computed<Person[]>(() => {
  const users = [...props.profiles.keys(), creator.value, ...curators.value.map((row) => row.user)];
  return [...new Set(users.filter(Boolean))].map((user) => {
    const profile = profileOf(user);
    return { title: profile.display_name, value: user, profile };
  });
});

const creatorProfile = computed(() => (creator.value ? profileOf(creator.value) : null));

function errorsAt(key: string): string[] {
  return props.errors.get(key) ?? [];
}

function markAt(key: string): string[] {
  const mark = props.marks.get(key);
  return mark ? [MARK_TEXT[mark]] : [];
}

function markColor(key: string): string | undefined {
  const mark = props.marks.get(key);
  return mark === "conflict" ? "warning" : mark ? "info" : undefined;
}

function userOf(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function setUser(index: number, value: unknown): void {
  curators.value = curators.value.map((row, position) => (position === index ? { ...row, user: userOf(value) } : row));
}

function setRating(index: number, rating: number): void {
  curators.value = curators.value.map((row, position) => (position === index ? { ...row, rating } : row));
}

function addCurator(): void {
  curators.value = [...curators.value, { user: "", rating: 0 }];
}

function removeCurator(index: number): void {
  curators.value = curators.value.filter((_, position) => position !== index);
}

function setCollaborators(value: unknown): void {
  collaborators.value = Array.isArray(value) ? value.map(userOf).filter(Boolean) : [];
}
</script>

<template>
  <div class="people-fields">
    <VAutocomplete
      :model-value="creator || null"
      :items="people"
      item-title="title"
      item-value="value"
      :filter-keys="['title', 'value']"
      label="Creator"
      hide-details="auto"
      :error-messages="errorsAt('creator')"
      :messages="markAt('creator')"
      :base-color="markColor('creator')"
      class="creator-field"
      @update:model-value="creator = userOf($event)"
    >
      <template v-if="creatorProfile" #prepend-inner>
        <PersonAvatar :profile="creatorProfile" :size="24" />
      </template>
      <template #item="{ props: item, item: person }">
        <VListItem v-bind="item" :subtitle="person.value" role="option">
          <template #prepend>
            <PersonAvatar :profile="person.profile" class="person-item-avatar" />
          </template>
        </VListItem>
      </template>
    </VAutocomplete>

    <div class="field-block curators-block" :class="{ [`field-block--${marks.get('curators')}`]: marks.has('curators') }">
      <h4 class="field-heading">Curators</h4>
      <p v-if="marks.has('curators')" class="field-mark">{{ markAt("curators")[0] }}</p>
      <div v-for="(row, index) in curators" :key="index" class="curator-row">
        <VAutocomplete
          :model-value="row.user || null"
          :items="people"
          item-title="title"
          item-value="value"
          :filter-keys="['title', 'value']"
          :label="`Curator ${index + 1}`"
          :error-messages="errorsAt(`curators.${index}.user`)"
          hide-details="auto"
          class="curator-user"
          @update:model-value="setUser(index, $event)"
        >
          <template v-if="row.user" #prepend-inner>
            <PersonAvatar :profile="profileOf(row.user)" :size="24" />
          </template>
          <template #item="{ props: item, item: person }">
            <VListItem v-bind="item" :subtitle="person.value" role="option">
              <template #prepend>
                <PersonAvatar :profile="person.profile" class="person-item-avatar" />
              </template>
            </VListItem>
          </template>
        </VAutocomplete>
        <RatingStars
          :model-value="row.rating"
          :label="`Rating of ${row.user || `curator ${index + 1}`}`"
          class="curator-rating"
          @update:model-value="setRating(index, $event)"
        />
        <VBtn
          icon="fas fa-xmark"
          variant="text"
          density="comfortable"
          size="small"
          :aria-label="`Remove curator ${index + 1}`"
          class="row-remove"
          @click="removeCurator(index)"
        />
        <p v-if="errorsAt(`curators.${index}.rating`).length" class="curator-messages field-error">
          {{ errorsAt(`curators.${index}.rating`).join(" ") }}
        </p>
      </div>
      <p v-if="!curators.length" class="field-empty">No curators</p>
      <p v-if="errorsAt('curators').length" class="field-error">{{ errorsAt("curators").join(" ") }}</p>
      <VBtn variant="text" color="primary" prepend-icon="fas fa-plus" class="row-add" @click="addCurator">
        Add curator
      </VBtn>
    </div>

    <VCombobox
      :model-value="collaborators"
      :items="people"
      item-title="title"
      item-value="value"
      :return-object="false"
      multiple
      chips
      closable-chips
      label="Collaborators"
      hide-details="auto"
      :error-messages="errorsAt('collaborators')"
      :messages="marks.has('collaborators') ? markAt('collaborators') : 'Names, or users of the roster'"
      :base-color="markColor('collaborators')"
      class="collaborators-field"
      @update:model-value="setCollaborators"
    />
  </div>
</template>

<style scoped>
.people-fields {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.curator-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto;
  align-items: center;
  gap: 4px 12px;
}
.curator-messages {
  grid-column: 1 / -1;
}
.person-item-avatar {
  margin-inline-end: 12px;
}
/* On a phone the rating goes below the curator, and the remove button stays beside the name. */
@media (max-width: 599.98px) {
  .curator-row {
    grid-template-columns: minmax(0, 1fr) auto;
  }
  .curator-rating {
    grid-row: 2;
    grid-column: 1;
  }
  .row-remove {
    grid-row: 1;
    grid-column: 2;
  }
}
</style>

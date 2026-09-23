<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { apiBase } from "./api/client";
import { useTheme } from "vuetify";
import { useSessionStore } from "./stores/session";
import { useSearchStore } from "./stores/search";
const session = useSessionStore(),
  search = useSearchStore(),
  theme = useTheme(),
  drawer = ref(false);
const avatarUrl = computed(() =>
  session.profile?.avatar_url ? apiBase + session.profile.avatar_url : "",
);
const resourceLinks = [
  {
    title: "Terms of use",
    href: "https://github.com/matthiaskoenig/pkdb/blob/develop/TERMS_OF_USE.md",
  },
  { title: "Contact", href: "mailto:koenigmx@hu-berlin.de" },
  { title: "REST API", href: `${apiBase}/docs` },
];
function toggleTheme() {
  const next = theme.global.name.value === "dark" ? "light" : "dark";
  theme.change(next);
  try {
    localStorage.setItem("pkdb.theme", next);
  } catch {
    /* Storage can be unavailable. */
  }
}
watch(
  () => session.epoch,
  () => search.invalidate(),
  { flush: "sync" },
);
onMounted(() => {
  try {
    if (localStorage.getItem("pkdb.theme") === "dark") theme.change("dark");
  } catch {
    /* Storage can be unavailable. */
  }
  void session.refreshProfile().catch(() => undefined);
});
</script>
<template>
  <v-app>
    <a class="skip-link" href="#main-content">Skip to main content</a>
    <v-app-bar elevation="0" class="app-header">
      <v-app-bar-nav-icon
        class="d-md-none"
        aria-label="Open navigation"
        @click="drawer = !drawer"
      /><RouterLink to="/" class="brand" aria-label="PK-DB home">
        <img
          class="brand-logo"
          src="/assets/images/pkdb_logo.png"
          alt="PK-DB"
          width="120"
          height="33"
        />
      </RouterLink><span class="brand-description d-none d-xl-inline"
        >Pharmacokinetics database</span
      ><v-spacer />
      <nav class="desktop-nav d-none d-md-flex" aria-label="Main navigation">
        <RouterLink to="/data">Explore data</RouterLink
        ><RouterLink to="/curation">Vocabulary</RouterLink
        ><a href="https://matthiaskoenig.github.io/pkdb">Documentation</a
        ><v-menu>
          <template #activator="{ props }">
            <v-btn
              v-bind="props"
              class="resource-menu"
              append-icon="fas fa-chevron-down"
            >About PK-DB</v-btn>
          </template>
          <v-list aria-label="About PK-DB resources">
            <v-list-item to="/" title="About PK-DB" />
            <v-list-item
              v-for="link in resourceLinks"
              :key="link.title"
              :href="link.href"
              :title="link.title"
            />
          </v-list>
        </v-menu><RouterLink to="/account" class="account-link">
          <img
            v-if="avatarUrl"
            :src="avatarUrl"
            class="account-avatar"
            alt=""
            width="32"
            height="32"
          />
          {{ session.profile?.username || "Account" }}
        </RouterLink>
      </nav>
      <v-btn
        icon="fas fa-circle-half-stroke"
        aria-label="Toggle color theme"
        @click="toggleTheme"
      />
    </v-app-bar>
    <v-navigation-drawer v-model="drawer" temporary>
      <nav
        class="mobile-nav"
        aria-label="Mobile navigation"
        :inert="!drawer"
        :aria-hidden="!drawer"
      >
        <RouterLink
          v-for="link in [
            { to: '/data', text: 'Explore data' },
            { to: '/curation', text: 'Vocabulary' },
          ]"
          :key="link.to"
          :to="link.to"
          @click="drawer = false"
        >
          {{ link.text }} </RouterLink
        ><a href="https://matthiaskoenig.github.io/pkdb">Documentation</a>
        <RouterLink to="/" @click="drawer = false">About PK-DB</RouterLink>
        <a
          v-for="link in resourceLinks"
          :key="link.title"
          :href="link.href"
          @click="drawer = false"
        >{{ link.title }}</a>
        <RouterLink to="/account" class="account-link" @click="drawer = false">
          <img
            v-if="avatarUrl"
            :src="avatarUrl"
            class="account-avatar"
            alt=""
            width="32"
            height="32"
          />
          {{ session.profile?.username || "Account" }}
        </RouterLink>
      </nav>
    </v-navigation-drawer>
    <v-main tag="div">
      <main id="main-content" tabindex="-1" class="main-content">
        <v-alert v-if="session.error" type="warning" class="mb-4">
          {{ session.error }}
          <v-btn @click="session.refreshProfile().catch(() => undefined)">
            Retry session
          </v-btn> </v-alert
        ><RouterView />
      </main>
      <footer class="app-footer">
        <div><strong>PK-DB</strong><span>Pharmacokinetics database</span></div>
        <p>Curated pharmacokinetic data for reproducible research.</p>
      </footer>
    </v-main>
  </v-app>
</template>

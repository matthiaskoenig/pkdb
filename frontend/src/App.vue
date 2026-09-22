<script setup lang="ts">
import { onMounted, ref, watch } from "vue";
import { apiBase } from "./api/client";
import { useTheme } from "vuetify";
import { useSessionStore } from "./stores/session";
import { useSearchStore } from "./stores/search";
const session = useSessionStore(),
  search = useSearchStore(),
  theme = useTheme(),
  drawer = ref(false);
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
        PK<span>-DB</span> </RouterLink
      ><span class="brand-description d-none d-lg-inline"
        >Pharmacokinetics database</span
      ><v-spacer />
      <nav class="desktop-nav d-none d-md-flex" aria-label="Main navigation">
        <RouterLink to="/data">Explore data</RouterLink
        ><RouterLink to="/curation">Vocabulary</RouterLink
        ><a href="https://matthiaskoenig.github.io/pkdb">Documentation</a
        ><RouterLink to="/account">
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
      <nav class="mobile-nav" aria-label="Mobile navigation">
        <RouterLink
          v-for="link in [
            { to: '/data', text: 'Explore data' },
            { to: '/curation', text: 'Vocabulary' },
            { to: '/account', text: 'Account' },
          ]"
          :key="link.to"
          :to="link.to"
          @click="drawer = false"
        >
          {{ link.text }} </RouterLink
        ><a href="https://matthiaskoenig.github.io/pkdb">Documentation</a>
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
        <RouterLink to="/">About PK-DB</RouterLink
        ><a
          href="https://github.com/matthiaskoenig/pkdb/blob/develop/TERMS_OF_USE.md"
          >Terms of use</a
        ><a href="mailto:koenigmx@hu-berlin.de">Contact</a
        ><a :href="`${apiBase}/docs`">REST API</a>
      </footer>
    </v-main>
  </v-app>
</template>

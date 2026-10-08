import { watch } from "vue";
import { useTheme } from "vuetify";
import type { ThemeChoice } from "../api/types";
import { useOverviewStore } from "../stores/overview";

/**
 * Where the browser keeps the theme that the curator chose in the header, until the state of the
 * local server is there. The server keeps the choice: the browser forgets it, as `pkdb curate`
 * starts on another port, and so another origin, every time.
 */
export const THEME_STORAGE_KEY = "pkdb.curation.theme";

/** The theme that this browser kept, or null without a choice or without storage. */
function storedChoice(): ThemeChoice | null {
  try {
    const value = localStorage.getItem(THEME_STORAGE_KEY);
    return value === "light" || value === "dark" ? value : null;
  } catch {
    // Storage can be unavailable, for example in a private window.
    return null;
  }
}

/** Keep `choice` in this browser, or forget it for the system theme; without storage it lasts until a reload. */
function store(choice: ThemeChoice): void {
  try {
    if (choice === "system") localStorage.removeItem(THEME_STORAGE_KEY);
    else localStorage.setItem(THEME_STORAGE_KEY, choice);
  } catch {
    // The choice then lasts until the page is reloaded.
  }
}

function systemTheme(): "light" | "dark" {
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

/** The light or dark theme: it follows the system until the curator switches it in the header. */
export function useColorTheme() {
  const theme = useTheme();
  const overview = useOverviewStore();

  function apply(choice: ThemeChoice): void {
    void theme.change(choice);
    store(choice);
  }

  /**
   * Apply the choice that this browser kept, then the one of the local server once its state is
   * there, and again whenever it changes there, such as from another tab.
   */
  function restore(): void {
    void theme.change(storedChoice() ?? "system");
    watch(
      () => overview.snapshot?.theme,
      (choice) => {
        if (choice) apply(choice);
      },
      { immediate: true },
    );
  }

  /**
   * Switch between light and dark. A choice other than the system theme is kept for the next
   * starts; switching back to the system theme follows the system again.
   */
  function toggle(): void {
    const next = theme.global.current.value.dark ? "light" : "dark";
    const choice: ThemeChoice = next === systemTheme() ? "system" : next;
    apply(choice);
    // The theme applies also when the local server cannot keep it, until the page is reloaded.
    overview.configure({ theme: choice }).catch(() => undefined);
  }

  return { restore, toggle };
}

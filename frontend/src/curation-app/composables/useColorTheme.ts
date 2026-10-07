import { useTheme } from "vuetify";

/** Where the browser keeps the theme that the curator chose in the header. */
export const THEME_STORAGE_KEY = "pkdb.curation.theme";

type Choice = "light" | "dark";

/** The theme that the curator chose, or null without a choice or without storage. */
function storedChoice(): Choice | null {
  try {
    const value = localStorage.getItem(THEME_STORAGE_KEY);
    return value === "light" || value === "dark" ? value : null;
  } catch {
    // Storage can be unavailable, for example in a private window.
    return null;
  }
}

/** Keep `choice`, or forget the choice when it is null; without storage it lasts until a reload. */
function store(choice: Choice | null): void {
  try {
    if (choice === null) localStorage.removeItem(THEME_STORAGE_KEY);
    else localStorage.setItem(THEME_STORAGE_KEY, choice);
  } catch {
    // The choice then lasts until the page is reloaded.
  }
}

function systemTheme(): Choice {
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

/** The light or dark theme: it follows the system until the curator switches it in the header. */
export function useColorTheme() {
  const theme = useTheme();

  /** Apply the stored choice, or follow the system without one. */
  function restore(): void {
    void theme.change(storedChoice() ?? "system");
  }

  /**
   * Switch between light and dark. A choice other than the system theme is kept for the next
   * visits; switching back to the system theme follows the system again.
   */
  function toggle(): void {
    const next: Choice = theme.global.current.value.dark ? "light" : "dark";
    const followSystem = next === systemTheme();
    void theme.change(followSystem ? "system" : next);
    store(followSystem ? null : next);
  }

  return { restore, toggle };
}

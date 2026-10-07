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

/** The light or dark theme: it follows the system until the curator switches it in the header. */
export function useColorTheme() {
  const theme = useTheme();

  /** Apply the stored choice, or follow the system without one. */
  function restore(): void {
    void theme.change(storedChoice() ?? "system");
  }

  /** Switch between light and dark and keep the choice for the next visits. */
  function toggle(): void {
    const next: Choice = theme.global.current.value.dark ? "light" : "dark";
    void theme.change(next);
    try {
      localStorage.setItem(THEME_STORAGE_KEY, next);
    } catch {
      // The choice then lasts until the page is reloaded.
    }
  }

  return { restore, toggle };
}

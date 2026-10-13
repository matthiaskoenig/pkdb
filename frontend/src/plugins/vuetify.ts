import "vuetify/styles";
import "@fortawesome/fontawesome-free/css/fontawesome.css";
import "@fortawesome/fontawesome-free/css/solid.css";
import "@fortawesome/fontawesome-free/css/regular.css";
import { createVuetify } from "vuetify";
import {
  VAlert,
  VApp,
  VAppBar,
  VAppBarNavIcon,
  VAutocomplete,
  VAvatar,
  VBtn,
  VCard,
  VCardActions,
  VCardText,
  VCardTitle,
  VCheckbox,
  VChip,
  VCol,
  VCombobox,
  VContainer,
  VDialog,
  VDivider,
  VExpansionPanel,
  VExpansionPanelText,
  VExpansionPanels,
  VFileInput,
  VForm,
  VList,
  VListItem,
  VListItemSubtitle,
  VListItemTitle,
  VMain,
  VMenu,
  VNavigationDrawer,
  VProgressLinear,
  VRadio,
  VRadioGroup,
  VRow,
  VSelect,
  VSpacer,
  VSwitch,
  VTab,
  VTable,
  VTabs,
  VTextField,
  VTextarea,
  VWindow,
  VWindowItem,
} from "vuetify/components";
import { Ripple } from "vuetify/directives";
import { aliases, fa } from "vuetify/iconsets/fa";
/** The component defaults of the website. */
const WEBSITE_DEFAULTS: Record<string, Record<string, unknown>> = {
  VBtn: { rounded: "lg", variant: "flat" },
  VTextField: { variant: "outlined", density: "compact" },
  VAutocomplete: { variant: "outlined", density: "compact" },
  VCombobox: { variant: "outlined", density: "compact" },
  VSelect: { variant: "outlined", density: "compact" },
  VCard: { rounded: "lg", elevation: 0 },
};

/** The website defaults with the given ones merged over them per component. */
function mergeDefaults(extra: Readonly<Record<string, Readonly<Record<string, unknown>>>>) {
  const merged: Record<string, Record<string, unknown>> = { ...WEBSITE_DEFAULTS };
  for (const [name, values] of Object.entries(extra)) {
    merged[name] = { ...WEBSITE_DEFAULTS[name], ...values };
  }
  return merged;
}

/** Colors and theme variables that an app adds to a theme of the website. */
export interface ThemeExtension {
  colors: Readonly<Record<string, string>>;
  variables: Readonly<Record<string, string>>;
}

/**
 * The website theme; `cspNonce` lets a page with a strict CSP keep Vuetify's runtime styles, and
 * `defaultTheme` sets the theme of the first paint (light by default); `themes` adds colors and
 * variables to its light and dark theme.
 */
export function makeVuetify(
  options: { cspNonce?: string | undefined; defaultTheme?: "light" | "dark" | "system";
    /** Component defaults merged per component over those of the website. */
    defaults?: Readonly<Record<string, Readonly<Record<string, unknown>>>>;
    /** Colors and variables added to the light and the dark theme, such as those of the curation app. */
    themes?: Readonly<Record<"light" | "dark", ThemeExtension>>;
  } = {},
) {
  return createVuetify({
    components: {
      VAlert,
      VApp,
      VAppBar,
      VAppBarNavIcon,
      VAutocomplete,
      VAvatar,
      VBtn,
      VCard,
      VCardActions,
      VCardText,
      VCardTitle,
      VCheckbox,
      VChip,
      VCol,
      VCombobox,
      VContainer,
      VDialog,
      VDivider,
      VExpansionPanel,
      VExpansionPanelText,
      VExpansionPanels,
      VFileInput,
      VForm,
      VList,
      VListItem,
      VListItemSubtitle,
      VListItemTitle,
      VMain,
      VMenu,
      VNavigationDrawer,
      VProgressLinear,
      VRadio,
      VRadioGroup,
      VRow,
      VSelect,
      VSpacer,
      VSwitch,
      VTab,
      VTable,
      VTabs,
      VTextField,
      VTextarea,
      VWindow,
      VWindowItem,
    },
    directives: { Ripple },
    icons: { defaultSet: "fa", aliases, sets: { fa } },
    theme: {
      // exactOptionalPropertyTypes: Vuetify accepts no explicit undefined.
      ...(options.cspNonce ? { cspNonce: options.cspNonce } : {}),
      defaultTheme: options.defaultTheme ?? "light",
      themes: {
        light: {
          colors: {
            primary: "#176b70",
            secondary: "#52676a",
            background: "#f5f7f7",
            surface: "#ffffff",
            error: "#b3261e",
            ...options.themes?.light.colors,
          },
          variables: { ...options.themes?.light.variables },
        },
        dark: {
          colors: {
            primary: "#79d5d6",
            background: "#101e23",
            surface: "#192b31",
            // Vuetify's default (#cf6679) has 4.1:1 on the surface; field errors are text.
            error: "#f28b82",
            // Text on the error color, such as a flat error alert: 5.5:1; Vuetify picks white, 2.4:1.
            "on-error": "#601410",
            // The thumb of switches; Vuetify's default is lavender.
            "surface-bright": "#dcefef",
            ...options.themes?.dark.colors,
          },
          variables: { ...options.themes?.dark.variables },
        },
      },
    },
    defaults: mergeDefaults(options.defaults ?? {}),
  });
}

/** The curation app is a dense working surface: compact controls everywhere, the website keeps its sizes. */
export const COMPACT_DEFAULTS = {
  VBtn: { size: "small" },
  VChip: { size: "small" },
  VTabs: { density: "compact" },
  VAlert: { density: "compact" },
  VList: { density: "compact" },
  VListItem: { density: "compact" },
  VSwitch: { density: "compact", hideDetails: true },
  VCheckbox: { density: "compact", hideDetails: "auto" },
  VTextField: { density: "compact" },
  VSelect: { density: "compact" },
  VAutocomplete: { density: "compact" },
  VCombobox: { density: "compact" },
  VTextarea: { density: "compact" },
} as const;

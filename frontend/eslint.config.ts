import js from "@eslint/js";
import vue from "eslint-plugin-vue";
import ts from "typescript-eslint";
export default ts.config(
  {
    ignores: [
      "dist/**",
      "node_modules/**",
      "test-results/**",
      "playwright-report/**",
    ],
  },
  js.configs.recommended,
  ...ts.configs.recommended,
  ...vue.configs["flat/recommended"],
  {
    files: ["**/*.vue"],
    languageOptions: {
      parserOptions: { parser: ts.parser, extraFileExtensions: [".vue"] },
    },
  },
  {
    rules: {
      "vue/multi-word-component-names": "off",
      "vue/max-attributes-per-line": "off",
      "vue/html-self-closing": "off",
      "vue/singleline-html-element-content-newline": "off",
      "vue/multiline-html-element-content-newline": "off",
      "vue/html-indent": "off",
      "vue/html-closing-bracket-newline": "off",
      "vue/attributes-order": "off",
      "no-undef": "off",
      "@typescript-eslint/no-explicit-any": "error",
    },
  },
  {
    // The study views (src/study-views) and the website never import the curation app (#963);
    // the curation app imports both. scripts/check-source.ts also refuses import() and import types.
    files: ["src/**/*.ts", "src/**/*.vue"],
    ignores: ["src/curation-app/**"],
    rules: {
      "no-restricted-imports": [
        "error",
        {
          patterns: [
            {
              regex: "(^|/)curation-app(/|$)",
              message: "Only src/curation-app imports the curation app: the study views and the website get what they need through useStudyViews() (#963).",
            },
          ],
        },
      ],
    },
  },
);

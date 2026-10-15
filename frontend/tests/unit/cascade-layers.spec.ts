import { readdirSync, readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import type { HtmlTagDescriptor } from "vite";
import { describe, expect, it } from "vitest";
import website from "../../vite.config";
import curation from "../../vite.curation.config";
import { CASCADE_LAYERS, cascadeLayers, layerOrder } from "../../scripts/cascade-layers";

// frontend/; Vite would rewrite a literal `new URL("../..", import.meta.url)` into a dev server address.
const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");

/** The files below `folder` whose name ends with one of `endings`. */
function files(folder: string, endings: string[]): string[] {
  return readdirSync(folder, { recursive: true, encoding: "utf8" })
    .filter((name) => endings.some((ending) => name.endsWith(ending)))
    .map((name) => join(folder, name));
}

/** The full names of the cascade layers of a stylesheet, nested ones as `a.b`, in the order in which it first names them. */
function layersOf(css: string): string[] {
  const names: string[] = [];
  const open: (string | null)[] = [];
  const name = (own: string) => [...open.filter((part) => part !== null), own].join(".");
  for (const [token, list, end] of css.matchAll(/@layer\s+([^;{]+)([;{])|[{}]/g)) {
    if (list === undefined) {
      if (token === "{") open.push(null);
      else open.pop();
      continue;
    }
    const own = list.split(",").map((part) => part.trim());
    for (const part of own) names.push(name(part));
    if (end === "{") open.push(own[0]!);
  }
  return [...new Set(names.flatMap((full) => full.split(".").map((_, index, parts) => parts.slice(0, index + 1).join("."))))];
}

function pluginNames(plugins: unknown[] | undefined): string[] {
  return (plugins ?? []).flat().flatMap((plugin) =>
    typeof plugin === "object" && plugin !== null && "name" in plugin && typeof plugin.name === "string" ? [plugin.name] : [],
  );
}

describe("the order of the cascade layers", () => {
  const declared = layersOf(layerOrder);

  it("is Vuetify's order, with every layer of Vuetify's stylesheets", () => {
    const vuetify = join(root, "node_modules/vuetify/lib");
    expect(declared.filter((name) => name.startsWith("vuetify-"))).toEqual(layersOf(readFileSync(join(vuetify, "styles/main.css"), "utf8")));
    for (const path of files(vuetify, [".css"])) expect(declared, path).toEqual(expect.arrayContaining(layersOf(readFileSync(path, "utf8"))));
  });

  it("names every layer of the frontend after Vuetify's", () => {
    const own = files(join(root, "src"), [".css", ".vue"]).flatMap((path) =>
      [...readFileSync(path, "utf8").matchAll(/@layer\s+([^;{]+)/g)].flatMap(([, list]) => list!.split(",").map((part) => part.trim())),
    );
    expect(own.length).toBeGreaterThan(0);
    expect(declared).toEqual(expect.arrayContaining(own));
    expect(CASCADE_LAYERS.at(-1)).toBe("website-study-views");
  });

  it("stands at the top of the head of both builds, before any stylesheet", async () => {
    const config = await website({ command: "build", mode: "production" });
    expect(pluginNames(config.plugins)).toContain("pkdb-cascade-layers");
    expect(pluginNames(curation.plugins)).toContain("pkdb-cascade-layers");
    const transform = cascadeLayers().transformIndexHtml as () => HtmlTagDescriptor[];
    expect(transform()).toEqual([{ tag: "style", children: layerOrder, injectTo: "head-prepend" }]);
    expect(layerOrder).toBe(`@layer ${CASCADE_LAYERS.join(", ")};`);
  });
});

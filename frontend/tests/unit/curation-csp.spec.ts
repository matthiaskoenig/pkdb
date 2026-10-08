import { createApp } from "vue";
import { beforeEach, describe, expect, it } from "vitest";
import { cspNonce } from "../../src/curation-app/csp";
import { makeVuetify } from "../../src/plugins/vuetify";

/** Installs Vuetify in an app and returns the theme stylesheet it created. */
function themeStylesheet(options?: Parameters<typeof makeVuetify>[0]) {
  createApp({ render: () => null }).use(makeVuetify(options));
  return document.getElementById("vuetify-theme-stylesheet");
}

// Vuetify reuses an existing theme stylesheet, so each test starts with an empty head.
beforeEach(() => {
  document.head.replaceChildren();
});

describe("cspNonce", () => {
  it("reads the nonce of the csp-nonce meta tag", () => {
    const meta = document.createElement("meta");
    meta.setAttribute("property", "csp-nonce");
    meta.nonce = "abc123";
    document.head.append(meta);
    expect(cspNonce()).toBe("abc123");
  });

  it("is undefined without the meta tag", () => {
    expect(cspNonce()).toBeUndefined();
  });
});

describe("makeVuetify", () => {
  it("puts the CSP nonce on the theme stylesheet it creates", () => {
    expect(themeStylesheet({ cspNonce: "n" })?.nonce).toBe("n");
  });

  it("uses the nonce of the csp-nonce meta tag", () => {
    const meta = document.createElement("meta");
    meta.setAttribute("property", "csp-nonce");
    meta.setAttribute("nonce", "from-the-server");
    document.head.append(meta);
    expect(themeStylesheet({ cspNonce: cspNonce() })?.nonce).toBe("from-the-server");
  });

  it("leaves the theme stylesheet without a nonce by default", () => {
    expect(themeStylesheet()?.hasAttribute("nonce")).toBe(false);
  });
});

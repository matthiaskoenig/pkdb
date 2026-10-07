import { describe, expect, it } from "vitest";
import { cspNonce } from "../../src/curation-app/csp";

describe("cspNonce", () => {
  it("reads the nonce of the csp-nonce meta tag", () => {
    const meta = document.createElement("meta");
    meta.setAttribute("property", "csp-nonce");
    meta.nonce = "abc123";
    document.head.append(meta);
    expect(cspNonce()).toBe("abc123");
    meta.remove();
  });

  it("is undefined without the meta tag", () => {
    expect(cspNonce()).toBeUndefined();
  });
});

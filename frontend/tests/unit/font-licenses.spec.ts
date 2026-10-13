import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { fontLicenseFiles } from "../../scripts/font-licenses";

describe("the licenses of the bundled fonts", () => {
  it("go beside the fonts of the build, with the text of the SIL Open Font License", () => {
    const files = fontLicenseFiles();
    expect([...files.keys()]).toEqual(["assets/Inter-LICENSE.txt", "assets/fontawesome-free-LICENSE.txt"]);
    for (const source of files.values()) expect(readFileSync(source, "utf8")).toContain("SIL OPEN FONT LICENSE");
    expect(readFileSync(files.get("assets/Inter-LICENSE.txt")!, "utf8")).toContain("The Inter Project Authors");
  });
});

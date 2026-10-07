import { rmSync } from "node:fs";
import { ROOT_VARIABLE } from "./paths.ts";

/** Remove the temporary folder of the run; the spec files stopped their servers already. */
export default function globalTeardown(): void {
  const root = process.env[ROOT_VARIABLE];
  if (root) rmSync(root, { recursive: true, force: true });
}

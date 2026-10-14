/** Why the curation app cannot upload, from the state of the local server. */
import type { Snapshot } from "./api/types";

/** Why uploads are not possible, or null when they are. */
export function uploadBlocker(snapshot: Snapshot): string | null {
  if (snapshot.can_upload) return null;
  if (snapshot.offline) return "Work offline is on. Turn it off in the settings to upload.";
  if (!snapshot.authenticated) return "Add your personal API key in the settings to upload.";
  if (snapshot.connection !== "connected") return "The PK-DB server is not connected.";
  return "Your PK-DB account cannot upload studies.";
}

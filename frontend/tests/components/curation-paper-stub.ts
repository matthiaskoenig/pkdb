import { defineComponent, h, onMounted, type PropType } from "vue";
import type { PaperPlace } from "../../src/curation-app/paper";

/** How often a test mounted the viewer of the paper; a test resets it. */
export const paperViewer = { mounts: 0 };

/**
 * The viewer of the paper, which PDF.js draws: it shows its PDF and the page of its place, and
 * Go to page 3 reports a place, as the viewer does with `v-model:place` when the curator scrolls.
 */
export const PaperViewerStub = defineComponent({
  name: "PaperViewer",
  props: {
    url: { type: String, required: true },
    file: { type: String, required: true },
    bytes: { type: Number as PropType<number | null>, default: null },
    place: { type: Object as PropType<PaperPlace | null>, default: null },
  },
  emits: ["update:place"],
  setup(props, { emit }) {
    onMounted(() => (paperViewer.mounts += 1));
    return () =>
      h("div", { class: "paper-viewer-stub", "data-url": props.url, "data-page": props.place?.page }, [
        h(
          "button",
          { type: "button", onClick: () => emit("update:place", { url: props.url, page: 3, fit: null, scale: 1.25 }) },
          "Go to page 3",
        ),
      ]);
  },
});

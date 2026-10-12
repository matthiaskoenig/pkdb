import { beforeEach, describe, expect, it, vi } from "vitest";
import * as pdfjs from "pdfjs-dist";
import type { PaperEvents, PaperStart } from "../../src/curation-app/paper";
import { openPaper } from "../../src/curation-app/paperEngine";

/** A fake PDF.js: it records what the engine creates, asks and dispatches. */
const fake = vi.hoisted(() => {
  type Listener = (data: Record<string, unknown>) => void;
  const state: {
    bus: EventBus | null;
    viewer: PDFViewer | null;
    worker: PDFWorker | null;
    options: Record<string, unknown> | null;
    task: { promise: Promise<{ numPages: number }>; destroy: () => Promise<void> };
  } = {
    bus: null,
    viewer: null,
    worker: null,
    options: null,
    task: { promise: Promise.resolve({ numPages: 3 }), destroy: async () => undefined },
  };
  class PDFWorker {
    destroyed = 0;
    constructor() {
      state.worker = this;
    }
    destroy(): void {
      this.destroyed += 1;
    }
  }
  class EventBus {
    readonly listeners = new Map<string, Listener[]>();
    readonly dispatched: [string, Record<string, unknown>][] = [];
    constructor() {
      state.bus = this;
    }
    on(name: string, listener: Listener): void {
      this.listeners.set(name, [...(this.listeners.get(name) ?? []), listener]);
    }
    dispatch(name: string, data: Record<string, unknown>): void {
      this.dispatched.push([name, data]);
      for (const listener of this.listeners.get(name) ?? []) listener(data);
    }
  }
  class PDFViewer {
    #scaleValue = "auto";
    /** The scale values that the engine set, in their order. */
    readonly scaleValues: string[] = [];
    updates = 0;
    currentPageNumber = 1;
    readonly pagesCount = 3;
    readonly options: Record<string, unknown>;
    readonly documents: unknown[] = [];
    readonly steps: number[] = [];
    constructor(options: Record<string, unknown>) {
      this.options = options;
      state.viewer = this;
    }
    setDocument(document: unknown): void {
      this.documents.push(document);
    }
    increaseScale(): void {
      this.steps.push(1);
    }
    decreaseScale(): void {
      this.steps.push(-1);
    }
    get currentScaleValue(): string {
      return this.#scaleValue;
    }
    set currentScaleValue(value: string) {
      this.scaleValues.push(value);
      this.#scaleValue = value;
    }
    update(): void {
      this.updates += 1;
    }
  }
  class PDFLinkService {
    readonly options: Record<string, unknown>;
    readonly documents: unknown[] = [];
    constructor(options: Record<string, unknown>) {
      this.options = options;
    }
    setViewer(): void {}
    setDocument(document: unknown): void {
      this.documents.push(document);
    }
  }
  class PDFFindController {
    readonly options: Record<string, unknown>;
    constructor(options: Record<string, unknown>) {
      this.options = options;
    }
  }
  return { state, EventBus, PDFViewer, PDFLinkService, PDFFindController, PDFWorker };
});

vi.mock("pdfjs-dist", () => ({
  GlobalWorkerOptions: { workerSrc: "" },
  AnnotationMode: { ENABLE: 1 },
  AnnotationEditorType: { DISABLE: -1 },
  PDFWorker: fake.PDFWorker,
  getDocument: (options: Record<string, unknown>) => {
    fake.state.options = options;
    return fake.state.task;
  },
}));
vi.mock("pdfjs-dist/web/pdf_viewer.mjs", () => ({
  EventBus: fake.EventBus,
  PDFViewer: fake.PDFViewer,
  PDFLinkService: fake.PDFLinkService,
  PDFFindController: fake.PDFFindController,
  LinkTarget: { BLANK: 2 },
  FindState: { FOUND: 0, NOT_FOUND: 1, WRAPPED: 2, PENDING: 3 },
}));

const BASE = new URL("pdfjs/", document.baseURI).href;
const URL_A = "/local/studies/caffeine/Example/files/Example.pdf";
const START: PaperStart = { page: 1, fit: "page-width", scale: 1 };

function events() {
  return { opened: vi.fn(), page: vi.fn(), scale: vi.fn(), found: vi.fn() } satisfies PaperEvents;
}

/** The signal of an opening that nothing aborts. */
function signal(): AbortSignal {
  return new AbortController().signal;
}

/** A promise with its resolve and reject. */
function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((done, fail) => {
    resolve = done;
    reject = fail;
  });
  return { promise, resolve, reject };
}

/** A scroll container of the viewer as a layout makes it: its size, which is none while it is hidden. */
interface Pane extends HTMLDivElement {
  resize(width: number, height: number): void;
}

/** The scroll container of the viewer with its empty `div.pdfViewer`, 600 x 800 px. */
function container(width = 600, height = 800): Pane {
  const element = document.createElement("div") as Pane;
  element.append(document.createElement("div"));
  let size = [width, height] as const;
  Object.defineProperty(element, "clientWidth", { get: () => size[0] });
  Object.defineProperty(element, "clientHeight", { get: () => size[1] });
  element.resize = (newWidth, newHeight) => {
    size = [newWidth, newHeight];
  };
  return element;
}

/** The callbacks of the resize observers of the test, which a test calls as a layout would. */
let observers: ResizeObserverCallback[] = [];
/** The animation frames that wait; `frames()` runs them. */
let waiting: FrameRequestCallback[] = [];

function frames(): void {
  const due = waiting;
  waiting = [];
  for (const callback of due) callback(0);
}

/** A change of the size of the pane: the observers report it, and the next frame comes. */
function resized(pane: Pane, width: number, height: number): void {
  pane.resize(width, height);
  for (const callback of observers) callback([], {} as ResizeObserver);
  frames();
}

beforeEach(() => {
  observers = [];
  waiting = [];
  vi.stubGlobal(
    "ResizeObserver",
    class {
      constructor(callback: ResizeObserverCallback) {
        observers.push(callback);
      }
      observe() {}
      unobserve() {}
      disconnect() {}
    },
  );
  vi.stubGlobal("requestAnimationFrame", (callback: FrameRequestCallback) => waiting.push(callback));
  vi.stubGlobal("cancelAnimationFrame", () => undefined);
  fake.state.bus = null;
  fake.state.viewer = null;
  fake.state.worker = null;
  fake.state.options = null;
  fake.state.task = { promise: Promise.resolve({ numPages: 3 }), destroy: vi.fn(async () => undefined) };
});

describe("the PDF.js engine of the paper viewer", () => {
  it("loads the worker of PDF.js from pdfjs/ beside the app", () => {
    expect(pdfjs.GlobalWorkerOptions.workerSrc).toBe(`${BASE}pdf.worker.min.mjs`);
  });

  it("opens a PDF in ranges with the options that the Content Security Policy of the local server allows", async () => {
    await openPaper(container(), URL_A, events(), START, signal());
    expect(fake.state.options).toEqual({
      url: URL_A,
      worker: fake.state.worker,
      cMapUrl: `${BASE}cmaps/`,
      cMapPacked: true,
      standardFontDataUrl: `${BASE}standard_fonts/`,
      wasmUrl: `${BASE}wasm/`,
      useWasm: false,
      disableAutoFetch: true,
      disableStream: true,
      enableXfa: false,
    });
    expect(fake.state.viewer!.options).toMatchObject({ annotationMode: 1, annotationEditorMode: -1 });
    expect(fake.state.viewer!.options).not.toHaveProperty("scriptingManager");
    expect(fake.state.viewer!.documents).toEqual([{ numPages: 3 }]);
  });

  it("starts on the page and the fit of the viewer and reports the page, the zoom and the finds", async () => {
    const reported = events();
    await openPaper(container(), URL_A, reported, { page: 2, fit: "page-fit", scale: 1 }, signal());
    const bus = fake.state.bus!;
    const viewer = fake.state.viewer!;
    expect(reported.opened).toHaveBeenCalledWith(3);
    bus.dispatch("pagesinit", {});
    expect([viewer.currentScaleValue, viewer.currentPageNumber]).toEqual(["page-fit", 2]);
    expect(reported.page).toHaveBeenLastCalledWith(2);
    bus.dispatch("pagechanging", { pageNumber: 3 });
    expect(reported.page).toHaveBeenLastCalledWith(3);
    viewer.currentScaleValue = "1.1";
    bus.dispatch("scalechanging", { scale: 1.1 });
    expect(reported.scale).toHaveBeenLastCalledWith(1.1, null);
    viewer.currentScaleValue = "page-width";
    bus.dispatch("scalechanging", { scale: 0.9 });
    expect(reported.scale).toHaveBeenLastCalledWith(0.9, "page-width");
    bus.dispatch("updatefindcontrolstate", { state: 0, matchesCount: { current: 0, total: 0 } });
    expect(reported.found).toHaveBeenLastCalledWith({ status: "pending", current: 0, total: 0 });
    bus.dispatch("updatefindmatchescount", { matchesCount: { current: 1, total: 3 } });
    expect(reported.found).toHaveBeenLastCalledWith({ status: "found", current: 1, total: 3 });
    bus.dispatch("updatefindcontrolstate", { state: 1, matchesCount: { current: 0, total: 0 } });
    expect(reported.found).toHaveBeenLastCalledWith({ status: "missing", current: 0, total: 0 });
  });

  it("refits the pages when the pane changes its size", async () => {
    const pane = container();
    await openPaper(pane, URL_A, events(), START, signal());
    const viewer = fake.state.viewer!;
    fake.state.bus!.dispatch("pagesinit", {});
    resized(pane, 500, 800);
    expect(viewer.scaleValues).toEqual(["page-width", "page-width"]);
    expect(viewer.updates).toBe(1);
  });

  it("waits with the fit and the first page until the pane, hidden while the PDF opened, shows", async () => {
    const pane = container(0, 0);
    const reported = events();
    await openPaper(pane, URL_A, reported, { page: 2, fit: "page-width", scale: 1 }, signal());
    const viewer = fake.state.viewer!;
    fake.state.bus!.dispatch("pagesinit", {});
    expect(viewer.scaleValues).toEqual([]);
    expect(viewer.currentPageNumber).toBe(1);
    expect(reported.page).not.toHaveBeenCalled();
    resized(pane, 600, 800);
    expect(viewer.scaleValues).toEqual(["page-width"]);
    expect(viewer.currentPageNumber).toBe(2);
    expect(reported.page).toHaveBeenLastCalledWith(2);
  });

  it("keeps the pages where they were while the pane is hidden, without fitting them to no size", async () => {
    const pane = container();
    await openPaper(pane, URL_A, events(), START, signal());
    const viewer = fake.state.viewer!;
    fake.state.bus!.dispatch("pagesinit", {});
    pane.scrollTop = 1500;
    pane.dispatchEvent(new Event("scroll"));
    // Hidden, the pane has no size and the browser forgets how far it was scrolled.
    pane.scrollTop = 0;
    resized(pane, 0, 0);
    pane.dispatchEvent(new Event("scroll"));
    expect(viewer.scaleValues).toEqual(["page-width"]);
    expect(viewer.updates).toBe(0);
    resized(pane, 600, 800);
    expect(pane.scrollTop).toBe(1500);
    expect(viewer.scaleValues).toEqual(["page-width", "page-width"]);
    expect(viewer.updates).toBe(1);
  });

  it("starts at the scale of zoom steps without a fit", async () => {
    await openPaper(container(), URL_A, events(), { page: 1, fit: null, scale: 1.25 }, signal());
    fake.state.bus!.dispatch("pagesinit", {});
    expect(fake.state.viewer!.currentScaleValue).toBe("1.25");
  });

  it("goes to pages, zooms, fits, finds, and ends a find", async () => {
    const session = await openPaper(container(), URL_A, events(), START, signal());
    const viewer = fake.state.viewer!;
    session.goTo(3);
    expect(viewer.currentPageNumber).toBe(3);
    session.zoom(1);
    session.zoom(-1);
    expect(viewer.steps).toEqual([1, -1]);
    session.fit("1");
    expect(viewer.currentScaleValue).toBe("1");
    session.find("the", { again: false, previous: false });
    session.find("the", { again: true, previous: true });
    session.find("", { again: false, previous: false });
    const dispatched = fake.state.bus!.dispatched;
    expect(dispatched.map(([name, data]) => [name, data.type, data.query, data.findPrevious])).toEqual([
      ["find", "", "the", false],
      ["find", "again", "the", true],
      ["findbarclose", undefined, undefined, undefined],
    ]);
    expect(dispatched[0]![1]).toMatchObject({ caseSensitive: false, entireWord: false, highlightAll: true, matchDiacritics: false });
  });

  it("reports a new find as running at once, also while PDF.js still counts the matches of the last one", async () => {
    const reported = events();
    const session = await openPaper(container(), URL_A, reported, START, signal());
    const bus = fake.state.bus!;
    bus.dispatch("updatefindmatchescount", { matchesCount: { current: 3, total: 12 } });
    expect(reported.found).toHaveBeenLastCalledWith({ status: "found", current: 3, total: 12 });
    session.find("then", { again: false, previous: false });
    expect(reported.found).toHaveBeenLastCalledWith({ status: "pending", current: 0, total: 0 });
    // PDF.js reports a pending find with the counts of the match that it selected last.
    bus.dispatch("updatefindcontrolstate", { state: 3, matchesCount: { current: 3, total: 12 } });
    expect(reported.found).toHaveBeenLastCalledWith({ status: "pending", current: 0, total: 0 });
    bus.dispatch("updatefindmatchescount", { matchesCount: { current: 1, total: 4 } });
    expect(reported.found).toHaveBeenLastCalledWith({ status: "found", current: 1, total: 4 });
    // The next match keeps the count until PDF.js reports the next one.
    const calls = reported.found.mock.calls.length;
    session.find("then", { again: true, previous: false });
    expect(reported.found).toHaveBeenCalledTimes(calls);
  });

  it("gives its signal to the viewer of PDF.js, which drops its listeners of the pane when it aborts", async () => {
    const controller = new AbortController();
    await openPaper(container(), URL_A, events(), START, controller.signal);
    expect(fake.state.viewer!.options.abortSignal).toBe(controller.signal);
  });

  it("stops the loading of a PDF that its viewer aborts: the worker goes, and the viewer never gets the PDF", async () => {
    const load = deferred<{ numPages: number }>();
    fake.state.task = { promise: load.promise, destroy: vi.fn(async () => undefined) };
    const controller = new AbortController();
    const reported = events();
    const opening = openPaper(container(), URL_A, reported, START, controller.signal);
    controller.abort();
    await expect(opening).rejects.toMatchObject({ name: "AbortError" });
    expect(fake.state.task.destroy).toHaveBeenCalledTimes(1);
    expect(fake.state.worker!.destroyed).toBe(1);
    load.resolve({ numPages: 3 });
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(fake.state.viewer!.documents).toEqual([]);
    expect(reported.opened).not.toHaveBeenCalled();
  });

  it("leaves a PDF that opened to its session: an abort does not destroy it, its close does", async () => {
    const controller = new AbortController();
    const session = await openPaper(container(), URL_A, events(), START, controller.signal);
    controller.abort();
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(fake.state.task.destroy).not.toHaveBeenCalled();
    await session.close();
    expect(fake.state.task.destroy).toHaveBeenCalledTimes(1);
    expect(fake.state.worker!.destroyed).toBe(1);
  });

  it("does not show a PDF that loads just as its viewer aborts", async () => {
    const load = deferred<{ numPages: number }>();
    fake.state.task = { promise: load.promise, destroy: vi.fn(async () => undefined) };
    const controller = new AbortController();
    const opening = openPaper(container(), URL_A, events(), START, controller.signal);
    load.resolve({ numPages: 3 });
    controller.abort();
    await expect(opening).rejects.toMatchObject({ name: "AbortError" });
    expect(fake.state.viewer!.documents).toEqual([]);
    expect(fake.state.task.destroy).toHaveBeenCalledTimes(1);
  });

  it("opens nothing for an opening that was aborted before it started", async () => {
    const controller = new AbortController();
    controller.abort();
    await expect(openPaper(container(), URL_A, events(), START, controller.signal)).rejects.toMatchObject({
      name: "AbortError",
    });
    expect(fake.state.options).toBeNull();
  });

  it("does not report a cancelled request of PDF.js that nothing handled, but any other rejection", () => {
    const rejected = (reason: unknown) =>
      Object.assign(new Event("unhandledrejection", { cancelable: true }), { reason });
    const aborted = rejected(new DOMException("signal is aborted without reason", "AbortError"));
    window.dispatchEvent(aborted);
    expect(aborted.defaultPrevented).toBe(true);
    const failed = rejected(new TypeError("Failed to fetch"));
    window.dispatchEvent(failed);
    expect(failed.defaultPrevented).toBe(false);
  });

  it("closes the PDF and its worker, and the PDF leaves the container at once", async () => {
    const session = await openPaper(container(), URL_A, events(), START, signal());
    const closing = session.close();
    expect(fake.state.viewer!.documents.at(-1)).toBeNull();
    await closing;
    expect(fake.state.task.destroy).toHaveBeenCalledTimes(1);
    expect(fake.state.worker!.destroyed).toBe(1);
  });

  it("ends the worker of a PDF whose task does not finish destroying after 2 s", async () => {
    vi.useFakeTimers();
    try {
      fake.state.task.destroy = vi.fn(() => new Promise<void>(() => undefined));
      const session = await openPaper(container(), URL_A, events(), START, signal());
      let closed = false;
      void session.close().then(() => (closed = true));
      await vi.advanceTimersByTimeAsync(1999);
      expect([closed, fake.state.worker!.destroyed]).toEqual([false, 0]);
      await vi.advanceTimersByTimeAsync(1);
      expect([closed, fake.state.worker!.destroyed]).toEqual([true, 1]);
    } finally {
      vi.useRealTimers();
    }
  });

  it("ends the loading of a PDF that PDF.js cannot open, with its error", async () => {
    const error = Object.assign(new Error("Invalid PDF structure."), { name: "InvalidPDFException" });
    fake.state.task = { promise: Promise.reject(error), destroy: vi.fn(async () => undefined) };
    await expect(openPaper(container(), URL_A, events(), START, signal())).rejects.toBe(error);
    expect(fake.state.task.destroy).toHaveBeenCalledTimes(1);
  });
});

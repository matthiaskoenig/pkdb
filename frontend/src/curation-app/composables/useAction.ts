import { computed, ref, type ComputedRef, type Ref } from "vue";
import { isNoUser } from "../api/client";
import { actionFailure, messageOf, userHint, type ActionFailure } from "../study";

export interface Action<A extends string> {
  /** The running action. */
  busy: Readonly<Ref<A | null>>;
  /** Whether an action runs, or something else that `waits` names; another action waits meanwhile. */
  working: ComputedRef<boolean>;
  /** The failure of the last action; it stays until it is dismissed or the next action starts. */
  failure: Ref<ActionFailure | null>;
  /** What to do when the last action was a write refused without a user, for `UserHint`. */
  userText: Ref<string | null>;
  /**
   * Run `work` unless an action runs already, and announce the text that it returns. A failure
   * becomes `failure` through `explain`; a write refused without a user becomes `userText`.
   */
  run(action: A, work: () => Promise<string | void>, explain?: (caught: unknown) => ActionFailure): Promise<void>;
}

/**
 * One action at a time, so that feedback and revisions never mix: the actions of a section or
 * the study header. `announce` shows the notice of an action that succeeded (`useNotice`), and
 * `waits` tells whether something else runs that the actions wait for, such as a dialog that
 * writes.
 */
export function useAction<A extends string>(announce: (text: string) => void, waits?: () => boolean): Action<A> {
  // Vue cannot unwrap a generic type parameter, which is a string anyway.
  const busy = ref<A | null>(null) as Ref<A | null>;
  const working = computed(() => busy.value !== null || (waits?.() ?? false));
  const failure = ref<ActionFailure | null>(null);
  const userText = ref<string | null>(null);

  async function run(
    action: A,
    work: () => Promise<string | void>,
    explain: (caught: unknown) => ActionFailure = (caught) => actionFailure(messageOf(caught)),
  ): Promise<void> {
    if (working.value) return;
    busy.value = action;
    failure.value = null;
    userText.value = null;
    announce("");
    try {
      announce((await work()) ?? "");
    } catch (caught) {
      if (isNoUser(caught)) userText.value = userHint(caught);
      else failure.value = explain(caught);
    } finally {
      busy.value = null;
    }
  }

  return { busy, working, failure, userText, run };
}

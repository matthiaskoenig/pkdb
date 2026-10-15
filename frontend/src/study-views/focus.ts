/** An element to focus, found when it is needed; nothing when there is none. */
export type FocusTarget = () => HTMLElement | null | undefined;

/** The attribute of the heading of the section of a study page, which the page sets on it. */
export const SECTION_HEADING = "data-study-section-heading";

/**
 * The heading of the section of the study page, which takes the focus after a dialog of a section
 * when the control that opened it is gone.
 */
export const sectionHeading: FocusTarget = () => document.querySelector<HTMLElement>(`[${SECTION_HEADING}]`);

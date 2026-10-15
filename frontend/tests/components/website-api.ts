import { AxiosError, AxiosHeaders, type AxiosResponse } from "axios";
import type { Mock } from "vitest";

/** An axios error that carries the answer of the server, as the API client rejects a failed read. */
export function httpError(status: number, data: unknown = { detail: "Not found" }): AxiosError {
  const config = { headers: new AxiosHeaders() };
  const response: AxiosResponse = { status, statusText: String(status), data, headers: {}, config };
  return new AxiosError(`Request failed with status code ${status}`, "ERR_BAD_REQUEST", config, null, response);
}

/**
 * Lets the mocked `get` of the API client answer GET requests from `answers`, by their URL: an
 * Error by throwing it, any other value as the data of the answer; a URL without an answer is a
 * 404. The answers are read at each request, so a test may change them between reads.
 */
export function serve(get: Mock, answers: Record<string, unknown>): void {
  get.mockImplementation(async (url: string) => {
    const answer = answers[url];
    if (answer === undefined) throw httpError(404, { detail: "Not found" });
    if (answer instanceof Error) throw answer;
    return { data: answer };
  });
}

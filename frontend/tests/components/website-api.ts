import { AxiosError, AxiosHeaders, type AxiosResponse } from "axios";

/** An axios error that carries the answer of the server, as the API client rejects a failed read. */
export function httpError(status: number, data: unknown = { detail: "Not found" }): AxiosError {
  const config = { headers: new AxiosHeaders() };
  const response: AxiosResponse = { status, statusText: String(status), data, headers: {}, config };
  return new AxiosError(`Request failed with status code ${status}`, "ERR_BAD_REQUEST", config, null, response);
}

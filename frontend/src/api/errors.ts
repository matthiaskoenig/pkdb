import axios from "axios";
export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
export function errorStatus(error: unknown): number | undefined {
  return axios.isAxiosError(error) ? error.response?.status : undefined;
}
export function errorMessage(error: unknown): string {
  if (error instanceof RangeError) return error.message;
  const data: unknown = axios.isAxiosError(error)
    ? error.response?.data
    : undefined;
  if (isRecord(data)) {
    if (typeof data.detail === "string") return data.detail;
    if (Array.isArray(data.detail)) {
      const messages = data.detail
        .filter(isRecord)
        .map((item) => item.msg)
        .filter((item): item is string => typeof item === "string");
      if (messages.length) return messages.join("; ");
    }
    const messages = Object.values(data).flatMap((value) =>
      Array.isArray(value)
        ? value.filter((item): item is string => typeof item === "string")
        : [],
    );
    if (messages.length) return messages.join("; ");
  }
  if (errorStatus(error) === 401) return "Sign in to continue.";
  if (errorStatus(error) === 403)
    return "You do not have permission to perform this action. Confirm your identity if required.";
  if (errorStatus(error) === 404)
    return "The requested resource was not found.";
  return "The request could not be completed. Please try again.";
}

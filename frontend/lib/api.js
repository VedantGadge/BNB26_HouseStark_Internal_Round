import { getCreatorAccessToken } from "./auth";

export const apiBaseUrl =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(message, status, detail) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

export async function apiFetch(path, init = {}) {
  const token = await getCreatorAccessToken();
  const response = await fetch(`${apiBaseUrl}/v1${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init.headers,
    },
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail = Array.isArray(body.detail)
      ? body.detail.map((item) => item.msg).join("; ")
      : body.detail;
    throw new ApiError(
      typeof detail === "string"
        ? detail
        : `API request failed (${response.status})`,
      response.status,
      body.detail,
    );
  }

  if (response.status === 204) return null;
  return response.json();
}

const pendingOperations = new Map();

export async function post(path, body, queued = false) {
  const payload = JSON.stringify(body);
  if (!queued) return apiFetch(path, { method: "POST", body: payload });
  const digest = await crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(path + payload),
  );
  const operation =
    "creatorai-operation:" +
    Array.from(new Uint8Array(digest), (v) =>
      v.toString(16).padStart(2, "0"),
    ).join("");
  let key = pendingOperations.get(operation) || crypto.randomUUID();
  pendingOperations.set(operation, key);
  try {
    key = sessionStorage.getItem(operation) || key;
    sessionStorage.setItem(operation, key);
  } catch {
    /* Memory-only submission still carries a nonce. */
  }
  try {
    const result = await apiFetch(path, {
      method: "POST",
      body: payload,
      headers: { "Idempotency-Key": key },
    });
    pendingOperations.delete(operation);
    try {
      sessionStorage.removeItem(operation);
    } catch {
      /* Request is already durable server-side. */
    }
    return result;
  } catch (error) {
    if (error.status >= 400 && error.status < 500) {
      pendingOperations.delete(operation);
      try {
        sessionStorage.removeItem(operation);
      } catch {}
    }
    throw error;
  }
}

export function patch(path, body) {
  return apiFetch(path, { method: "PATCH", body: JSON.stringify(body) });
}

export function put(path, body) {
  return apiFetch(path, { method: "PUT", body: JSON.stringify(body) });
}

export async function optionalFetch(path) {
  try {
    return await apiFetch(path);
  } catch (error) {
    if (error.status === 404) return null;
    throw error;
  }
}

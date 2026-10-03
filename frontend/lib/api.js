import { getCreatorAccessToken } from "./auth";

export const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

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
    throw new Error(detail || `API request failed (${response.status})`);
  }

  return response.json();
}

export function post(path, body, queued = false) {
  return apiFetch(path, { method: "POST", body: JSON.stringify(body),
    headers: queued ? { "Idempotency-Key": crypto.randomUUID() } : {} });
}

export function patch(path, body) {
  return apiFetch(path, { method: "PATCH", body: JSON.stringify(body) });
}

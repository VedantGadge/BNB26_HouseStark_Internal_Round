/**
 * Auth is intentionally provider-neutral until the project selects one.
 * Keep token acquisition in this module; API clients should never infer ownership from route IDs.
 */
export async function getCreatorAccessToken() {
  return typeof window === "undefined" ? null : sessionStorage.getItem("creatorai-token");
}

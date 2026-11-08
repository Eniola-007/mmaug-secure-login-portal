import type { AccountInfo } from "@azure/msal-browser";
import { loginRequest, msalInstance } from "./auth";

const apiBase = import.meta.env.VITE_API_BASE_URL ?? "";

export async function apiRequest<T>(
  path: string,
  account: AccountInfo | null,
  devUser: string,
  init?: RequestInit,
): Promise<T> {
  const headers = new Headers(init?.headers);
  headers.set("Content-Type", "application/json");
  headers.set("X-Correlation-ID", crypto.randomUUID());

  if (account) {
    const token = await msalInstance.acquireTokenSilent({ ...loginRequest, account });
    headers.set("Authorization", `Bearer ${token.accessToken}`);
  } else if (devUser) {
    headers.set("X-Dev-User", devUser);
  }

  const response = await fetch(`${apiBase}${path}`, { ...init, headers });
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(body?.detail ?? `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

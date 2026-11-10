import type { AccountInfo } from "@azure/msal-browser";
import { loginRequest, msalInstance } from "./auth";

const apiBase = import.meta.env.VITE_API_BASE_URL ?? "";

export async function apiRequest<T>(
  path: string,
  account: AccountInfo | null,
  devUser: string,
  localToken: string,
  init?: RequestInit,
): Promise<T> {
  const headers = new Headers(init?.headers);
  headers.set("Content-Type", "application/json");
  headers.set("X-Correlation-ID", crypto.randomUUID());

  if (account) {
    const token = await msalInstance.acquireTokenSilent({ ...loginRequest, account });
    headers.set("Authorization", `Bearer ${token.accessToken}`);
  } else if (localToken) {
    headers.set("Authorization", `Bearer ${localToken}`);
  } else if (devUser) {
    headers.set("X-Dev-User", devUser);
  }

  const response = await fetch(`${apiBase}${path}`, { ...init, headers });
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as {
      detail?: string | Array<{ msg?: string }> | {
        message?: string;
        tenant_id?: string;
        object_id?: string;
      };
    } | null;
    if (body?.detail && typeof body.detail === "object") {
      if (Array.isArray(body.detail)) {
        throw new Error(body.detail.map((item) => item.msg).filter(Boolean).join(". ") || `Request failed (${response.status})`);
      }
      const reference = body.detail.tenant_id && body.detail.object_id
        ? ` Enrollment reference: ${body.detail.tenant_id}:${body.detail.object_id}`
        : "";
      throw new Error(`${body.detail.message ?? `Request failed (${response.status})`}${reference}`);
    }
    throw new Error(
      typeof body?.detail === "string" ? body.detail : `Request failed (${response.status})`,
    );
  }
  return response.json() as Promise<T>;
}

export async function publicApiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  return apiRequest<T>(path, null, "", "", init);
}

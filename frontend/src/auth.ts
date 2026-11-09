import {
  BrowserCacheLocation,
  PublicClientApplication,
  type Configuration,
} from "@azure/msal-browser";

const authorityTenant = import.meta.env.VITE_ENTRA_AUTHORITY_TENANT ?? "common";
const spaClientId = import.meta.env.VITE_ENTRA_SPA_CLIENT_ID ?? "";
const apiClientId = import.meta.env.VITE_ENTRA_API_CLIENT_ID ?? "";

const configuration: Configuration = {
  auth: {
    clientId: spaClientId || "00000000-0000-0000-0000-000000000000",
    authority: `https://login.microsoftonline.com/${authorityTenant}`,
    redirectUri: window.location.origin,
    postLogoutRedirectUri: window.location.origin,
  },
  cache: {
    cacheLocation: BrowserCacheLocation.SessionStorage,
  },
};

export const msalInstance = new PublicClientApplication(configuration);
export const loginRequest = {
  scopes: [`api://${apiClientId}/access_as_user`],
};
export const devAuthEnabled = import.meta.env.VITE_DEV_AUTH === "true";

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { MsalProvider } from "@azure/msal-react";
import App from "./App";
import { msalInstance } from "./auth";
import "./styles.css";

async function start() {
  await msalInstance.initialize();
  await msalInstance.handleRedirectPromise();
  createRoot(document.getElementById("root")!).render(
    <StrictMode>
      <MsalProvider instance={msalInstance}>
        <App />
      </MsalProvider>
    </StrictMode>,
  );
}

void start();

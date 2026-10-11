import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "@voyara/i18n"; // initialise langue + dir (utilisé par les composants partagés)
import "./index.css";
import App from "./App";
import { Providers } from "./app/providers";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Providers>
      <App />
    </Providers>
  </StrictMode>,
);

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./app/App";
import "./styles/globals.css";
import "./styles/app.css";
import "./styles/aurora-glass.css";
import "./styles/dashboard-cockpit.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);

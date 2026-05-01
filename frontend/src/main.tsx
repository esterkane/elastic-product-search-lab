import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { SearchPage } from "./pages/SearchPage";
import "./styles.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <SearchPage />
  </StrictMode>
);

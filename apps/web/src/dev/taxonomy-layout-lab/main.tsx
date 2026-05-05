// abstract: Browser entrypoint for the standalone taxonomy layout tuning page.
// out_of_scope: Production app routing and backend layout solving.

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import "../../index.css";
import { TaxonomyLayoutLabApp } from "./TaxonomyLayoutLabApp";

const rootElement = document.getElementById("root");

if (!rootElement) {
  throw new Error("Layout lab root element was not found.");
}

createRoot(rootElement).render(
  <StrictMode>
    <TaxonomyLayoutLabApp />
  </StrictMode>,
);

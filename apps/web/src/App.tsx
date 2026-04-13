// abstract: Root app entry that mounts the shared router-backed web application.
// out_of_scope: Feature-level data fetching and rendering engine internals.

import { RouterProvider } from "@tanstack/react-router";
import { useState } from "react";

import { createAppRouter } from "./app/router";

export function App() {
  const [router] = useState(createAppRouter);

  return <RouterProvider router={router} />;
}

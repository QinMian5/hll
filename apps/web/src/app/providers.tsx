// abstract: Application-wide React providers for the web client shell.
// out_of_scope: Feature-specific page composition and backend transport logic.

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { type PropsWithChildren, useState } from "react";

import { AuthCoordinatorProvider } from "./auth/AuthCoordinatorProvider";

function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        refetchOnWindowFocus: false,
        retry: false,
        staleTime: 30_000,
      },
    },
  });
}

export function AppProviders({ children }: PropsWithChildren) {
  const [queryClient] = useState(createQueryClient);

  return (
    <QueryClientProvider client={queryClient}>
      <AuthCoordinatorProvider>{children}</AuthCoordinatorProvider>
    </QueryClientProvider>
  );
}

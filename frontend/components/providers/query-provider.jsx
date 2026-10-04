"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";

export function QueryProvider({ children }) {
  const [queryClient] = useState(() => new QueryClient({defaultOptions:{queries:{staleTime:15000,retry:(attempt,error)=>attempt<1 && !(error.status>=400 && error.status<500)}}}));

  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}

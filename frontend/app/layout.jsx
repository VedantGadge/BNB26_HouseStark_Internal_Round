import "./globals.css";

import { QueryProvider } from "@/components/providers/query-provider";

export const metadata = {
  title: "CreatorAI",
  description: "Creator workspace for source footage, clips, exports, and insights.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <QueryProvider>{children}</QueryProvider>
      </body>
    </html>
  );
}

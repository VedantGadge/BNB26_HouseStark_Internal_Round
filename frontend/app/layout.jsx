import "./globals.css";
import localFont from "next/font/local";
import { cookies } from "next/headers";

import { QueryProvider } from "@/components/providers/query-provider";

export const metadata = {
  title: { default: "CreatorAI | Your connected creator studio", template: "%s | CreatorAI" },
  description: "Creator workspace for source footage, clips, exports, and insights.",
};

const geist = localFont({ src: "../node_modules/@fontsource-variable/geist/files/geist-latin-wght-normal.woff2", variable: "--font-geist", display: "swap" });
const devanagari = localFont({ src: "../node_modules/@fontsource-variable/noto-sans-devanagari/files/noto-sans-devanagari-devanagari-wght-normal.woff2", variable: "--font-devanagari", display: "swap", preload: false });
const contract = {
  THESIS: "One source becomes simultaneous formats; media is the proof, not invented analytics.",
  OWN_WORLD: "White, cool silver, ink Geist, violet pills and softly inset media trays.",
  STORY: "Understand the connected workflow, enter the studio, keep original and saved versions intact.",
  FIRST_VIEWPORT: "Centered two-line 68px headline, centered copy and action, then wide portrait/landscape/square multiview.",
  FORM: "Broadcast multiview monitor, position 3, seed 499df743.",
  FINISH: "unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, and DESIGN.md",
};

export default async function RootLayout({ children }) {
  const theme = (await cookies()).get("creatorai-theme")?.value === "dark" ? "dark" : "light";
  return (
    <html lang="en" data-theme={theme} className={`${geist.variable} ${devanagari.variable}`}>
      <body>
        <script id="design-contract" type="application/json" dangerouslySetInnerHTML={{ __html: JSON.stringify(contract) }} />
        <a className="skip-link" href="#main-content">Skip to content</a>
        <QueryProvider>{children}</QueryProvider>
      </body>
    </html>
  );
}

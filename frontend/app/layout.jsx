import "./globals.css";
import localFont from "next/font/local";
import { cookies } from "next/headers";

import { QueryProvider } from "@/components/providers/query-provider";

export const metadata = {
  title: {
    default: "CreatorAI | Your connected creator studio",
    template: "%s | CreatorAI",
  },
  description:
    "Creator workspace for source footage, clips, exports, and insights.",
};

const outfit = localFont({
  src: "../node_modules/@fontsource-variable/outfit/files/outfit-latin-wght-normal.woff2",
  variable: "--font-outfit",
  display: "swap",
});
const devanagari = localFont({
  src: "../node_modules/@fontsource-variable/noto-sans-devanagari/files/noto-sans-devanagari-devanagari-wght-normal.woff2",
  variable: "--font-devanagari",
  display: "swap",
  preload: false,
});
const contract = {
  THESIS:
    "A connected creator workflow shown through an editable product demonstration, not invented analytics.",
  OWN_WORLD:
    "Instagram-inspired white, ink Outfit, coral selections, monochrome primary actions, dark media and composed working panels. No violet.",
  STORY:
    "Understand the connected workflow, enter the studio, keep original and saved versions intact.",
  FIRST_VIEWPORT:
    "Centered two-line 68px headline, two centered actions, then full-width dark source/editor/caption demonstration.",
  FORM: "Landing Cinematic Center, seed 66; studio production board position 3, seed 26ff84ab. User-pinned Instagram-inspired monochrome/coral replaces violet.",
  STUDIO: {
    THESIS:
      "Each project has a visible place in the workflow, not an unstructured list.",
    FIRST_VIEWPORT:
      "224px sidebar, slim breadcrumb topbar, 32px title and New project action, workflow strip, filters and three stage lanes.",
    APPROVED_COMP: ".impeccable/mocks/studio-social-1.png",
  },
  FINISH:
    "unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, and DESIGN.md",
};

export default async function RootLayout({ children }) {
  const theme =
    (await cookies()).get("creatorai-theme")?.value === "dark"
      ? "dark"
      : "light";
  return (
    <html
      lang="en"
      data-theme={theme}
      className={`${outfit.variable} ${devanagari.variable}`}
    >
      <body>
        <script
          id="design-contract"
          type="application/json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(contract) }}
        />
        <a className="skip-link" href="#main-content">
          Skip to content
        </a>
        <QueryProvider>{children}</QueryProvider>
      </body>
    </html>
  );
}

const { test, expect } = require("@playwright/test");
const AxeBuilder = require("@axe-core/playwright").default;

test("landing is readable, accessible, responsive and theme-aware", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "One workspace. From idea to publish-ready.",
  );
  await expect(
    page.getByRole("button", { name: "Play video", exact: true }),
  ).toBeVisible();
  await page.evaluate(() => document.fonts.ready);
  const geometry = await page.locator("h1").evaluate((heading) => ({
    lines:
      heading.clientHeight / parseFloat(getComputedStyle(heading).lineHeight),
    overflow: document.documentElement.scrollWidth > innerWidth,
  }));
  expect(geometry.lines).toBeLessThanOrEqual(3.1);
  expect(geometry.overflow).toBe(false);
  expect(
    (await new AxeBuilder({ page }).include(".landing").analyze()).violations,
  ).toEqual([]);
  await page.getByRole("button", { name: "Use dark theme" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.evaluate(async () => {
    await Promise.all(
      document
        .getAnimations()
        .map((animation) => animation.finished.catch(() => {})),
    );
  });
  expect(
    (await new AxeBuilder({ page }).include(".landing").analyze()).violations,
  ).toEqual([]);
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
});

test("illustrative editor controls, framing, accordion and carousel work", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .getByRole("textbox", { name: "Caption text", exact: true })
    .fill("An original story, in my own words.");
  await page
    .getByRole("button", { name: "Save demo version", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Demo version saved" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Export", exact: true }).click();
  await page
    .getByRole("combobox", { name: "Platform preset", exact: true })
    .selectOption("youtube_video");
  await expect(page.locator(".preset-dimensions")).toHaveText("1920 × 1080");
  await page.getByRole("button", { name: "Script", exact: true }).click();
  const hooks = page.locator(".demo-hook-options button");
  await hooks.nth(1).click();
  await expect(hooks.nth(1)).toHaveAttribute("aria-pressed", "true");
  await page.getByRole("button", { name: "Shape", exact: true }).click();
  await expect(page.locator("#workflow-panel-2")).toBeVisible();
  await page.getByRole("button", { name: "Next editing example" }).click();
  await expect(page.locator(".carousel-position")).toHaveText("Example 2 of 3");
  await page.getByRole("button", { name: "Previous editing example" }).click();
  await expect(page.locator(".carousel-position")).toHaveText("Example 1 of 3");
});

test("reduced motion keeps all meaningful content visible", async ({
  page,
}) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  await expect(page.locator(".reveal-word").first()).toHaveCSS("opacity", "1");
  await page.getByRole("link", { name: "Explore the workflow" }).click();
  await expect(page.locator("#workflow")).toBeInViewport();
});

const projectId = process.env.CREATORAI_E2E_PROJECT_ID;
test.describe("connected isolated QA studio", () => {
  test.skip(
    !projectId,
    "Set CREATORAI_E2E_PROJECT_ID to an isolated QA project; never use a real creator project for mutation tests.",
  );
  for (const feature of [
    "",
    "script",
    "assets",
    "clips",
    "publish",
    "insights",
  ]) {
    test(`${feature || "overview"} is accessible and has no horizontal overflow`, async ({
      page,
    }) => {
      await page.goto(`/projects/${projectId}/${feature}`);
      await expect(page.locator(".workspace h1")).toBeVisible();
      await expect(page.locator(".status-loading")).toHaveCount(0);
      await expect(page.locator(".workspace [role=alert]")).toHaveCount(0);
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth > innerWidth,
        ),
      ).toBe(false);
      expect(
        (await new AxeBuilder({ page }).include(".studio-shell").analyze())
          .violations,
      ).toEqual([]);
    });
  }
  test("script draft survives a reload and recording view manages focus", async ({
    page,
  }) => {
    await page.goto(`/projects/${projectId}/script`);
    await page.getByRole("button", { name: "Edit", exact: true }).click();
    const hook = page.getByRole("textbox", { name: "Hook 1", exact: true });
    await expect(hook).toBeVisible();
    const original = await hook.inputValue();
    await hook.fill("[QA unsaved] Preserve my local editing buffer.");
    page.on("dialog", (dialog) => dialog.accept());
    await page.reload();
    await page.getByRole("button", { name: "Edit", exact: true }).click();
    await expect(hook).toHaveValue(
      "[QA unsaved] Preserve my local editing buffer.",
    );
    await page
      .getByRole("button", { name: "Load latest / revert draft" })
      .click();
    await expect(hook).toHaveValue(original);
    await page.getByRole("button", { name: "Read", exact: true }).click();
    await page
      .getByRole("button", { name: "Recording read", exact: true })
      .click();
    await expect(page.getByRole("dialog")).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(page.getByRole("dialog")).toHaveCount(0);
    await expect(
      page.getByRole("button", { name: "Recording read", exact: true }),
    ).toBeFocused();
  });
});

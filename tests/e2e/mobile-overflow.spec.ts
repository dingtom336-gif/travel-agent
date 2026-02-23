import { test, expect } from "@playwright/test";

// Base path for the app
const BASE = "/travel";

// Viewports: narrow (iPhone SE) and standard (iPhone 14 Pro)
const IPHONE_SE = { width: 320, height: 568 };
const IPHONE_14_PRO = { width: 393, height: 852 };

// Helper: assert no horizontal overflow
async function assertNoOverflow(page: import("@playwright/test").Page) {
  const result = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
  }));
  expect(result.scrollWidth).toBeLessThanOrEqual(result.clientWidth + 1);
}

test.describe("Mobile overflow - iPhone 14 Pro (393px)", () => {
  test.use({ viewport: IPHONE_14_PRO });

  test("home page has no horizontal overflow", async ({ page }) => {
    await page.goto(`${BASE}/`);
    await page.waitForLoadState("networkidle");
    await assertNoOverflow(page);
    await page.screenshot({ path: "tests/screenshots/mobile-home-14pro.png", fullPage: true });
  });

  test("chat page has no horizontal overflow", async ({ page }) => {
    await page.goto(`${BASE}/chat`);
    await page.waitForLoadState("networkidle");
    await assertNoOverflow(page);
    await page.screenshot({ path: "tests/screenshots/mobile-chat-empty-14pro.png", fullPage: true });
  });

  test("chat input is fully visible and usable", async ({ page }) => {
    await page.goto(`${BASE}/chat`);
    await page.waitForLoadState("networkidle");

    const textarea = page.locator("textarea");
    await expect(textarea).toBeVisible();

    const sendBtn = page.locator('button[aria-label="Send message"]');
    await expect(sendBtn).toBeVisible();

    const inputBox = await textarea.boundingBox();
    expect(inputBox).not.toBeNull();
    if (inputBox) {
      expect(inputBox.x).toBeGreaterThanOrEqual(0);
      expect(inputBox.x + inputBox.width).toBeLessThanOrEqual(IPHONE_14_PRO.width + 1);
    }

    await page.screenshot({ path: "tests/screenshots/mobile-chat-input-14pro.png" });
  });

  test("send message and verify bubble does not overflow", async ({ page }) => {
    await page.goto(`${BASE}/chat`);
    await page.waitForLoadState("networkidle");

    const textarea = page.locator("textarea");
    await textarea.fill("我想去东京玩5天，帮我规划一下行程，预算大概1万元人民币左右，想去浅草寺、东京塔、新宿、涩谷、秋叶原");

    const sendBtn = page.locator('button[aria-label="Send message"]');
    await sendBtn.click();
    await page.waitForTimeout(500);

    await assertNoOverflow(page);
    await page.screenshot({ path: "tests/screenshots/mobile-chat-message-14pro.png" });
  });
});

test.describe("Mobile overflow - iPhone SE (320px)", () => {
  test.use({ viewport: IPHONE_SE });

  test("home page has no horizontal overflow on narrow screen", async ({ page }) => {
    await page.goto(`${BASE}/`);
    await page.waitForLoadState("networkidle");
    await assertNoOverflow(page);
    await page.screenshot({ path: "tests/screenshots/mobile-home-se.png", fullPage: true });
  });

  test("chat page has no horizontal overflow on narrow screen", async ({ page }) => {
    await page.goto(`${BASE}/chat`);
    await page.waitForLoadState("networkidle");
    await assertNoOverflow(page);
    await page.screenshot({ path: "tests/screenshots/mobile-chat-empty-se.png", fullPage: true });
  });

  test("guide cards do not overflow on narrow screen", async ({ page }) => {
    await page.goto(`${BASE}/`);
    await page.waitForLoadState("networkidle");

    // All guide cards should be within viewport
    const cards = page.locator("section button");
    const count = await cards.count();
    for (let i = 0; i < count; i++) {
      const box = await cards.nth(i).boundingBox();
      if (box) {
        expect(box.x + box.width).toBeLessThanOrEqual(IPHONE_SE.width + 2);
      }
    }
    await page.screenshot({ path: "tests/screenshots/mobile-guide-cards-se.png", fullPage: true });
  });

  test("send long message on narrow screen", async ({ page }) => {
    await page.goto(`${BASE}/chat`);
    await page.waitForLoadState("networkidle");

    const textarea = page.locator("textarea");
    await textarea.fill("这是一条很长的消息用来测试在iPhone SE这种非常窄的屏幕上用户消息气泡是否会溢出viewport导致出现水平滚动条影响体验");

    const sendBtn = page.locator('button[aria-label="Send message"]');
    await sendBtn.click();
    await page.waitForTimeout(500);

    await assertNoOverflow(page);
    await page.screenshot({ path: "tests/screenshots/mobile-chat-message-se.png" });
  });
});

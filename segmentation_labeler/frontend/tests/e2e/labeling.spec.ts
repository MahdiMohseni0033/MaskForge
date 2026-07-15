import { expect, test } from "@playwright/test";
import { promises as fs } from "node:fs";
import path from "node:path";
import { PNG } from "pngjs";

const API_BASE = "http://127.0.0.1:18000";

function bmp(width: number, height: number, shade: number): Buffer {
  const rowSize = Math.ceil((width * 3) / 4) * 4;
  const dataSize = rowSize * height;
  const buffer = Buffer.alloc(54 + dataSize);
  buffer.write("BM", 0, "ascii");
  buffer.writeUInt32LE(buffer.length, 2);
  buffer.writeUInt32LE(54, 10);
  buffer.writeUInt32LE(40, 14);
  buffer.writeInt32LE(width, 18);
  buffer.writeInt32LE(height, 22);
  buffer.writeUInt16LE(1, 26);
  buffer.writeUInt16LE(24, 28);
  buffer.writeUInt32LE(dataSize, 34);
  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      const offset = 54 + y * rowSize + x * 3;
      buffer[offset] = shade;
      buffer[offset + 1] = Math.min(255, shade + x * 2);
      buffer[offset + 2] = Math.min(255, shade + y * 2);
    }
  }
  return buffer;
}

test("opening screen remains scrollable on a short desktop viewport", async ({ page }) => {
  await page.setViewportSize({ width: 1100, height: 520 });
  await page.goto("/");
  const opening = page.locator(".opening-screen");
  await expect(opening).toBeVisible();
  const dimensions = await opening.evaluate((element) => ({
    clientHeight: element.clientHeight,
    scrollHeight: element.scrollHeight,
  }));
  expect(dimensions.scrollHeight).toBeGreaterThan(dimensions.clientHeight);
  await opening.evaluate((element) => element.scrollTo({ top: element.scrollHeight }));
  await expect.poll(() => opening.evaluate((element) => element.scrollTop)).toBeGreaterThan(0);
  await expect(page.getByRole("button", { name: "Create project" })).toBeVisible();
});

test("creates, annotates, resumes, and exports a two-image project", async ({ page, request }) => {
  const unique = `${process.pid}-${Date.now()}`;
  const projectName = `Browser workflow ${unique}`;
  const projectPath = `/tmp/segmentation-labeler-e2e-project-${unique}`;
  await fs.rm(projectPath, { recursive: true, force: true });

  await page.goto("/");
  await page.getByLabel("Project name").fill(projectName);
  await page.getByPlaceholder("Uses ~/.segmentation_labeler when blank").fill(projectPath);
  await page.getByLabel("Class 1 name").fill("Tissue");
  await page.getByRole("button", { name: "+ Add class" }).click();
  await page.getByLabel("Class 2 name").fill("Lesion");
  await page.getByRole("button", { name: "Create project" }).click();
  await expect(page.getByText(projectName)).toBeVisible();

  const importPanel = page.locator("details.action-panel").filter({ hasText: "Import images" });
  await importPanel.locator("summary").click();
  await importPanel.locator('input[type="file"]').first().setInputFiles([
    { name: "first.bmp", mimeType: "image/bmp", buffer: bmp(32, 24, 40) },
    { name: "second.bmp", mimeType: "image/bmp", buffer: bmp(32, 24, 90) },
  ]);
  await expect(page.locator(".image-item").filter({ hasText: "first.bmp" })).toBeVisible();
  await expect(page.locator(".image-item").filter({ hasText: "second.bmp" })).toBeVisible();
  await expect(page.locator(".canvas-container")).toBeVisible();

  const brushSize = page.getByLabel("Brush size");
  await brushSize.fill("4");
  const canvas = page.locator(".canvas-container");
  const box = await canvas.boundingBox();
  expect(box).not.toBeNull();
  if (!box) throw new Error("Canvas has no bounding box");

  // Brush class 1.
  await page.mouse.move(box.x + box.width * 0.25, box.y + box.height * 0.72);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width * 0.72, box.y + box.height * 0.72, { steps: 8 });
  await page.mouse.up();
  await expect(page.getByText("Saved", { exact: true })).toBeVisible();

  // Polygon class 2, closed with Enter.
  await page.locator(".class-item").filter({ hasText: "Lesion" }).click();
  await page.getByRole("button", { name: /Polygon/ }).click();
  await page.mouse.click(box.x + box.width * 0.32, box.y + box.height * 0.30);
  await page.mouse.click(box.x + box.width * 0.58, box.y + box.height * 0.31);
  await page.mouse.click(box.x + box.width * 0.45, box.y + box.height * 0.55);
  await page.keyboard.press("Enter");
  await expect(page.getByText("Saved", { exact: true })).toBeVisible();

  // Erase a small part, then exercise undo, redo, reset, and undo-reset.
  await page.getByRole("button", { name: /Eraser/ }).click();
  await page.mouse.click(box.x + box.width * 0.45, box.y + box.height * 0.40);
  await page.getByRole("button", { name: /Undo/ }).click();
  await page.getByRole("button", { name: /Redo/ }).click();
  page.once("dialog", (dialog) => void dialog.accept());
  await page.getByRole("button", { name: "Reset" }).click();
  await page.getByRole("button", { name: /Undo/ }).click();
  await page.getByLabel("Mark image completed").check();

  // Navigate and annotate the second image with class 2.
  await page.getByRole("button", { name: /Next/ }).click();
  await expect(page.getByText("2 of 2")).toBeVisible();
  await page.locator(".class-item").filter({ hasText: "Lesion" }).click();
  await page.getByRole("button", { name: /Brush/ }).click();
  await page.mouse.click(box.x + box.width * 0.55, box.y + box.height * 0.55);
  await expect(page.getByText("Saved", { exact: true })).toBeVisible();

  // A page reload returns to the opener; reopen from the persistent recent-project list.
  await page.reload();
  await expect(page.getByRole("heading", { name: "Segmentation Labeler" })).toBeVisible();
  await page.getByRole("button", { name: new RegExp(projectName) }).click();
  await expect(page.getByText("2 of 2")).toBeVisible();

  const exportPanel = page.locator("details.action-panel").filter({ hasText: "Export masks" });
  await exportPanel.locator("summary").click();
  const currentDownload = page.waitForEvent("download");
  await exportPanel.getByRole("button", { name: "Download current mask" }).click();
  expect((await currentDownload).suggestedFilename()).toBe("second_mask.png");

  const projectsResponse = await request.get(`${API_BASE}/api/projects`);
  const projects = (await projectsResponse.json()) as Array<{ project_id: string; name: string }>;
  const projectId = projects.find((item) => item.name === projectName)?.project_id;
  expect(projectId).toBeTruthy();
  if (!projectId) throw new Error("Created project was not registered");
  const detail = (await (await request.get(`${API_BASE}/api/projects/${projectId}`)).json()) as {
    images: Array<{ image_id: string; source_name: string; width: number; height: number }>;
  };
  expect(detail.images).toHaveLength(2);
  const first = detail.images.find((item) => item.source_name === "first.bmp");
  expect(first).toBeTruthy();
  if (!first) throw new Error("First image is missing");
  const maskResponse = await request.get(
    `${API_BASE}/api/projects/${projectId}/images/${first.image_id}/mask`,
  );
  const bytes = await maskResponse.body();
  const ids = new Set<number>();
  for (let offset = 0; offset < bytes.length; offset += 2) ids.add(bytes.readUInt16LE(offset));
  expect(ids).toContain(1);
  expect(ids).toContain(2);

  await exportPanel.getByRole("button", { name: "Export batch", exact: true }).click();
  const outputCode = exportPanel.locator(".success-message code");
  await expect(outputCode).toBeVisible();
  const outputDirectory = (await outputCode.textContent())?.trim();
  expect(outputDirectory).toBeTruthy();
  if (!outputDirectory) throw new Error("Export output path is missing");
  const zipDownload = page.waitForEvent("download");
  await exportPanel.getByRole("link", { name: "Download export ZIP" }).click();
  expect((await zipDownload).suggestedFilename()).toMatch(/\.zip$/);
  const metadata = JSON.parse(await fs.readFile(path.join(outputDirectory, "classes.json"), "utf8")) as {
    classes: Array<{ class_id: number }>;
    images: Array<{ mask: string; width: number; height: number }>;
  };
  expect(metadata.classes.map((item) => item.class_id)).toEqual([1, 2]);
  expect(metadata.images).toHaveLength(2);
  await expect(fs.readFile(path.join(outputDirectory, "class_summary.txt"), "utf8")).resolves.toContain(
    "ID\tLabel\tColor\tPixels\tImages containing class",
  );
  for (const item of metadata.images) {
    const exported = PNG.sync.read(await fs.readFile(path.join(outputDirectory, item.mask)));
    expect([exported.width, exported.height]).toEqual([item.width, item.height]);
    const values = new Set<number>();
    for (let offset = 0; offset < exported.data.length; offset += 4) values.add(exported.data[offset]);
    expect([...values].every((value) => value === 0 || value === 1 || value === 2)).toBe(true);
  }

  await fs.rm(projectPath, { recursive: true, force: true });
});

import type { Locator } from "@playwright/test";

/** What a screenshot of an element shows. */
export interface PixelStats {
  /** The share of the pixels inside a frame of 2 px that are darker than #ebebeb: 0 for a blank element. */
  ink: number;
  /** The most frequent color, such as the background of a cell. */
  dominant: [number, number, number];
}

/** A part of an element, in CSS pixels from its top left corner. */
export interface Area {
  x: number;
  y: number;
  width: number;
  height: number;
}

/**
 * The painted pixels of `locator`, or of an `area` of it: a screenshot, decoded in a blank page
 * of the same browser context, which has no Content Security Policy. A screenshot shows what the
 * browser painted, unlike the image data of the page.
 */
export async function pixelStats(locator: Locator, area?: Area): Promise<PixelStats> {
  const shot = area ? await areaShot(locator, area) : await locator.screenshot();
  const probe = await locator.page().context().newPage();
  try {
    return await probe.evaluate(async (data) => {
      const image = new Image();
      image.src = `data:image/png;base64,${data}`;
      await image.decode();
      const canvas = document.createElement("canvas");
      canvas.width = image.width;
      canvas.height = image.height;
      const context = canvas.getContext("2d")!;
      context.drawImage(image, 0, 0);
      const pixels = context.getImageData(0, 0, canvas.width, canvas.height).data;
      const counts = new Map<string, number>();
      let dark = 0;
      let inner = 0;
      for (let y = 0; y < canvas.height; y++)
        for (let x = 0; x < canvas.width; x++) {
          const at = (y * canvas.width + x) * 4;
          const [red, green, blue] = [pixels[at]!, pixels[at + 1]!, pixels[at + 2]!];
          const key = `${red},${green},${blue}`;
          counts.set(key, (counts.get(key) ?? 0) + 1);
          if (x < 2 || y < 2 || x >= canvas.width - 2 || y >= canvas.height - 2) continue;
          inner += 1;
          if (red + green + blue < 3 * 235) dark += 1;
        }
      const [color] = [...counts.entries()].sort((a, b) => b[1] - a[1])[0]!;
      return { ink: inner ? dark / inner : 0, dominant: color.split(",").map(Number) as [number, number, number] };
    }, shot.toString("base64"));
  } finally {
    await probe.close();
  }
}

async function areaShot(locator: Locator, area: Area): Promise<Buffer> {
  await locator.scrollIntoViewIfNeeded();
  const box = await locator.boundingBox();
  if (!box) throw new Error("The element of the area is not visible");
  return locator.page().screenshot({ clip: { ...area, x: box.x + area.x, y: box.y + area.y } });
}

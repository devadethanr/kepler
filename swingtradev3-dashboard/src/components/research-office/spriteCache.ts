// Adapted from Pixel Agents spriteCache.ts at b1bafd02896d90d83457266575a1e8e5011ce997.
// See LICENSE.pixel-agents for the upstream MIT notice.
type SpriteData = string[][];
const zoomCaches = new Map<number, WeakMap<SpriteData, HTMLCanvasElement>>();

export function getCachedSprite(sprite: SpriteData, zoom: number): HTMLCanvasElement {
  let cache = zoomCaches.get(zoom);
  if (!cache) {
    cache = new WeakMap();
    zoomCaches.set(zoom, cache);
  }
  const cached = cache.get(sprite);
  if (cached) return cached;
  const rows = sprite.length;
  const cols = sprite[0].length;
  const canvas = document.createElement('canvas');
  canvas.width = cols * zoom;
  canvas.height = rows * zoom;
  const ctx = canvas.getContext('2d')!;
  ctx.imageSmoothingEnabled = false;
  for (let row = 0; row < rows; row++) {
    for (let col = 0; col < cols; col++) {
      const color = sprite[row][col];
      if (color === '') continue;
      ctx.fillStyle = color;
      ctx.fillRect(col * zoom, row * zoom, zoom, zoom);
    }
  }
  cache.set(sprite, canvas);
  return canvas;
}

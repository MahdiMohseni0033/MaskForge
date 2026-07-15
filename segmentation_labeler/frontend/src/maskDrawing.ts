export interface Point {
  x: number;
  y: number;
}

function paintCircle(
  mask: Uint16Array,
  width: number,
  height: number,
  point: Point,
  radius: number,
  classId: number,
) {
  const x0 = Math.max(0, Math.floor(point.x - radius));
  const x1 = Math.min(width - 1, Math.ceil(point.x + radius));
  const y0 = Math.max(0, Math.floor(point.y - radius));
  const y1 = Math.min(height - 1, Math.ceil(point.y + radius));
  const squared = radius * radius;
  for (let y = y0; y <= y1; y += 1) {
    for (let x = x0; x <= x1; x += 1) {
      if ((x - point.x) ** 2 + (y - point.y) ** 2 <= squared) {
        mask[y * width + x] = classId;
      }
    }
  }
}

export function paintSegment(
  mask: Uint16Array,
  width: number,
  height: number,
  start: Point,
  end: Point,
  brushSize: number,
  classId: number,
) {
  const radius = brushSize / 2;
  const distance = Math.hypot(end.x - start.x, end.y - start.y);
  const spacing = Math.max(0.5, radius / 2);
  const steps = Math.max(1, Math.ceil(distance / spacing));
  for (let index = 0; index <= steps; index += 1) {
    const fraction = index / steps;
    paintCircle(
      mask,
      width,
      height,
      {
        x: start.x + (end.x - start.x) * fraction,
        y: start.y + (end.y - start.y) * fraction,
      },
      radius,
      classId,
    );
  }
}

export function polygonArea(vertices: Point[]) {
  return Math.abs(
    vertices.reduce((sum, point, index) => {
      const next = vertices[(index + 1) % vertices.length];
      return sum + point.x * next.y - next.x * point.y;
    }, 0) / 2,
  );
}

export function fillPolygon(
  source: Uint16Array,
  width: number,
  height: number,
  vertices: Point[],
  classId: number,
) {
  if (vertices.length < 3 || polygonArea(vertices) < 0.5) {
    throw new Error("A polygon needs at least three valid vertices");
  }
  const selection = document.createElement("canvas");
  selection.width = width;
  selection.height = height;
  const context = selection.getContext("2d", { willReadFrequently: true });
  if (!context) throw new Error("Canvas rendering is unavailable");
  context.beginPath();
  context.moveTo(vertices[0].x, vertices[0].y);
  vertices.slice(1).forEach((point) => context.lineTo(point.x, point.y));
  context.closePath();
  context.fillStyle = "#ffffff";
  context.fill();
  const pixels = context.getImageData(0, 0, width, height).data;
  const result = new Uint16Array(source);
  for (let index = 0; index < result.length; index += 1) {
    if (pixels[index * 4 + 3] > 0) result[index] = classId;
  }
  return result;
}


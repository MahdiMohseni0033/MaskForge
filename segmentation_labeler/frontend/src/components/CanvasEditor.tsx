import { useEffect, useMemo, useRef, useState } from "react";
import Konva from "konva";
import { Circle, Image as KonvaImage, Layer, Line, Rect, Stage } from "react-konva";
import { fillPolygon, paintSegment, type Point } from "../maskDrawing";
import type { SegmentationClass, Tool } from "../types";

export type ViewCommand = { kind: "fit" | "actual" | "zoom-in" | "zoom-out"; serial: number };

interface Props {
  imageUrl: string;
  width: number;
  height: number;
  mask: Uint16Array;
  classes: SegmentationClass[];
  selectedClassId: number;
  tool: Tool;
  brushSize: number;
  opacity: number;
  maskVisible: boolean;
  viewCommand: ViewCommand;
  onPreview: (mask: Uint16Array) => void;
  onCommit: (mask: Uint16Array) => void;
  onMessage: (message: string) => void;
}

interface ViewTransform {
  x: number;
  y: number;
  scale: number;
}

export function CanvasEditor({
  imageUrl,
  width,
  height,
  mask,
  classes,
  selectedClassId,
  tool,
  brushSize,
  opacity,
  maskVisible,
  viewCommand,
  onPreview,
  onCommit,
  onMessage,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const stageRef = useRef<Konva.Stage>(null);
  const draftRef = useRef<Uint16Array | null>(null);
  const lastPointRef = useRef<Point | null>(null);
  const [container, setContainer] = useState({ width: 800, height: 600 });
  const [sourceImage, setSourceImage] = useState<HTMLImageElement | null>(null);
  const [maskImage, setMaskImage] = useState<HTMLCanvasElement | null>(null);
  const [view, setView] = useState<ViewTransform>({ x: 0, y: 0, scale: 1 });
  const [cursor, setCursor] = useState<Point | null>(null);
  const [polygon, setPolygon] = useState<Point[]>([]);
  const [polygonPointer, setPolygonPointer] = useState<Point | null>(null);

  const fit = () => {
    const scale = Math.min(container.width / width, container.height / height) * 0.96;
    setView({
      scale,
      x: (container.width - width * scale) / 2,
      y: (container.height - height * scale) / 2,
    });
  };

  useEffect(() => {
    const element = containerRef.current;
    if (!element) return;
    const observer = new ResizeObserver(([entry]) => {
      setContainer({
        width: Math.max(1, Math.floor(entry.contentRect.width)),
        height: Math.max(1, Math.floor(entry.contentRect.height)),
      });
    });
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const image = new window.Image();
    image.onload = () => setSourceImage(image);
    image.onerror = () => onMessage("The imported display image could not be loaded");
    image.src = imageUrl;
  }, [imageUrl, onMessage]);

  useEffect(() => {
    fit();
    // Fit after switching source images or after the first measured layout.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [imageUrl, width, height, container.width, container.height]);

  useEffect(() => {
    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    const context = canvas.getContext("2d");
    if (!context) return;
    const imageData = context.createImageData(width, height);
    const colors = new Map(
      classes.map((item) => [
        item.class_id,
        [
          Number.parseInt(item.color.slice(1, 3), 16),
          Number.parseInt(item.color.slice(3, 5), 16),
          Number.parseInt(item.color.slice(5, 7), 16),
        ],
      ]),
    );
    for (let index = 0; index < mask.length; index += 1) {
      const color = colors.get(mask[index]);
      if (!color) continue;
      const offset = index * 4;
      imageData.data[offset] = color[0];
      imageData.data[offset + 1] = color[1];
      imageData.data[offset + 2] = color[2];
      imageData.data[offset + 3] = 255;
    }
    context.putImageData(imageData, 0, 0);
    setMaskImage(canvas);
  }, [mask, classes, width, height]);

  useEffect(() => {
    if (viewCommand.kind === "fit") fit();
    if (viewCommand.kind === "actual") {
      setView({ x: (container.width - width) / 2, y: (container.height - height) / 2, scale: 1 });
    }
    if (viewCommand.kind === "zoom-in" || viewCommand.kind === "zoom-out") {
      const factor = viewCommand.kind === "zoom-in" ? 1.25 : 0.8;
      setView((current) => {
        const nextScale = Math.min(20, Math.max(0.05, current.scale * factor));
        const cx = container.width / 2;
        const cy = container.height / 2;
        const imageX = (cx - current.x) / current.scale;
        const imageY = (cy - current.y) / current.scale;
        return { scale: nextScale, x: cx - imageX * nextScale, y: cy - imageY * nextScale };
      });
    }
    // The serial is intentionally the trigger even when command kinds repeat.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [viewCommand.serial]);

  useEffect(() => {
    setPolygon([]);
    setPolygonPointer(null);
  }, [tool, imageUrl]);

  const imagePoint = (): Point | null => {
    const pointer = stageRef.current?.getPointerPosition();
    if (!pointer) return null;
    const point = { x: (pointer.x - view.x) / view.scale, y: (pointer.y - view.y) / view.scale };
    if (point.x < 0 || point.y < 0 || point.x >= width || point.y >= height) return null;
    return point;
  };

  const finishPolygon = () => {
    if (polygon.length < 3) {
      onMessage("A polygon needs at least three vertices");
      return;
    }
    try {
      onCommit(fillPolygon(mask, width, height, polygon, selectedClassId));
      setPolygon([]);
      setPolygonPointer(null);
    } catch (error) {
      onMessage(error instanceof Error ? error.message : "Invalid polygon");
    }
  };

  useEffect(() => {
    const keyboard = (event: KeyboardEvent) => {
      if (tool !== "polygon") return;
      if (event.key === "Escape") {
        setPolygon([]);
        setPolygonPointer(null);
      } else if (event.key === "Enter") {
        event.preventDefault();
        finishPolygon();
      }
    };
    window.addEventListener("keydown", keyboard);
    return () => window.removeEventListener("keydown", keyboard);
  });

  const pointerDown = () => {
    const point = imagePoint();
    if (!point || tool === "pan") return;
    if (tool === "polygon") {
      if (polygon.length >= 3 && Math.hypot(point.x - polygon[0].x, point.y - polygon[0].y) <= 10 / view.scale) {
        finishPolygon();
      } else {
        setPolygon((current) => [...current, point]);
      }
      return;
    }
    const draft = new Uint16Array(mask);
    const classId = tool === "eraser" ? 0 : selectedClassId;
    paintSegment(draft, width, height, point, point, brushSize, classId);
    draftRef.current = draft;
    lastPointRef.current = point;
    onPreview(new Uint16Array(draft));
  };

  const pointerMove = () => {
    const point = imagePoint();
    setCursor(point);
    if (tool === "polygon") setPolygonPointer(point);
    if (!point || !draftRef.current || !lastPointRef.current) return;
    const classId = tool === "eraser" ? 0 : selectedClassId;
    paintSegment(
      draftRef.current,
      width,
      height,
      lastPointRef.current,
      point,
      brushSize,
      classId,
    );
    lastPointRef.current = point;
    onPreview(new Uint16Array(draftRef.current));
  };

  const pointerUp = () => {
    if (draftRef.current) onCommit(new Uint16Array(draftRef.current));
    draftRef.current = null;
    lastPointRef.current = null;
  };

  const polygonPoints = useMemo(
    () => [...polygon, ...(polygonPointer && polygon.length ? [polygonPointer] : [])].flatMap((p) => [p.x, p.y]),
    [polygon, polygonPointer],
  );

  return (
    <div className="canvas-container" ref={containerRef} data-testid="annotation-canvas">
      <Stage
        ref={stageRef}
        width={container.width}
        height={container.height}
        x={view.x}
        y={view.y}
        scaleX={view.scale}
        scaleY={view.scale}
        draggable={tool === "pan"}
        onDragEnd={(event) => setView((current) => ({ ...current, x: event.target.x(), y: event.target.y() }))}
        onPointerDown={pointerDown}
        onPointerMove={pointerMove}
        onPointerUp={pointerUp}
        onPointerLeave={() => { setCursor(null); pointerUp(); }}
        onDblClick={() => tool === "polygon" && finishPolygon()}
        onWheel={(event) => {
          event.evt.preventDefault();
          const pointer = stageRef.current?.getPointerPosition();
          if (!pointer) return;
          const imageX = (pointer.x - view.x) / view.scale;
          const imageY = (pointer.y - view.y) / view.scale;
          const nextScale = Math.min(20, Math.max(0.05, view.scale * (event.evt.deltaY > 0 ? 0.9 : 1.1)));
          setView({ x: pointer.x - imageX * nextScale, y: pointer.y - imageY * nextScale, scale: nextScale });
        }}
      >
        <Layer imageSmoothingEnabled={false}>
          <Rect x={0} y={0} width={width} height={height} fill="#05090d" />
          {sourceImage && <KonvaImage image={sourceImage} width={width} height={height} />}
          {maskImage && maskVisible && (
            <KonvaImage image={maskImage} width={width} height={height} opacity={opacity} listening={false} />
          )}
          {polygon.length > 0 && (
            <>
              <Line points={polygonPoints} stroke="#ffffff" strokeWidth={2 / view.scale} dash={[8 / view.scale, 5 / view.scale]} />
              {polygon.map((point, index) => (
                <Circle
                  key={`${point.x}-${point.y}-${index}`}
                  x={point.x}
                  y={point.y}
                  radius={(index === 0 ? 7 : 4) / view.scale}
                  fill={index === 0 ? "#facc15" : "#ffffff"}
                  stroke="#111827"
                  strokeWidth={1 / view.scale}
                />
              ))}
            </>
          )}
          {cursor && (tool === "brush" || tool === "eraser") && (
            <Circle
              x={cursor.x}
              y={cursor.y}
              radius={brushSize / 2}
              stroke={tool === "eraser" ? "#ffffff" : classes.find((item) => item.class_id === selectedClassId)?.color || "#ffffff"}
              strokeWidth={1.5 / view.scale}
              listening={false}
            />
          )}
        </Layer>
      </Stage>
      <div className="zoom-readout">{Math.round(view.scale * 100)}%</div>
    </div>
  );
}

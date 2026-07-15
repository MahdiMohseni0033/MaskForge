import type { SaveStatus, Tool } from "../types";

interface Props {
  tool: Tool;
  brushSize: number;
  canUndo: boolean;
  canRedo: boolean;
  saveStatus: SaveStatus;
  maskVisible: boolean;
  opacity: number;
  onTool: (tool: Tool) => void;
  onBrushSize: (size: number) => void;
  onUndo: () => void;
  onRedo: () => void;
  onClear: () => void;
  onReset: () => void;
  onMaskVisible: (visible: boolean) => void;
  onOpacity: (opacity: number) => void;
  onView: (kind: "fit" | "actual" | "zoom-in" | "zoom-out") => void;
}

const tools: Array<{ id: Tool; label: string; shortcut: string; glyph: string }> = [
  { id: "brush", label: "Brush", shortcut: "B", glyph: "●" },
  { id: "eraser", label: "Eraser", shortcut: "E", glyph: "◇" },
  { id: "polygon", label: "Polygon", shortcut: "P", glyph: "⬡" },
  { id: "pan", label: "Pan", shortcut: "H", glyph: "✥" },
];

export function Toolbar(props: Props) {
  return (
    <div className="toolbar" aria-label="Annotation toolbar">
      <div className="tool-group">
        {tools.map((item) => (
          <button
            key={item.id}
            className={props.tool === item.id ? "tool active" : "tool"}
            aria-pressed={props.tool === item.id}
            title={`${item.label} (${item.shortcut})`}
            onClick={() => props.onTool(item.id)}
          >
            <span>{item.glyph}</span>{item.label}<kbd>{item.shortcut}</kbd>
          </button>
        ))}
      </div>
      <div className="toolbar-divider" />
      <label className="brush-control">
        Size
        <input
          aria-label="Brush size"
          type="range"
          min="1"
          max="200"
          value={props.brushSize}
          onChange={(event) => props.onBrushSize(Number(event.target.value))}
        />
        <output>{props.brushSize}px</output>
      </label>
      <div className="toolbar-divider" />
      <button title="Undo (Ctrl/Command+Z)" disabled={!props.canUndo} onClick={props.onUndo}>↶ Undo</button>
      <button title="Redo (Ctrl+Y or Ctrl/Command+Shift+Z)" disabled={!props.canRedo} onClick={props.onRedo}>↷ Redo</button>
      <button title="Clear only the active class" onClick={props.onClear}>Clear class</button>
      <button title="Reset every class on this image" onClick={props.onReset}>Reset</button>
      <div className="toolbar-spacer" />
      <button title="Zoom out" aria-label="Zoom out" onClick={() => props.onView("zoom-out")}>−</button>
      <button title="100% zoom" onClick={() => props.onView("actual")}>100%</button>
      <button title="Fit image" onClick={() => props.onView("fit")}>Fit</button>
      <button title="Zoom in" aria-label="Zoom in" onClick={() => props.onView("zoom-in")}>+</button>
      <label className="overlay-toggle" title="Show or hide the mask overlay">
        <input
          type="checkbox"
          checked={props.maskVisible}
          onChange={(event) => props.onMaskVisible(event.target.checked)}
        />
        Mask
      </label>
      <label className="opacity-control" title="Mask overlay opacity">
        <input
          aria-label="Overlay opacity"
          type="range"
          min="0"
          max="1"
          step="0.05"
          value={props.opacity}
          onChange={(event) => props.onOpacity(Number(event.target.value))}
        />
      </label>
      <div className={`save-state ${props.saveStatus}`} role="status">
        <span />{props.saveStatus === "saving" ? "Saving" : props.saveStatus === "failed" ? "Save failed" : "Saved"}
      </div>
    </div>
  );
}


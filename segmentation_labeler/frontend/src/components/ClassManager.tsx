import { useState } from "react";
import { api } from "../api";
import type { SegmentationClass } from "../types";

interface Props {
  projectId: string;
  classes: SegmentationClass[];
  selectedClassId: number;
  onSelect: (classId: number) => void;
  onChange: () => Promise<void>;
  onError: (message: string) => void;
}

export function ClassManager({
  projectId,
  classes,
  selectedClassId,
  onSelect,
  onChange,
  onError,
}: Props) {
  const [editing, setEditing] = useState(false);
  const [newName, setNewName] = useState("");
  const [newColor, setNewColor] = useState("#22C55E");

  const update = async (item: SegmentationClass, form: HTMLFormElement) => {
    const data = new FormData(form);
    try {
      await api.updateClass(projectId, item.class_id, {
        name: String(data.get("name")),
        color: String(data.get("color")),
      });
      await onChange();
    } catch (caught) {
      onError(caught instanceof Error ? caught.message : "Could not update class");
    }
  };

  const remove = async (item: SegmentationClass) => {
    const confirmed = window.confirm(
      `Delete class “${item.name}”? If it is used, a second confirmation will be required to replace its pixels with background.`,
    );
    if (!confirmed) return;
    try {
      await api.deleteClass(projectId, item.class_id, false);
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : "Could not delete class";
      if (!message.includes("used in masks") || !window.confirm(`${message}\n\nReplace those pixels with background now?`)) {
        onError(message);
        return;
      }
      await api.deleteClass(projectId, item.class_id, true);
    }
    await onChange();
  };

  return (
    <section className="sidebar-section class-section">
      <div className="section-heading">
        <span>CLASSES</span>
        <button className="text-button" onClick={() => setEditing((value) => !value)}>
          {editing ? "Done" : "Manage"}
        </button>
      </div>
      <button
        className={selectedClassId === 0 ? "class-item active background" : "class-item background"}
        onClick={() => onSelect(0)}
        title="Background is reserved for erasing"
      >
        <span className="class-swatch checker" />
        <span><strong>Background</strong><small>ID 0 · eraser only</small></span>
      </button>
      {classes.map((item) => (
        <div key={item.class_id}>
          <button
            className={selectedClassId === item.class_id ? "class-item active" : "class-item"}
            onClick={() => onSelect(item.class_id)}
          >
            <span className="class-swatch" style={{ backgroundColor: item.color }} />
            <span><strong>{item.name}</strong><small>ID {item.class_id}</small></span>
            {selectedClassId === item.class_id && <span className="selected-tick">✓</span>}
          </button>
          {editing && (
            <form
              className="class-edit"
              onSubmit={(event) => {
                event.preventDefault();
                void update(item, event.currentTarget);
              }}
            >
              <input name="color" aria-label={`${item.name} color`} type="color" defaultValue={item.color} />
              <input name="name" aria-label={`${item.name} name`} defaultValue={item.name} required />
              <button type="submit">Save</button>
              <button type="button" title={`Delete ${item.name}`} onClick={() => void remove(item)}>×</button>
            </form>
          )}
        </div>
      ))}
      {editing && (
        <form
          className="class-add"
          onSubmit={async (event) => {
            event.preventDefault();
            try {
              await api.addClass(projectId, { name: newName, color: newColor });
              setNewName("");
              await onChange();
            } catch (caught) {
              onError(caught instanceof Error ? caught.message : "Could not add class");
            }
          }}
        >
          <input aria-label="New class color" type="color" value={newColor} onChange={(event) => setNewColor(event.target.value)} />
          <input aria-label="New class name" required placeholder="New class" value={newName} onChange={(event) => setNewName(event.target.value)} />
          <button type="submit">Add</button>
        </form>
      )}
    </section>
  );
}


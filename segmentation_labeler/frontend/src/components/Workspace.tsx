import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api";
import type {
  AnnotationStatus,
  ImportResult,
  Project,
  SaveStatus,
  Tool,
} from "../types";
import { CanvasEditor, type ViewCommand } from "./CanvasEditor";
import { ClassManager } from "./ClassManager";
import { ExportPanel, ImportPanel } from "./ImportExport";
import { Toolbar } from "./Toolbar";

interface Props {
  initialProject: Project;
  onClose: () => void;
}

const masksEqual = (left: Uint16Array, right: Uint16Array) => {
  if (left.length !== right.length) return false;
  for (let index = 0; index < left.length; index += 1) {
    if (left[index] !== right[index]) return false;
  }
  return true;
};

export function Workspace({ initialProject, onClose }: Props) {
  const [project, setProject] = useState(initialProject);
  const [currentId, setCurrentId] = useState(
    initialProject.last_image_id || initialProject.images[0]?.image_id || "",
  );
  const [mask, setMask] = useState<Uint16Array | null>(null);
  const [history, setHistory] = useState<Uint16Array[]>([]);
  const [historyIndex, setHistoryIndex] = useState(0);
  const [selectedClassId, setSelectedClassId] = useState(initialProject.classes[0]?.class_id || 1);
  const [tool, setTool] = useState<Tool>("brush");
  const [brushSize, setBrushSize] = useState(24);
  const [saveStatus, setSaveStatus] = useState<SaveStatus>("saved");
  const [loading, setLoading] = useState(Boolean(currentId));
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [search, setSearch] = useState("");
  const [exportSelection, setExportSelection] = useState<string[]>([]);
  const [viewCommand, setViewCommand] = useState<ViewCommand>({ kind: "fit", serial: 0 });
  const [opacity, setOpacity] = useState(project.overlay_opacity);
  const [maskVisible, setMaskVisible] = useState(project.mask_visible);
  const pendingSave = useRef<Promise<void>>(Promise.resolve());
  const queuedSave = useRef<{
    imageId: string;
    mask: Uint16Array;
    generation: number;
  } | null>(null);
  const saveWorkerActive = useRef(false);
  const unsaved = useRef(false);
  const saveGeneration = useRef(0);
  const statusOverrides = useRef(new Map<string, AnnotationStatus>());
  const lastForegroundClass = useRef(initialProject.classes[0]?.class_id || 1);
  const loadSerial = useRef(0);

  const currentImage = project.images.find((item) => item.image_id === currentId);
  const currentIndex = project.images.findIndex((item) => item.image_id === currentId);
  const completed = project.images.filter((item) => item.status === "completed").length;
  const filteredImages = project.images.filter((item) =>
    item.relative_path.toLocaleLowerCase().includes(search.toLocaleLowerCase()),
  );

  const showError = useCallback((message: string) => {
    setError(message);
    window.setTimeout(() => setError((value) => (value === message ? "" : value)), 8000);
  }, []);

  const reloadProject = useCallback(async () => {
    const refreshed = await api.getProject(initialProject.project_id);
    setProject(refreshed);
    if (!refreshed.classes.some((item) => item.class_id === selectedClassId)) {
      setSelectedClassId(refreshed.classes[0]?.class_id || 1);
    }
    return refreshed;
  }, [initialProject.project_id, selectedClassId]);

  const loadMask = useCallback(
    async (imageId: string) => {
      const serial = ++loadSerial.current;
      setLoading(true);
      try {
        const loaded = await api.fetchMask(project.project_id, imageId);
        if (serial !== loadSerial.current) return;
        setMask(loaded);
        setHistory([new Uint16Array(loaded)]);
        setHistoryIndex(0);
        setSaveStatus("saved");
        unsaved.current = false;
      } catch (caught) {
        showError(caught instanceof Error ? caught.message : "Could not load mask");
        setMask(null);
      } finally {
        if (serial === loadSerial.current) setLoading(false);
      }
    },
    [project.project_id, showError],
  );

  useEffect(() => {
    if (currentId) void loadMask(currentId);
    else {
      setMask(null);
      setHistory([]);
      setLoading(false);
    }
  }, [currentId, loadMask]);

  const persist = useCallback(
    (nextMask: Uint16Array, imageId: string) => {
      const generation = ++saveGeneration.current;
      unsaved.current = true;
      setSaveStatus("saving");
      queuedSave.current = { imageId, mask: new Uint16Array(nextMask), generation };
      if (saveWorkerActive.current) return;

      saveWorkerActive.current = true;
      pendingSave.current = (async () => {
        while (queuedSave.current) {
          const job = queuedSave.current;
          queuedSave.current = null;
          try {
            const result = await api.saveMask(project.project_id, job.imageId, job.mask);
            setProject((current) => ({
              ...current,
              images: current.images.map((item) =>
                item.image_id === job.imageId
                  ? {
                      ...item,
                      status:
                        statusOverrides.current.get(job.imageId) ||
                        (item.status === "completed" ? "completed" : result.status),
                      modified_at: result.modified_at,
                    }
                  : item,
              ),
            }));
            if (job.generation === saveGeneration.current) {
              unsaved.current = false;
              setSaveStatus("saved");
            }
          } catch (caught) {
            if (job.generation === saveGeneration.current) {
              unsaved.current = true;
              setSaveStatus("failed");
              showError(caught instanceof Error ? caught.message : "Autosave failed");
            }
          }
        }
        saveWorkerActive.current = false;
      })();
    },
    [project.project_id, showError],
  );

  const commit = useCallback(
    (nextMask: Uint16Array) => {
      const savedState = history[historyIndex];
      if (!currentImage || (savedState && masksEqual(savedState, nextMask))) return;
      const snapshot = new Uint16Array(nextMask);
      setMask(snapshot);
      setHistory((current) => {
        const next = [...current.slice(0, historyIndex + 1), new Uint16Array(snapshot)];
        const limited = next.length > 31 ? next.slice(next.length - 31) : next;
        setHistoryIndex(limited.length - 1);
        return limited;
      });
      persist(snapshot, currentImage.image_id);
    },
    [currentImage, history, historyIndex, persist],
  );

  const applyHistory = useCallback(
    (nextIndex: number) => {
      if (!currentImage || nextIndex < 0 || nextIndex >= history.length) return;
      const nextMask = new Uint16Array(history[nextIndex]);
      setHistoryIndex(nextIndex);
      setMask(nextMask);
      persist(nextMask, currentImage.image_id);
    },
    [currentImage, history, persist],
  );

  const clearClass = useCallback(() => {
    if (!mask || selectedClassId === 0) {
      showError("Select a foreground class to clear");
      return;
    }
    const selected = project.classes.find((item) => item.class_id === selectedClassId);
    if (!window.confirm(`Clear every “${selected?.name || selectedClassId}” pixel from this image?`)) return;
    const next = new Uint16Array(mask);
    for (let index = 0; index < next.length; index += 1) {
      if (next[index] === selectedClassId) next[index] = 0;
    }
    commit(next);
  }, [commit, mask, project.classes, selectedClassId, showError]);

  const reset = useCallback(() => {
    if (!mask || !window.confirm("Reset the entire mask for this image? This can be undone.")) return;
    commit(new Uint16Array(mask.length));
  }, [commit, mask]);

  const selectImage = useCallback(
    async (imageId: string) => {
      if (imageId === currentId) return;
      await pendingSave.current;
      if (unsaved.current && !window.confirm("The latest changes were not saved. Leave this image anyway?")) return;
      setCurrentId(imageId);
      try {
        await api.updateSettings(project.project_id, { last_image_id: imageId });
      } catch (caught) {
        showError(caught instanceof Error ? caught.message : "Could not save navigation state");
      }
    },
    [currentId, project.project_id, showError],
  );

  const activateTool = useCallback(
    (nextTool: Tool) => {
      if ((nextTool === "brush" || nextTool === "polygon") && selectedClassId === 0) {
        const fallback = project.classes.find(
          (item) => item.class_id === lastForegroundClass.current,
        )?.class_id;
        setSelectedClassId(fallback || project.classes[0]?.class_id || 1);
      }
      setTool(nextTool);
    },
    [project.classes, selectedClassId],
  );

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement;
      if (["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName)) return;
      const command = event.ctrlKey || event.metaKey;
      if (command && event.key.toLowerCase() === "z") {
        event.preventDefault();
        applyHistory(historyIndex + (event.shiftKey ? 1 : -1));
      } else if (command && event.key.toLowerCase() === "y") {
        event.preventDefault();
        applyHistory(historyIndex + 1);
      } else if (!command && event.key.toLowerCase() === "b") activateTool("brush");
      else if (!command && event.key.toLowerCase() === "e") activateTool("eraser");
      else if (!command && event.key.toLowerCase() === "p") activateTool("polygon");
      else if (!command && event.key.toLowerCase() === "h") activateTool("pan");
      else if (!command && event.key === "[") setBrushSize((value) => Math.max(1, value - 2));
      else if (!command && event.key === "]") setBrushSize((value) => Math.min(200, value + 2));
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [activateTool, applyHistory, historyIndex]);

  const importFinished = async (result: ImportResult) => {
    const refreshed = await reloadProject();
    if (result.errors.length) {
      showError(result.errors.map((item) => `${item.file}: ${item.error}`).join(" · "));
    }
    if (!currentId && result.imported[0]) {
      await selectImage(result.imported[0].image_id);
    }
    setNotice(`Imported ${result.imported.length} image${result.imported.length === 1 ? "" : "s"}`);
    if (!refreshed.images.length) setNotice("No supported images were imported");
  };

  const updateStatus = async (status: AnnotationStatus) => {
    if (!currentImage) return;
    statusOverrides.current.set(currentImage.image_id, status);
    setProject((current) => ({
      ...current,
      images: current.images.map((item) =>
        item.image_id === currentImage.image_id ? { ...item, status } : item,
      ),
    }));
    try {
      await pendingSave.current;
      if (unsaved.current) throw new Error("The latest mask changes have not been saved");
      const updated = await api.setStatus(project.project_id, currentImage.image_id, status);
      setProject((current) => ({
        ...current,
        images: current.images.map((item) =>
          item.image_id === currentImage.image_id ? { ...item, status: updated.status } : item,
        ),
      }));
      statusOverrides.current.delete(currentImage.image_id);
    } catch (caught) {
      statusOverrides.current.delete(currentImage.image_id);
      showError(caught instanceof Error ? caught.message : "Could not change image status");
      await reloadProject();
    }
  };

  const settingChange = (value: { opacity?: number; visible?: boolean }) => {
    if (value.opacity !== undefined) setOpacity(value.opacity);
    if (value.visible !== undefined) setMaskVisible(value.visible);
    void api
      .updateSettings(project.project_id, {
        overlay_opacity: value.opacity,
        mask_visible: value.visible,
      })
      .catch((caught) => showError(caught instanceof Error ? caught.message : "Could not save display setting"));
  };

  return (
    <main className="workspace">
      <div className="small-window-warning">Enlarge this window for reliable annotation.</div>
      <header className="workspace-header">
        <button
          className="brand-button"
          title="Return to project screen"
          onClick={async () => {
            await pendingSave.current;
            if (unsaved.current && !window.confirm("Unsaved changes remain. Close the project anyway?")) return;
            onClose();
          }}
        >SL</button>
        <div><strong>{project.name}</strong><span>{project.storage_path}</span></div>
        <div className="header-progress">
          <span>{completed} / {project.images.length} completed</span>
          <div><i style={{ width: `${project.images.length ? (completed / project.images.length) * 100 : 0}%` }} /></div>
        </div>
      </header>

      <Toolbar
        tool={tool}
        brushSize={brushSize}
        canUndo={historyIndex > 0}
        canRedo={historyIndex + 1 < history.length}
        saveStatus={saveStatus}
        maskVisible={maskVisible}
        opacity={opacity}
        onTool={activateTool}
        onBrushSize={setBrushSize}
        onUndo={() => applyHistory(historyIndex - 1)}
        onRedo={() => applyHistory(historyIndex + 1)}
        onClear={clearClass}
        onReset={reset}
        onMaskVisible={(visible) => settingChange({ visible })}
        onOpacity={(nextOpacity) => settingChange({ opacity: nextOpacity })}
        onView={(kind) => setViewCommand((current) => ({ kind, serial: current.serial + 1 }))}
      />

      <aside className="sidebar">
        <ClassManager
          projectId={project.project_id}
          classes={project.classes}
          selectedClassId={selectedClassId}
          onSelect={(classId) => {
            setSelectedClassId(classId);
            if (classId === 0) setTool("eraser");
            else {
              lastForegroundClass.current = classId;
              if (tool === "eraser") setTool("brush");
            }
          }}
          onChange={async () => { await reloadProject(); if (currentId) await loadMask(currentId); }}
          onError={showError}
        />

        <section className="sidebar-section image-section">
          <div className="section-heading"><span>IMAGES</span><b>{project.images.length}</b></div>
          <input
            className="image-search"
            aria-label="Search images"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search image list…"
          />
          <div className="image-list">
            {filteredImages.map((item, index) => (
              <button
                key={item.image_id}
                className={item.image_id === currentId ? "image-item active" : "image-item"}
                onClick={() => void selectImage(item.image_id)}
              >
                <input
                  aria-label={`Select ${item.relative_path} for export`}
                  type="checkbox"
                  checked={exportSelection.includes(item.image_id)}
                  onClick={(event) => event.stopPropagation()}
                  onChange={(event) =>
                    setExportSelection((current) =>
                      event.target.checked
                        ? [...current, item.image_id]
                        : current.filter((id) => id !== item.image_id),
                    )
                  }
                />
                <span className={`status-dot ${item.status}`} title={item.status.replace("_", " ")} />
                <span><strong>{item.source_name}</strong><small>{item.relative_path} · {item.width}×{item.height}</small></span>
                <em>{index + 1}</em>
              </button>
            ))}
            {!filteredImages.length && <p className="empty-note">No matching images</p>}
          </div>
          <div className="status-legend"><span><i className="status-dot not_started" />Not started</span><span><i className="status-dot in_progress" />In progress</span><span><i className="status-dot completed" />Completed</span></div>
        </section>

        <section className="sidebar-section project-actions">
          <ImportPanel
            projectId={project.project_id}
            currentImage={currentImage}
            onImported={importFinished}
            onMaskImported={async () => { if (currentId) await loadMask(currentId); await reloadProject(); }}
            onError={showError}
          />
          <ExportPanel
            projectId={project.project_id}
            currentImageId={currentId || undefined}
            selectedIds={exportSelection}
            onError={showError}
          />
        </section>
      </aside>

      <section className="editor-area">
        {currentImage && mask && !loading ? (
          <>
            <CanvasEditor
              imageUrl={api.imageUrl(project.project_id, currentImage.image_id)}
              width={currentImage.width}
              height={currentImage.height}
              mask={mask}
              classes={project.classes}
              selectedClassId={selectedClassId}
              tool={tool}
              brushSize={brushSize}
              opacity={opacity}
              maskVisible={maskVisible}
              viewCommand={viewCommand}
              onPreview={setMask}
              onCommit={commit}
              onMessage={showError}
            />
            <footer className="image-footer">
              <div className="navigation-buttons">
                <button disabled={currentIndex <= 0} onClick={() => void selectImage(project.images[currentIndex - 1].image_id)}>← Previous</button>
                <span>{currentIndex + 1} of {project.images.length}</span>
                <button disabled={currentIndex < 0 || currentIndex + 1 >= project.images.length} onClick={() => void selectImage(project.images[currentIndex + 1].image_id)}>Next →</button>
              </div>
              <label className="complete-control">
                <input
                  type="checkbox"
                  checked={currentImage.status === "completed"}
                  onChange={(event) => void updateStatus(event.target.checked ? "completed" : (mask.some((value) => value > 0) ? "in_progress" : "not_started"))}
                />
                Mark image completed
              </label>
              <span>{currentImage.relative_path} · {currentImage.width} × {currentImage.height}px</span>
            </footer>
          </>
        ) : loading ? (
          <div className="empty-editor"><div className="spinner" /><h2>Loading image…</h2></div>
        ) : (
          <div className="empty-editor"><div className="empty-glyph">▧</div><h2>No images yet</h2><p>Use “Import images” in the sidebar to add files, folders, ZIP archives, or a local path.</p></div>
        )}
      </section>
      {error && <div className="toast error" role="alert"><button onClick={() => setError("")}>×</button>{error}</div>}
      {notice && <div className="toast notice" role="status"><button onClick={() => setNotice("")}>×</button>{notice}</div>}
    </main>
  );
}

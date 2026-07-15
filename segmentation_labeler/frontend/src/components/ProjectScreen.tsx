import { useEffect, useState, type FormEvent } from "react";
import { api } from "../api";
import type { Project, ProjectSummary } from "../types";

interface DraftClass {
  name: string;
  color: string;
}

interface Props {
  onOpen: (project: Project) => void;
}

export function ProjectScreen({ onOpen }: Props) {
  const [recent, setRecent] = useState<ProjectSummary[]>([]);
  const [name, setName] = useState("");
  const [storagePath, setStoragePath] = useState("");
  const [openPath, setOpenPath] = useState("");
  const [classes, setClasses] = useState<DraftClass[]>([
    { name: "Foreground", color: "#EF4444" },
  ]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.listProjects().then(setRecent).catch(() => setRecent([]));
  }, []);

  const create = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      onOpen(
        await api.createProject({
          name,
          storage_path: storagePath || undefined,
          classes,
        }),
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not create project");
    } finally {
      setBusy(false);
    }
  };

  const open = async (path: string) => {
    setBusy(true);
    setError("");
    try {
      onOpen(await api.openProject(path));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not open project");
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="opening-screen">
      <section className="brand-panel">
        <div className="brand-mark">SL</div>
        <p className="eyebrow">LOCAL ANNOTATION WORKSPACE</p>
        <h1>Segmentation Labeler</h1>
        <p className="lede">
          Paint precise, class-indexed masks without sending images outside this computer.
        </p>
        <div className="feature-line"><span>01</span> Pixel-aligned brush and polygon tools</div>
        <div className="feature-line"><span>02</span> Automatic, resumable project saves</div>
        <div className="feature-line"><span>03</span> Reproducible mask exports with metadata</div>
      </section>

      <section className="opening-actions">
        <div className="opening-card">
          <p className="eyebrow">NEW PROJECT</p>
          <h2>Start a labeling set</h2>
          <form onSubmit={create}>
            <label>
              Project name
              <input
                required
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="e.g. Wound study"
              />
            </label>
            <label>
              Project directory <span className="muted">(optional)</span>
              <input
                value={storagePath}
                onChange={(event) => setStoragePath(event.target.value)}
                placeholder="Uses ~/.segmentation_labeler when blank"
              />
            </label>
            <fieldset>
              <legend>Segmentation classes</legend>
              {classes.map((item, index) => (
                <div className="class-draft" key={index}>
                  <input
                    aria-label={`Class ${index + 1} color`}
                    type="color"
                    value={item.color}
                    onChange={(event) =>
                      setClasses((current) =>
                        current.map((entry, entryIndex) =>
                          entryIndex === index ? { ...entry, color: event.target.value } : entry,
                        ),
                      )
                    }
                  />
                  <input
                    aria-label={`Class ${index + 1} name`}
                    required
                    value={item.name}
                    onChange={(event) =>
                      setClasses((current) =>
                        current.map((entry, entryIndex) =>
                          entryIndex === index ? { ...entry, name: event.target.value } : entry,
                        ),
                      )
                    }
                  />
                  <button
                    className="icon-button"
                    type="button"
                    title="Remove class"
                    disabled={classes.length === 1}
                    onClick={() => setClasses((current) => current.filter((_, i) => i !== index))}
                  >
                    ×
                  </button>
                </div>
              ))}
              <button
                className="text-button"
                type="button"
                onClick={() => setClasses((current) => [...current, { name: "", color: "#3B82F6" }])}
              >
                + Add class
              </button>
            </fieldset>
            <button className="primary-button" disabled={busy} type="submit">
              {busy ? "Working…" : "Create project"}
            </button>
          </form>
        </div>

        <div className="opening-card compact-card">
          <p className="eyebrow">RESUME</p>
          <h2>Open an existing project</h2>
          <div className="inline-form">
            <input
              aria-label="Existing project directory"
              value={openPath}
              onChange={(event) => setOpenPath(event.target.value)}
              placeholder="Path containing project.sqlite"
            />
            <button disabled={!openPath || busy} onClick={() => void open(openPath)}>
              Open
            </button>
          </div>
          {recent.length > 0 && (
            <div className="recent-list">
              <span className="muted small">RECENT PROJECTS</span>
              {recent.slice(0, 4).map((item) => (
                <button key={item.project_id} onClick={() => void open(item.storage_path)}>
                  <strong>{item.name}</strong>
                  <span>{item.storage_path}</span>
                </button>
              ))}
            </div>
          )}
        </div>
        {error && <div className="error-banner" role="alert">{error}</div>}
      </section>
    </main>
  );
}

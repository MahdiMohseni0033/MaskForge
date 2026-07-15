import { useRef, useState } from "react";
import { api } from "../api";
import type { ExportResult, ImportResult, ProjectImage } from "../types";

interface ImportProps {
  projectId: string;
  currentImage: ProjectImage | undefined;
  onImported: (result: ImportResult) => Promise<void>;
  onMaskImported: () => Promise<void>;
  onError: (message: string) => void;
}

export function ImportPanel({
  projectId,
  currentImage,
  onImported,
  onMaskImported,
  onError,
}: ImportProps) {
  const folderRef = useRef<HTMLInputElement>(null);
  const [localPath, setLocalPath] = useState("");
  const [busy, setBusy] = useState(false);

  const upload = async (files: File[]) => {
    if (!files.length) return;
    setBusy(true);
    try {
      await onImported(await api.importFiles(projectId, files));
    } catch (caught) {
      onError(caught instanceof Error ? caught.message : "Import failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <details className="action-panel">
      <summary>Import images</summary>
      <p>Raster images, 2D NPY, DICOM, or ZIP archives.</p>
      <label className="file-button">
        {busy ? "Importing…" : "Choose file(s) / ZIP"}
        <input
          type="file"
          multiple
          disabled={busy}
          accept=".png,.jpg,.jpeg,.tif,.tiff,.bmp,.webp,.npy,.dcm,.zip"
          onChange={(event) => void upload(Array.from(event.target.files || []))}
        />
      </label>
      <label className="file-button secondary">
        Choose browser folder
        <input
          ref={folderRef}
          type="file"
          multiple
          {...({ webkitdirectory: "", directory: "" } as Record<string, string>)}
          onChange={(event) => void upload(Array.from(event.target.files || []))}
        />
      </label>
      <div className="stacked-form">
        <input
          aria-label="Local server directory"
          value={localPath}
          onChange={(event) => setLocalPath(event.target.value)}
          placeholder="Local directory on this machine"
        />
        <button
          disabled={!localPath || busy}
          onClick={async () => {
            setBusy(true);
            try {
              await onImported(await api.importDirectory(projectId, localPath));
            } catch (caught) {
              onError(caught instanceof Error ? caught.message : "Directory import failed");
            } finally {
              setBusy(false);
            }
          }}
        >
          Import local path
        </button>
      </div>
      {currentImage && (
        <label className="file-button tertiary" title="Mask dimensions and IDs are validated without resizing">
          Import mask for current image
          <input
            type="file"
            accept=".png,.tif,.tiff,.npy"
            onChange={async (event) => {
              const file = event.target.files?.[0];
              if (!file) return;
              try {
                await api.importMask(projectId, currentImage.image_id, file);
                await onMaskImported();
              } catch (caught) {
                onError(caught instanceof Error ? caught.message : "Mask import failed");
              }
            }}
          />
        </label>
      )}
    </details>
  );
}

interface ExportProps {
  projectId: string;
  currentImageId?: string;
  selectedIds: string[];
  onError: (message: string) => void;
}

export function ExportPanel({ projectId, currentImageId, selectedIds, onError }: ExportProps) {
  const [scope, setScope] = useState<"current" | "selected" | "all">("all");
  const [format, setFormat] = useState<"png" | "tiff" | "npy">("png");
  const [directory, setDirectory] = useState("");
  const [result, setResult] = useState<ExportResult | null>(null);
  const [busy, setBusy] = useState(false);

  return (
    <details className="action-panel">
      <summary>Export masks</summary>
      <label>
        Images
        <select value={scope} onChange={(event) => setScope(event.target.value as typeof scope)}>
          <option value="all">All images</option>
          <option value="current">Current image</option>
          <option value="selected">Checked images ({selectedIds.length})</option>
        </select>
      </label>
      <label>
        Format
        <select value={format} onChange={(event) => setFormat(event.target.value as typeof format)}>
          <option value="png">Indexed PNG (IDs ≤ 255)</option>
          <option value="tiff">16-bit TIFF</option>
          <option value="npy">NumPy uint16</option>
        </select>
      </label>
      <label>
        Export parent directory <span className="muted">(optional)</span>
        <input value={directory} onChange={(event) => setDirectory(event.target.value)} placeholder="Defaults inside project" />
      </label>
      <p>
        Batch exports include masks, <code>classes.json</code>, and a readable
        <code> class_summary.txt</code> report in one ZIP download.
      </p>
      <button
        className="download-current-button"
        disabled={busy || !currentImageId}
        onClick={async () => {
          if (!currentImageId) return;
          setBusy(true);
          try {
            await api.downloadCurrentMask(projectId, currentImageId, format);
          } catch (caught) {
            onError(caught instanceof Error ? caught.message : "Mask download failed");
          } finally {
            setBusy(false);
          }
        }}
      >
        Download current mask
      </button>
      <button
        className="primary-button"
        disabled={busy || (scope === "current" && !currentImageId) || (scope === "selected" && !selectedIds.length)}
        onClick={async () => {
          setBusy(true);
          setResult(null);
          try {
            setResult(
              await api.exportMasks(projectId, {
                scope,
                format,
                image_ids: selectedIds,
                current_image_id: currentImageId,
                export_directory: directory || undefined,
              }),
            );
          } catch (caught) {
            onError(caught instanceof Error ? caught.message : "Export failed");
          } finally {
            setBusy(false);
          }
        }}
      >
        {busy ? "Working…" : "Export batch"}
      </button>
      {result && (
        <div className="success-message">
          <p>Exported {result.images.length} mask(s). A server-side copy is at<br /><code>{result.output_directory}</code></p>
          <a className="download-link" href={result.download_url} download={result.archive_name}>
            Download export ZIP
          </a>
        </div>
      )}
    </details>
  );
}

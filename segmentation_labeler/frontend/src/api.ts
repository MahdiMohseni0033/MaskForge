import type {
  AnnotationStatus,
  ExportResult,
  ImportResult,
  Project,
  ProjectSummary,
  SegmentationClass,
} from "./types";

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`;
    try {
      const body = (await response.json()) as { detail?: string | Array<{ msg: string }> };
      message = Array.isArray(body.detail)
        ? body.detail.map((item) => item.msg).join("; ")
        : body.detail || message;
    } catch {
      // Keep the HTTP status when the response is not JSON.
    }
    throw new Error(message);
  }
  return (await response.json()) as T;
}

async function download(url: string): Promise<void> {
  const response = await fetch(url);
  if (!response.ok) {
    let message = `Download failed (${response.status})`;
    try {
      const body = (await response.json()) as { detail?: string };
      message = body.detail || message;
    } catch {
      // Keep the HTTP status when the response is not JSON.
    }
    throw new Error(message);
  }
  const disposition = response.headers.get("Content-Disposition") || "";
  const match = disposition.match(/filename="?([^";]+)"?/i);
  const blobUrl = URL.createObjectURL(await response.blob());
  const anchor = document.createElement("a");
  anchor.href = blobUrl;
  anchor.download = match?.[1] || "mask";
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(blobUrl), 1000);
}

const json = (value: unknown): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(value),
});

export const api = {
  listProjects: () => request<ProjectSummary[]>("/api/projects"),
  getProject: (projectId: string) => request<Project>(`/api/projects/${projectId}`),
  createProject: (payload: {
    name: string;
    storage_path?: string;
    classes: Array<{ name: string; color: string; class_id?: number }>;
  }) => request<Project>("/api/projects", json(payload)),
  openProject: (storagePath: string) =>
    request<Project>("/api/projects/open", json({ storage_path: storagePath })),
  updateSettings: (
    projectId: string,
    value: { last_image_id?: string; overlay_opacity?: number; mask_visible?: boolean },
  ) =>
    request<Project>(`/api/projects/${projectId}`, {
      ...json(value),
      method: "PATCH",
    }),
  addClass: (projectId: string, value: { name: string; color: string }) =>
    request<SegmentationClass>(`/api/projects/${projectId}/classes`, json(value)),
  updateClass: (
    projectId: string,
    classId: number,
    value: { name: string; color: string },
  ) =>
    request<SegmentationClass>(`/api/projects/${projectId}/classes/${classId}`, {
      ...json(value),
      method: "PATCH",
    }),
  deleteClass: (projectId: string, classId: number, replace: boolean) =>
    request<{ deleted: number }>(
      `/api/projects/${projectId}/classes/${classId}?replace_with_background=${replace}`,
      { method: "DELETE" },
    ),
  importFiles: async (projectId: string, files: File[]): Promise<ImportResult> => {
    const form = new FormData();
    files.forEach((file) => {
      form.append("files", file);
      form.append("relative_paths", file.webkitRelativePath || file.name);
    });
    return request(`/api/projects/${projectId}/images/upload`, { method: "POST", body: form });
  },
  importDirectory: (projectId: string, directory: string) =>
    request<ImportResult>(
      `/api/projects/${projectId}/images/import-directory`,
      json({ directory }),
    ),
  imageUrl: (projectId: string, imageId: string) =>
    `/api/projects/${projectId}/images/${imageId}/source`,
  fetchMask: async (projectId: string, imageId: string): Promise<Uint16Array> => {
    const response = await fetch(`/api/projects/${projectId}/images/${imageId}/mask`);
    if (!response.ok) throw new Error(`Could not load mask (${response.status})`);
    const data = await response.arrayBuffer();
    return new Uint16Array(data.slice(0));
  },
  saveMask: async (projectId: string, imageId: string, mask: Uint16Array) => {
    const raw = new Uint8Array(mask.byteLength);
    raw.set(new Uint8Array(mask.buffer, mask.byteOffset, mask.byteLength));
    let body: BodyInit = raw;
    const headers: Record<string, string> = { "Content-Type": "application/octet-stream" };
    if (raw.byteLength > 1024 && typeof CompressionStream !== "undefined") {
      const stream = new Blob([raw.buffer]).stream().pipeThrough(new CompressionStream("gzip"));
      const compressed = await new Response(stream).arrayBuffer();
      if (compressed.byteLength < raw.byteLength) {
        body = compressed;
        headers["Content-Encoding"] = "gzip";
      }
    }
    return request<{ saved: boolean; modified_at: string; status: AnnotationStatus }>(
      `/api/projects/${projectId}/images/${imageId}/mask`,
      {
        method: "PUT",
        headers,
        body,
      },
    );
  },
  importMask: async (projectId: string, imageId: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<{ imported: boolean; status: AnnotationStatus }>(
      `/api/projects/${projectId}/images/${imageId}/mask/import`,
      { method: "POST", body: form },
    );
  },
  setStatus: (projectId: string, imageId: string, status: AnnotationStatus) =>
    request<{ image_id: string; status: AnnotationStatus; modified_at: string }>(
      `/api/projects/${projectId}/images/${imageId}`,
      { ...json({ status }), method: "PATCH" },
    ),
  downloadCurrentMask: (
    projectId: string,
    imageId: string,
    format: "png" | "tiff" | "npy",
  ) =>
    download(
      `/api/projects/${projectId}/images/${imageId}/mask/download?format=${format}`,
    ),
  exportMasks: (
    projectId: string,
    value: {
      scope: "current" | "selected" | "all";
      image_ids: string[];
      current_image_id?: string;
      format: "png" | "tiff" | "npy";
      export_directory?: string;
    },
  ) => request<ExportResult>(`/api/projects/${projectId}/export`, json(value)),
};

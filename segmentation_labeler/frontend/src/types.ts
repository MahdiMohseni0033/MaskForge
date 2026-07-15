export type AnnotationStatus = "not_started" | "in_progress" | "completed";
export type Tool = "brush" | "eraser" | "polygon" | "pan";
export type SaveStatus = "saved" | "saving" | "failed";

export interface SegmentationClass {
  class_id: number;
  name: string;
  color: string;
}

export interface ProjectImage {
  image_id: string;
  source_name: string;
  relative_path: string;
  width: number;
  height: number;
  status: AnnotationStatus;
  modified_at: string;
}

export interface Project {
  project_id: string;
  name: string;
  storage_path: string;
  created_at: string;
  modified_at: string;
  last_image_id: string | null;
  overlay_opacity: number;
  mask_visible: boolean;
  classes: SegmentationClass[];
  images: ProjectImage[];
}

export interface ProjectSummary {
  project_id: string;
  name: string;
  storage_path: string;
  modified_at: string;
}

export interface ImportResult {
  imported: Array<{ image_id: string; relative_path: string; width: number; height: number }>;
  errors: Array<{ file: string; error: string }>;
}

export interface ExportResult {
  output_directory: string;
  metadata_file: string;
  summary_file: string;
  archive_name: string;
  download_url: string;
  images: Array<{
    image_id: string;
    source: string;
    mask: string;
    width: number;
    height: number;
    class_pixel_counts: Record<string, number>;
  }>;
}

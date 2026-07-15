import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { Project, SegmentationClass, Tool } from "../src/types";

const apiMock = vi.hoisted(() => ({
  fetchMask: vi.fn(),
  saveMask: vi.fn(),
  getProject: vi.fn(),
  updateSettings: vi.fn(),
  setStatus: vi.fn(),
  imageUrl: vi.fn((_projectId: string, imageId: string) => `/source/${imageId}`),
  updateClass: vi.fn(),
  addClass: vi.fn(),
  deleteClass: vi.fn(),
}));

vi.mock("../src/api", () => ({ api: apiMock }));
vi.mock("../src/components/ImportExport", () => ({
  ImportPanel: () => <div>Import panel</div>,
  ExportPanel: () => <div>Export panel</div>,
}));
vi.mock("../src/components/CanvasEditor", () => ({
  CanvasEditor: ({
    mask,
    selectedClassId,
    tool,
    onCommit,
  }: {
    mask: Uint16Array;
    selectedClassId: number;
    tool: Tool;
    classes: SegmentationClass[];
    onCommit: (next: Uint16Array) => void;
  }) => (
    <div data-testid="annotation-canvas">
      <span>Canvas tool {tool}, class {selectedClassId}</span>
      <button onClick={() => {
        const next = new Uint16Array(mask);
        next[0] = next[0] === selectedClassId ? (selectedClassId === 1 ? 2 : 1) : selectedClassId;
        onCommit(next);
      }}>Paint test stroke</button>
    </div>
  ),
}));

import { Workspace } from "../src/components/Workspace";

const project: Project = {
  project_id: "project-1",
  name: "Study",
  storage_path: "/tmp/study",
  created_at: "2026-01-01T00:00:00Z",
  modified_at: "2026-01-01T00:00:00Z",
  last_image_id: "image-1",
  overlay_opacity: 0.45,
  mask_visible: true,
  classes: [
    { class_id: 1, name: "Tissue", color: "#EF4444" },
    { class_id: 2, name: "Instrument", color: "#3B82F6" },
  ],
  images: [
    { image_id: "image-1", source_name: "one.png", relative_path: "one.png", width: 4, height: 3, status: "not_started", modified_at: "now" },
    { image_id: "image-2", source_name: "two.png", relative_path: "nested/two.png", width: 4, height: 3, status: "in_progress", modified_at: "now" },
  ],
};

describe("Workspace", () => {
  beforeEach(() => {
    apiMock.fetchMask.mockResolvedValue(new Uint16Array(12));
    apiMock.saveMask.mockResolvedValue({ saved: true, modified_at: "later", status: "in_progress" });
    apiMock.getProject.mockResolvedValue(project);
    apiMock.updateSettings.mockResolvedValue(project);
    apiMock.setStatus.mockResolvedValue({ image_id: "image-1", status: "completed", modified_at: "later" });
  });

  it("selects images, classes, tools, and navigates", async () => {
    const user = userEvent.setup();
    render(<Workspace initialProject={project} onClose={vi.fn()} />);
    await screen.findByTestId("annotation-canvas");
    expect(screen.getByText("Canvas tool brush, class 1")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Instrument/ }));
    expect(screen.getByText("Canvas tool brush, class 2")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Polygon/ }));
    expect(screen.getByText("Canvas tool polygon, class 2")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /two.png/ }));
    await waitFor(() => expect(apiMock.fetchMask).toHaveBeenLastCalledWith("project-1", "image-2"));
    expect(apiMock.updateSettings).toHaveBeenCalledWith("project-1", { last_image_id: "image-2" });
    expect(screen.getByText("2 of 2")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Previous/ }));
    await waitFor(() => expect(apiMock.fetchMask).toHaveBeenLastCalledWith("project-1", "image-1"));
  });

  it("autosaves logical edits and supports undo and redo", async () => {
    const user = userEvent.setup();
    let resolveSave: ((value: { saved: true; modified_at: string; status: "in_progress" }) => void) | undefined;
    apiMock.saveMask.mockImplementationOnce(
      () => new Promise((resolve) => { resolveSave = resolve; }),
    );
    render(<Workspace initialProject={project} onClose={vi.fn()} />);
    await screen.findByTestId("annotation-canvas");
    await user.click(screen.getByRole("button", { name: "Paint test stroke" }));
    expect(screen.getByText("Saving")).toBeInTheDocument();
    resolveSave?.({ saved: true, modified_at: "later", status: "in_progress" });
    await waitFor(() => expect(screen.getByText("Saved")).toBeInTheDocument());
    expect(apiMock.saveMask).toHaveBeenCalledOnce();

    await user.click(screen.getByRole("button", { name: /Undo/ }));
    await waitFor(() => expect(apiMock.saveMask).toHaveBeenCalledTimes(2));
    await user.click(screen.getByRole("button", { name: /Redo/ }));
    await waitFor(() => expect(apiMock.saveMask).toHaveBeenCalledTimes(3));
  });

  it("asks for confirmation before clear and reset", async () => {
    const user = userEvent.setup();
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
    render(<Workspace initialProject={project} onClose={vi.fn()} />);
    await screen.findByTestId("annotation-canvas");
    await user.click(screen.getByRole("button", { name: "Clear class" }));
    await user.click(screen.getByRole("button", { name: "Reset" }));
    expect(confirm).toHaveBeenCalledTimes(2);
    expect(apiMock.saveMask).not.toHaveBeenCalled();
  });

  it("coalesces queued edits and navigates after only the newest mask is saved", async () => {
    const user = userEvent.setup();
    const resolvers: Array<(
      value: { saved: true; modified_at: string; status: "in_progress" },
    ) => void> = [];
    apiMock.saveMask.mockImplementation(
      () => new Promise((resolve) => { resolvers.push(resolve); }),
    );
    render(<Workspace initialProject={project} onClose={vi.fn()} />);
    await screen.findByTestId("annotation-canvas");

    const paint = screen.getByRole("button", { name: "Paint test stroke" });
    await user.click(paint);
    await user.click(paint);
    await user.click(paint);
    expect(apiMock.saveMask).toHaveBeenCalledTimes(1);

    resolvers[0]({ saved: true, modified_at: "first", status: "in_progress" });
    await waitFor(() => expect(apiMock.saveMask).toHaveBeenCalledTimes(2));
    await user.click(screen.getByRole("button", { name: /Next/ }));
    expect(screen.getByText("1 of 2")).toBeInTheDocument();

    resolvers[1]({ saved: true, modified_at: "latest", status: "in_progress" });
    await waitFor(() => expect(screen.getByText("2 of 2")).toBeInTheDocument());
    expect(apiMock.saveMask).toHaveBeenCalledTimes(2);
  });
});

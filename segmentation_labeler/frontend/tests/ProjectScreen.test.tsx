import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { Project } from "../src/types";

const apiMock = vi.hoisted(() => ({
  listProjects: vi.fn(),
  createProject: vi.fn(),
  openProject: vi.fn(),
}));

vi.mock("../src/api", () => ({ api: apiMock }));

import { ProjectScreen } from "../src/components/ProjectScreen";

const project: Project = {
  project_id: "project-1",
  name: "Study",
  storage_path: "/tmp/study",
  created_at: "2026-01-01T00:00:00Z",
  modified_at: "2026-01-01T00:00:00Z",
  last_image_id: null,
  overlay_opacity: 0.45,
  mask_visible: true,
  classes: [{ class_id: 1, name: "Tissue", color: "#EF4444" }],
  images: [],
};

describe("ProjectScreen", () => {
  beforeEach(() => {
    apiMock.listProjects.mockResolvedValue([]);
    apiMock.createProject.mockResolvedValue(project);
    apiMock.openProject.mockResolvedValue(project);
  });

  it("creates a named project with multiple class definitions", async () => {
    const user = userEvent.setup();
    const onOpen = vi.fn();
    render(<ProjectScreen onOpen={onOpen} />);

    await user.type(screen.getByLabelText("Project name"), "Study");
    await user.clear(screen.getByLabelText("Class 1 name"));
    await user.type(screen.getByLabelText("Class 1 name"), "Tissue");
    await user.click(screen.getByRole("button", { name: "+ Add class" }));
    await user.type(screen.getByLabelText("Class 2 name"), "Lesion");
    await user.click(screen.getByRole("button", { name: "Create project" }));

    await waitFor(() => expect(onOpen).toHaveBeenCalledWith(project));
    expect(apiMock.createProject).toHaveBeenCalledWith(
      expect.objectContaining({
        name: "Study",
        classes: [
          expect.objectContaining({ name: "Tissue" }),
          expect.objectContaining({ name: "Lesion" }),
        ],
      }),
    );
  });

  it("opens a project by its directory", async () => {
    const user = userEvent.setup();
    const onOpen = vi.fn();
    render(<ProjectScreen onOpen={onOpen} />);
    await user.type(screen.getByLabelText("Existing project directory"), "/tmp/study");
    await user.click(screen.getByRole("button", { name: "Open" }));
    await waitFor(() => expect(apiMock.openProject).toHaveBeenCalledWith("/tmp/study"));
    expect(onOpen).toHaveBeenCalledWith(project);
  });
});


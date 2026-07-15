import { useState } from "react";
import type { Project } from "./types";
import { ProjectScreen } from "./components/ProjectScreen";
import { Workspace } from "./components/Workspace";

export default function App() {
  const [project, setProject] = useState<Project | null>(null);
  return project ? (
    <Workspace initialProject={project} onClose={() => setProject(null)} />
  ) : (
    <ProjectScreen onOpen={setProject} />
  );
}


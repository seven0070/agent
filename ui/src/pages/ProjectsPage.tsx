import React from "react";
import { UnavailableState } from "../components/ui";

export const ProjectsPage: React.FC = () => {
  return (
    <section className="page">
      <p className="eyebrow">Organization</p>
      <h1>Projects</h1>
      <UnavailableState title="Projects API NOT EXPOSED">
        The backend has sessions, workspace files, and plans. It does not expose a first-class projects resource.
        No project list is invented here.
      </UnavailableState>
    </section>
  );
};

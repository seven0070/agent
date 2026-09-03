import React from "react";
import { PageHeader, UnavailableState } from "../components/ui";

export const ProjectsPage: React.FC = () => {
  return (
    <section className="page">
      <PageHeader eyebrow="Organization" title="Projects">
        Projects are not a backend resource. This page stays honest about that.
      </PageHeader>
      <UnavailableState title="Projects API NOT EXPOSED">
        The backend has sessions, workspace files, and plans. It does not expose a first-class projects resource.
        No project list is invented here.
      </UnavailableState>
    </section>
  );
};

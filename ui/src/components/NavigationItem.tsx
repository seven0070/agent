import React from "react";
import { sectionHref, type SectionId } from "../lib/navigation";

export const NavigationItem: React.FC<{
  id: SectionId;
  label: string;
  active: boolean;
  onSelect: (id: SectionId) => void;
}> = ({ id, label, active, onSelect }) => {
  return (
    <a
      className={`nav-item${active ? " is-active" : ""}`}
      href={sectionHref(id)}
      aria-current={active ? "page" : undefined}
      onClick={(event) => {
        event.preventDefault();
        onSelect(id);
      }}
    >
      {label}
    </a>
  );
};

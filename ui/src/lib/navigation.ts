export const PRIMARY_SECTIONS = [
  { id: "agent", label: "Agent" },
  { id: "workspace", label: "Workspace" },
  { id: "tasks", label: "Tasks" },
  { id: "projects", label: "Projects" },
  { id: "files", label: "Files" },
  { id: "memory", label: "Memory" },
  { id: "tools", label: "Tools" },
  { id: "jcode", label: "Jcode" },
  { id: "models", label: "Models" },
  { id: "evaluation", label: "Evaluation" },
  { id: "evolution", label: "Evolution" },
  { id: "security", label: "Security" },
] as const;

export const FOOTER_SECTIONS = [{ id: "settings", label: "Settings" }] as const;

export const SECTIONS = [...PRIMARY_SECTIONS, ...FOOTER_SECTIONS] as const;

export type SectionId = (typeof SECTIONS)[number]["id"];

export const DEFAULT_SECTION: SectionId = "agent";

const SECTION_IDS = new Set<string>(SECTIONS.map((section) => section.id));

export function isSectionId(value: string): value is SectionId {
  return SECTION_IDS.has(value);
}

export function parseSectionHash(hash: string): SectionId {
  const raw = hash.replace(/^#\/?/, "").split("/")[0]?.trim().toLowerCase() ?? "";
  return isSectionId(raw) ? raw : DEFAULT_SECTION;
}

export function sectionHref(id: SectionId): string {
  return `#/${id}`;
}

export function sectionLabel(id: SectionId): string {
  return SECTIONS.find((section) => section.id === id)?.label ?? "Agent";
}

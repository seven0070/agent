import React from "react";
import { ComingSoon } from "../components/ComingSoon";
import { sectionLabel, type SectionId } from "../lib/navigation";

export const ComingSoonPage: React.FC<{ section: SectionId }> = ({ section }) => {
  return <ComingSoon title={sectionLabel(section)} />;
};

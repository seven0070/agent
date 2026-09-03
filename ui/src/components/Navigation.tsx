import React, { useRef } from "react";
import { FOOTER_SECTIONS, PRIMARY_SECTIONS, type SectionId } from "../lib/navigation";
import { useNavigation } from "../state/NavigationContext";
import { NavigationItem } from "./NavigationItem";

export const Navigation: React.FC = () => {
  const { section, navigate } = useNavigation();
  const navRef = useRef<HTMLElement>(null);
  const items: SectionId[] = [...PRIMARY_SECTIONS.map((item) => item.id), ...FOOTER_SECTIONS.map((item) => item.id)];

  const onKeyDown = (event: React.KeyboardEvent<HTMLElement>) => {
    if (event.key !== "ArrowDown" && event.key !== "ArrowUp" && event.key !== "Home" && event.key !== "End") {
      return;
    }
    event.preventDefault();
    const current = items.indexOf(section);
    let next = current;
    if (event.key === "ArrowDown") next = Math.min(items.length - 1, current + 1);
    if (event.key === "ArrowUp") next = Math.max(0, current - 1);
    if (event.key === "Home") next = 0;
    if (event.key === "End") next = items.length - 1;
    const target = items[next];
    if (!target) return;
    navigate(target);
    navRef.current?.querySelector<HTMLAnchorElement>(`a[href="#/${target}"]`)?.focus();
  };

  return (
    <nav ref={navRef} className="app-sidebar__nav" aria-label="Primary" onKeyDown={onKeyDown}>
      <div className="app-sidebar__group">
        {PRIMARY_SECTIONS.map((item) => (
          <NavigationItem
            key={item.id}
            id={item.id}
            label={item.label}
            active={section === item.id}
            onSelect={navigate}
          />
        ))}
      </div>
      <div className="app-sidebar__spacer" />
      <div className="app-sidebar__group">
        {FOOTER_SECTIONS.map((item) => (
          <NavigationItem
            key={item.id}
            id={item.id}
            label={item.label}
            active={section === item.id}
            onSelect={navigate}
          />
        ))}
      </div>
    </nav>
  );
};

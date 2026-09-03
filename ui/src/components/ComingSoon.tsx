import React from "react";

export const ComingSoon: React.FC<{ title: string }> = ({ title }) => {
  return (
    <section className="coming-soon">
      <p className="eyebrow">Not implemented</p>
      <h1>{title}</h1>
      <p className="coming-soon__body">Coming in next GUI phase.</p>
      <p className="muted">
        This section is reserved in the desktop shell. It does not display live {title.toLowerCase()} data
        yet.
      </p>
    </section>
  );
};

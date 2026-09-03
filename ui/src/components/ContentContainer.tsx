import React from "react";

export const ContentContainer: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <main className="content-container" id="main-content">
      {children}
    </main>
  );
};

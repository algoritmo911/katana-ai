import React, { createContext, useState } from 'react';

export const CommandContext = createContext(null);

export const CommandProvider = ({ children }) => {
  const [commands, setCommands] = useState([]);

  return (
    <CommandContext.Provider value={{ commands, setCommands }}>
      {children}
    </CommandContext.Provider>
  );
};
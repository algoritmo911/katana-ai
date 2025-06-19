import React, { createContext, useContext, useReducer, useEffect, ReactNode } from 'react';

// --- Interfaces and Types ---
export interface Message {
  id: number;
  role: 'user' | 'katana' | 'system';
  text: string;
  timestamp?: string;
}

export interface ServiceConnection {
  id: string;
  name: string;
  status: 'connected' | 'disconnected' | 'error' | 'pending';
}

export type KatanaMode = 'Default' | 'Integrator' | 'Focus' | 'Archivist' | 'SilentMonk';

interface KatanaState {
  messages: Message[];
  nextMessageId: number;
  connectedServices: ServiceConnection[];
  currentMode: KatanaMode;
  lastKatanaAction: string | null;
}

type Action =
  | { type: 'ADD_MESSAGE'; payload: Message }
  | { type: 'LOAD_MESSAGES'; payload: Message[] }
  | { type: 'SET_KATANA_MODE'; payload: KatanaMode }
  | { type: 'ADD_CONNECTED_SERVICE'; payload: ServiceConnection }
  | { type: 'UPDATE_SERVICE_STATUS'; payload: { id: string; status: ServiceConnection['status'] } }
  | { type: 'SET_LAST_ACTION'; payload: string | null }
  | { type: 'INCREMENT_NEXT_ID' ; payload?: number };

const LOCAL_STORAGE_MESSAGES_KEY = 'katana_chat_history_v2';

// --- Initial State ---
const initialState: KatanaState = {
  messages: [],
  nextMessageId: 1,
  connectedServices: [
    { id: 'gmail', name: 'Gmail', status: 'disconnected' },
    { id: 'github', name: 'GitHub', status: 'connected' },
  ],
  currentMode: 'Default',
  lastKatanaAction: 'Katana context initialized.', // Changed from "Katana initialized"
};

// --- Reducer ---
const katanaReducer = (state: KatanaState, action: Action): KatanaState => {
  switch (action.type) {
    case 'LOAD_MESSAGES':
      // Ensure IDs are numbers and find max correctly
      const numericIds = action.payload.map(m => Number(m.id)).filter(id => !isNaN(id));
      return {
        ...state,
        messages: action.payload,
        nextMessageId: numericIds.length > 0
                       ? Math.max(...numericIds) + 1
                       : Date.now(),
      };
    case 'ADD_MESSAGE':
      const newMessageId = action.payload.id || state.nextMessageId; // Use provided ID or next from state
      const newMessage = { ...action.payload, id: newMessageId };
      const newNextId = Math.max(state.nextMessageId, newMessage.id) + 1;
      return {
        ...state,
        messages: [...state.messages, newMessage],
        nextMessageId: newNextId,
        lastKatanaAction: newMessage.role === 'katana' ? `Responded: ${newMessage.text.substring(0,30)}...` : `User said: ${newMessage.text.substring(0,30)}...`,
      };
    case 'INCREMENT_NEXT_ID':
      return { ...state, nextMessageId: state.nextMessageId + (action.payload || 1) };
    case 'SET_KATANA_MODE':
      return { ...state, currentMode: action.payload, lastKatanaAction: `Mode changed to: ${action.payload}` };
    case 'ADD_CONNECTED_SERVICE':
      if (state.connectedServices.find(s => s.id === action.payload.id)) return state;
      return { ...state, connectedServices: [...state.connectedServices, action.payload] };
    case 'UPDATE_SERVICE_STATUS':
      return {
        ...state,
        connectedServices: state.connectedServices.map(s =>
          s.id === action.payload.id ? { ...s, status: action.payload.status } : s
        ),
        lastKatanaAction: `Service ${action.payload.id} status updated to ${action.payload.status}`
      };
    case 'SET_LAST_ACTION':
      return { ...state, lastKatanaAction: action.payload };
    default:
      // Should not happen if types are correct, but as a fallback:
      // const exhaustiveCheck: never = action;
      return state;
  }
};

// --- Context Definition ---
interface KatanaContextProps {
  state: KatanaState;
  dispatch: React.Dispatch<Action>;
}

const KatanaContext = createContext<KatanaContextProps | undefined>(undefined);

// --- Provider Component ---
interface KatanaProviderProps {
  children: ReactNode;
}

export const KatanaProvider: React.FC<KatanaProviderProps> = ({ children }) => {
  const [state, dispatch] = useReducer(katanaReducer, initialState);

  useEffect(() => {
    const storedMessages = localStorage.getItem(LOCAL_STORAGE_MESSAGES_KEY);
    if (storedMessages) {
      try {
        const parsedMessages: Message[] = JSON.parse(storedMessages);
        if (Array.isArray(parsedMessages) && parsedMessages.every(m => typeof m.id === 'number')) {
            dispatch({ type: 'LOAD_MESSAGES', payload: parsedMessages });
        } else {
            console.warn("KatanaContext: Stored messages not an array or IDs not numbers, initializing.");
            localStorage.removeItem(LOCAL_STORAGE_MESSAGES_KEY);
            const welcomeId = Date.now();
            dispatch({ type: 'LOAD_MESSAGES', payload: [{id: welcomeId, role: 'system', text: 'Chat history corrupted/invalid, started new session.'}] });
        }
      } catch (error) {
        console.error("KatanaContext: Failed to parse messages from localStorage", error);
        localStorage.removeItem(LOCAL_STORAGE_MESSAGES_KEY);
        const errorMsgId = Date.now();
        dispatch({ type: 'LOAD_MESSAGES', payload: [{id: errorMsgId, role: 'system', text: 'Failed to load chat history, started new session.'}] });
      }
    } else {
       const welcomeId = Date.now();
       // Ensure initial message ID is consistent with nextMessageId logic
       dispatch({type: 'ADD_MESSAGE', payload: {id: welcomeId, role: 'katana', text: 'Katana Nexus Initialized. Awaiting commands.', timestamp: new Date().toISOString()}});
       // ADD_MESSAGE reducer already updates nextMessageId based on the new message's ID
    }
  }, []);

  useEffect(() => {
    if (state.messages.length > 0 || localStorage.getItem(LOCAL_STORAGE_MESSAGES_KEY) !== null ) {
        localStorage.setItem(LOCAL_STORAGE_MESSAGES_KEY, JSON.stringify(state.messages));
    }
  }, [state.messages]);

  return (
    <KatanaContext.Provider value={{ state, dispatch }}>
      {children}
    </KatanaContext.Provider>
  );
};

// --- Custom Hook ---
export const useKatana = (): KatanaContextProps => {
  const context = useContext(KatanaContext);
  if (context === undefined) {
    throw new Error('useKatana must be used within a KatanaProvider');
  }
  return context;
};
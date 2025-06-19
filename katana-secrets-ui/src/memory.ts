// src/memory.ts
const STORAGE_KEY = 'katana_chat_memory';

export type MemoryEntry = {
  id: number;
  role: 'user' | 'katana';
  text: string;
  timestamp?: string;
};

export function loadMemory(): MemoryEntry[] {
  if (typeof window === 'undefined' || !window.localStorage) {
    return [];
  }
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw) as MemoryEntry[];
    if (Array.isArray(parsed) && parsed.every(item => typeof item === 'object' && item !== null && 'id' in item && 'role' in item && 'text' in item)) {
        return parsed;
    }
    console.warn("Katana Memory: Stored data is not in expected format. Resetting.");
    localStorage.removeItem(STORAGE_KEY);
    return [];
  } catch (error) {
    console.warn("Katana Memory: Failed to parse stored data. Resetting.", error);
    localStorage.removeItem(STORAGE_KEY);
    return [];
  }
}

export function saveMemory(data: MemoryEntry[]) {
  if (typeof window === 'undefined' || !window.localStorage) {
    return;
  }
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  } catch (error) {
    console.error("Katana Memory: Failed to save data to localStorage.", error);
  }
}

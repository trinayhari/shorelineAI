"use client";

import { create } from "zustand";

interface ParcelState {
  availableTowns: string[];
  selectedTown: string | null;
  isSearching: boolean;
  lastResult: string | null;

  // Actions
  setTowns: (towns: string[]) => void;
  setSelectedTown: (town: string | null) => void;
  setSearching: (isSearching: boolean) => void;
  setSearchResult: (result: string | null) => void;
  reset: () => void;
}

const initialState = {
  availableTowns: [],
  selectedTown: null,
  isSearching: false,
  lastResult: null,
};

export const useParcelStore = create<ParcelState>((set) => ({
  ...initialState,

  setTowns: (towns) => set({ availableTowns: towns }),

  setSelectedTown: (town) => set({ selectedTown: town, lastResult: null }),

  setSearching: (isSearching) => set({ isSearching }),

  setSearchResult: (result) => set({ lastResult: result, isSearching: false }),

  reset: () => set(initialState),
}));

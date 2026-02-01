"use client";

import { create } from "zustand";

interface ZoningState {
  // Location selection
  selectedState: string | null;
  selectedMunicipality: string | null;
  municipalities: Record<string, string | null>;

  // Processing state
  isReady: boolean;
  isProcessing: boolean;
  statusMessage: string;
  jobId: string | null;

  // Document info
  pdfTitle: string | null;
  pdfUrl: string | null;
  chunksCount: number;

  // Actions
  setSelectedState: (state: string | null) => void;
  setSelectedMunicipality: (municipality: string | null) => void;
  setMunicipalities: (municipalities: Record<string, string | null>) => void;
  setProcessingStatus: (status: Partial<{
    isReady: boolean;
    isProcessing: boolean;
    statusMessage: string;
    jobId: string | null;
  }>) => void;
  setDocumentInfo: (info: Partial<{
    pdfTitle: string | null;
    pdfUrl: string | null;
    chunksCount: number;
  }>) => void;
  reset: () => void;
  resetMunicipality: () => void;
}

const initialState = {
  selectedState: null,
  selectedMunicipality: null,
  municipalities: {},
  isReady: false,
  isProcessing: false,
  statusMessage: "",
  jobId: null,
  pdfTitle: null,
  pdfUrl: null,
  chunksCount: 0,
};

export const useZoningStore = create<ZoningState>((set) => ({
  ...initialState,

  setSelectedState: (state) =>
    set({
      selectedState: state,
      selectedMunicipality: null,
      municipalities: {},
      isReady: false,
      isProcessing: false,
      statusMessage: "",
      pdfTitle: null,
      pdfUrl: null,
      chunksCount: 0,
    }),

  setSelectedMunicipality: (municipality) =>
    set({
      selectedMunicipality: municipality,
      isReady: false,
      isProcessing: false,
      statusMessage: "",
      pdfTitle: null,
      pdfUrl: null,
      chunksCount: 0,
    }),

  setMunicipalities: (municipalities) => set({ municipalities }),

  setProcessingStatus: (status) => set((state) => ({ ...state, ...status })),

  setDocumentInfo: (info) => set((state) => ({ ...state, ...info })),

  reset: () => set(initialState),

  resetMunicipality: () =>
    set({
      selectedMunicipality: null,
      isReady: false,
      isProcessing: false,
      statusMessage: "",
      pdfTitle: null,
      pdfUrl: null,
      chunksCount: 0,
    }),
}));

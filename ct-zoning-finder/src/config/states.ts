export interface StateConfig {
  abbreviation: string;
  municipalityTerm: string;
  sourceUrl: string;
}

export const STATES: Record<string, StateConfig> = {
  Connecticut: {
    abbreviation: "CT",
    municipalityTerm: "town",
    sourceUrl: "https://portal.ct.gov/government/cities-and-towns",
  },
};

export const DEFAULT_STATE = "Connecticut";

export function getMunicipalityTerm(stateName: string): string {
  return STATES[stateName]?.municipalityTerm ?? "municipality";
}

export function getStateAbbreviation(stateName: string): string {
  return STATES[stateName]?.abbreviation ?? "";
}

"use client";

import { useEffect, useState } from "react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { STATES } from "@/config/states";
import { useZoningStore } from "@/store/zoning-store";

export function LocationSelector() {
  const {
    selectedState,
    selectedMunicipality,
    municipalities,
    setSelectedState,
    setSelectedMunicipality,
    setMunicipalities,
  } = useZoningStore();

  const [isLoadingMunicipalities, setIsLoadingMunicipalities] = useState(false);

  const availableStates = Object.keys(STATES);

  useEffect(() => {
    if (selectedState && Object.keys(municipalities).length === 0) {
      loadMunicipalities(selectedState);
    }
  }, [selectedState]);

  const loadMunicipalities = async (stateName: string) => {
    setIsLoadingMunicipalities(true);
    try {
      const response = await fetch(
        `/api/municipalities?state=${encodeURIComponent(stateName)}`
      );
      const data = await response.json();

      if (data.success && data.data?.municipalities) {
        setMunicipalities(data.data.municipalities);
      }
    } catch (error) {
      console.error("Failed to load municipalities:", error);
    } finally {
      setIsLoadingMunicipalities(false);
    }
  };

  const handleStateChange = (value: string) => {
    setSelectedState(value);
  };

  const handleMunicipalityChange = (value: string) => {
    setSelectedMunicipality(value);
  };

  const sortedMunicipalities = Object.keys(municipalities).sort();

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-medium">Select Location</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">
          <label className="text-sm font-medium">State</label>
          <Select value={selectedState || ""} onValueChange={handleStateChange}>
            <SelectTrigger>
              <SelectValue placeholder="Select a state" />
            </SelectTrigger>
            <SelectContent>
              {availableStates.map((state) => (
                <SelectItem key={state} value={state}>
                  {state}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium">Municipality</label>
          <Select
            value={selectedMunicipality || ""}
            onValueChange={handleMunicipalityChange}
            disabled={!selectedState || isLoadingMunicipalities}
          >
            <SelectTrigger>
              <SelectValue
                placeholder={
                  isLoadingMunicipalities
                    ? "Loading..."
                    : selectedState
                      ? "Select a municipality"
                      : "Select a state first"
                }
              />
            </SelectTrigger>
            <SelectContent>
              {sortedMunicipalities.map((muni) => (
                <SelectItem key={muni} value={muni}>
                  {muni}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>
    </div>
  );
}

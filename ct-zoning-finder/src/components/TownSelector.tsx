"use client";

import { useEffect, useState } from "react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useParcelStore } from "@/store/parcel-store";

export function TownSelector() {
  const { availableTowns, selectedTown, setTowns, setSelectedTown } = useParcelStore();
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (availableTowns.length === 0) {
      loadTowns();
    }
  }, []);

  const loadTowns = async () => {
    setIsLoading(true);
    try {
      const response = await fetch("/api/parcels/towns");
      const data = await response.json();

      if (data.success && data.data?.towns) {
        setTowns(data.data.towns);
      }
    } catch (error) {
      console.error("Failed to load towns:", error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-2">
      <label className="text-sm font-medium">Select Town</label>
      <Select
        value={selectedTown || ""}
        onValueChange={setSelectedTown}
        disabled={isLoading}
      >
        <SelectTrigger>
          <SelectValue
            placeholder={isLoading ? "Loading towns..." : "Choose a town to search"}
          />
        </SelectTrigger>
        <SelectContent>
          {availableTowns.map((town) => (
            <SelectItem key={town} value={town}>
              {town}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

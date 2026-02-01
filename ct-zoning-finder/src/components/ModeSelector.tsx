"use client";

import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";

export type SearchMode = "zoning" | "parcels" | "research";

interface ModeSelectorProps {
  value: SearchMode;
  onChange: (value: SearchMode) => void;
}

export function ModeSelector({ value, onChange }: ModeSelectorProps) {
  return (
    <div className="space-y-3">
      <h3 className="text-lg font-medium">Search Mode</h3>
      <RadioGroup
        value={value}
        onValueChange={(v) => onChange(v as SearchMode)}
        className="flex flex-col sm:flex-row gap-4"
      >
        <div className="flex items-center space-x-2">
          <RadioGroupItem value="zoning" id="zoning" />
          <Label htmlFor="zoning" className="cursor-pointer">
            Zoning Regulations
          </Label>
        </div>
        <div className="flex items-center space-x-2">
          <RadioGroupItem value="parcels" id="parcels" />
          <Label htmlFor="parcels" className="cursor-pointer">
            Property Search
          </Label>
        </div>
        <div className="flex items-center space-x-2">
          <RadioGroupItem value="research" id="research" />
          <Label htmlFor="research" className="cursor-pointer font-semibold text-blue-600">
            Property Research (Combined)
          </Label>
        </div>
      </RadioGroup>
      {value === "research" && (
        <p className="text-sm text-muted-foreground">
          Chat with zoning regulations + live property data from your selected town
        </p>
      )}
    </div>
  );
}

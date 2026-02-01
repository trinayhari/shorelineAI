"use client";

import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";

interface ModeSelectorProps {
  value: "zoning" | "parcels";
  onChange: (value: "zoning" | "parcels") => void;
}

export function ModeSelector({ value, onChange }: ModeSelectorProps) {
  return (
    <div className="space-y-2">
      <h3 className="text-lg font-medium">Search Mode</h3>
      <RadioGroup
        value={value}
        onValueChange={(v) => onChange(v as "zoning" | "parcels")}
        className="flex gap-4"
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
            Property/Parcel Data
          </Label>
        </div>
      </RadioGroup>
    </div>
  );
}

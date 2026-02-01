export interface ParcelLocation {
  address?: string;
  city?: string;
  state?: string;
  zip?: string;
}

export interface ParcelTown {
  name?: string;
}

export interface ParcelOwnership {
  owner?: string;
}

export interface ParcelZoning {
  stateUseDescription?: string;
  zoneDescription?: string;
}

export interface ParcelLand {
  acres?: number;
  waterFrontageFt?: number;
}

export interface ParcelRooms {
  bedrooms?: number;
  bathrooms?: number;
}

export interface ParcelArea {
  living?: number;
}

export interface ParcelBuilding {
  styleDesc?: string;
  rooms?: ParcelRooms;
  area?: ParcelArea;
  actualYearBuilt?: number;
}

export interface ParcelValuation {
  valuationYear: number;
  assessed?: {
    total?: number;
  };
}

export interface ParcelSale {
  salePrice?: number;
  saleDate?: string;
}

export interface Parcel {
  _id?: string;
  parcelId?: string;
  town?: ParcelTown;
  location?: ParcelLocation;
  ownership?: ParcelOwnership;
  zoning?: ParcelZoning;
  land?: ParcelLand;
  buildings?: ParcelBuilding[];
  valuations?: ParcelValuation[];
  sales?: ParcelSale[];
  embedding?: number[];
  rag?: {
    searchableText?: string;
    embedding?: number[];
  };
  score?: number;
}

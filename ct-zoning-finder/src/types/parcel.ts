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
  state_use_description?: string;
  zone_description?: string;
  zone?: string;
}

export interface ParcelLand {
  acres?: number;
  water_frontage_ft?: number;
  frontage_ft?: number;
  depth_ft?: number;
}

export interface ParcelRooms {
  bedrooms?: number;
  bathrooms?: number;
  total_rooms?: number;
}

export interface ParcelArea {
  living?: number;
  total?: number;
}

export interface ParcelBuilding {
  style_desc?: string;
  rooms?: ParcelRooms;
  area?: ParcelArea;
  actual_year_built?: number;
  condition?: string;
  grade?: string;
  stories?: number;
}

export interface ParcelValuation {
  valuation_year: number;
  assessed?: {
    total?: number;
    land?: number;
    building?: number;
  };
  appraised?: {
    total?: number;
  };
}

export interface ParcelSale {
  sale_price?: number;
  sale_date?: string;
  deed_type?: string;
}

export interface Parcel {
  _id?: string;
  parcel_id?: string;
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
    searchable_text?: string;
    embedding?: number[];
  };
  score?: number;
}

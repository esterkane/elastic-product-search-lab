export type SearchQueryParams = {
  q?: string;
  category?: string;
  brand?: string;
  availability?: string;
  minPrice?: number;
  maxPrice?: number;
  size: number;
  debug: boolean;
  boost?: boolean;
};

export type SuggestQueryParams = {
  q: string;
  size: number;
};

export type ProductResponse = {
  productId: string;
  title: string;
  description: string;
  brand: string;
  category: string;
  attributes: Record<string, unknown>;
  price: number;
  currency: string;
  availability: string;
  popularityScore: number;
  sellerId: string;
  updatedAt: string;
  score?: number;
  overlay?: {
    source: string;
    appliedFields: string[];
  };
};

export type ProductSearchResponse = {
  took: number;
  total: number;
  products: ProductResponse[];
  debug?: {
    query: Record<string, unknown>;
    overlay?: {
      enabled: boolean;
      index?: string;
      attempted: boolean;
      applied: number;
      error?: string;
    };
  };
};

export type ProductSuggestOption = {
  productId: string;
  text: string;
  title: string;
  brand: string;
  category: string;
  score?: number;
};

export type ProductSuggestResponse = {
  took: number;
  suggestions: ProductSuggestOption[];
  debug?: {
    query: Record<string, unknown>;
  };
};

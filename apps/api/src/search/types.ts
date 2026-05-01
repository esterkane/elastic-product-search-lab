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
};

export type ProductSearchResponse = {
  took: number;
  total: number;
  products: ProductResponse[];
  debug?: {
    query: Record<string, unknown>;
  };
};
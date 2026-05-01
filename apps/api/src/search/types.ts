export type SearchQueryParams = {
  q?: string;
  category?: string;
  brand?: string;
  availability?: string;
  minPrice?: number;
  maxPrice?: number;
  size: number;
  debug: boolean;
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
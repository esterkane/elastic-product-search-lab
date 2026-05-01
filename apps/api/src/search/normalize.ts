import type { ProductResponse } from "./types.js";

type ElasticsearchHit = {
  _id?: string;
  _score?: number;
  _source?: Record<string, unknown>;
};

export function normalizeProductHit(hit: ElasticsearchHit): ProductResponse {
  const source = hit._source ?? {};
  return {
    productId: String(source.product_id ?? hit._id ?? ""),
    title: String(source.title ?? ""),
    description: String(source.description ?? ""),
    brand: String(source.brand ?? ""),
    category: String(source.category ?? ""),
    attributes: (source.attributes as Record<string, unknown> | undefined) ?? {},
    price: Number(source.price ?? 0),
    currency: String(source.currency ?? ""),
    availability: String(source.availability ?? ""),
    popularityScore: Number(source.popularity_score ?? 0),
    sellerId: String(source.seller_id ?? ""),
    updatedAt: String(source.updated_at ?? ""),
    score: hit._score,
  };
}
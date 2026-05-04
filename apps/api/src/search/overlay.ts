import type { ElasticsearchLikeClient } from "../app.js";
import type { ProductResponse } from "./types.js";

const VOLATILE_FIELDS = ["price", "currency", "availability"] as const;

type VolatileField = (typeof VOLATILE_FIELDS)[number];

export type OverlayOptions = {
  enabled: boolean;
  index?: string;
};

export type OverlayDebug = {
  enabled: boolean;
  index?: string;
  attempted: boolean;
  applied: number;
  error?: string;
};

type LiveSource = Partial<Record<VolatileField, unknown>>;

export async function mergeVolatileOverlay(
  client: ElasticsearchLikeClient,
  products: ProductResponse[],
  options: OverlayOptions,
): Promise<{ products: ProductResponse[]; debug: OverlayDebug }> {
  const debug: OverlayDebug = {
    enabled: options.enabled,
    index: options.index,
    attempted: false,
    applied: 0,
  };

  if (!options.enabled || !options.index || products.length === 0) {
    return { products, debug };
  }
  if (!client.mget) {
    return { products, debug: { ...debug, error: "mget_unavailable" } };
  }

  debug.attempted = true;
  try {
    const response = await client.mget({
      index: options.index,
      ids: products.map((product) => product.productId),
      _source: [...VOLATILE_FIELDS],
    });
    const docs = response.docs ?? [];
    const overlays = new Map<string, LiveSource>();
    for (const doc of docs) {
      if (doc?.found && doc._id && doc._source) overlays.set(String(doc._id), doc._source as LiveSource);
    }

    const merged = products.map((product) => {
      const overlay = overlays.get(product.productId);
      if (!overlay) return product;
      const appliedFields: string[] = [];
      const next = { ...product };
      if (overlay.price !== undefined) {
        next.price = Number(overlay.price);
        appliedFields.push("price");
      }
      if (overlay.currency !== undefined) {
        next.currency = String(overlay.currency);
        appliedFields.push("currency");
      }
      if (overlay.availability !== undefined) {
        next.availability = String(overlay.availability);
        appliedFields.push("availability");
      }
      if (appliedFields.length === 0) return product;
      debug.applied += 1;
      return { ...next, overlay: { source: options.index ?? "", appliedFields } };
    });
    return { products: merged, debug };
  } catch (error) {
    return {
      products,
      debug: {
        ...debug,
        error: error instanceof Error ? error.message : "overlay_lookup_failed",
      },
    };
  }
}

import type { MetadataRoute } from "next";
import { SITE_ORIGIN } from "@/lib/site";

/** 静态导出下必须显式声明，否则 Next 会当成动态路由 */
export const dynamic = "force-static";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [{ userAgent: "*", allow: "/" }],
    sitemap: `${SITE_ORIGIN}/sitemap.xml`,
    host: SITE_ORIGIN,
  };
}

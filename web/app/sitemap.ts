import type { MetadataRoute } from "next";
import { loadMeta, loadVideos } from "@/lib/data";
import { SITE_ORIGIN } from "@/lib/site";

/** 静态导出下必须显式声明，否则 Next 会当成动态路由 */
export const dynamic = "force-static";

export default function sitemap(): MetadataRoute.Sitemap {
  const meta = loadMeta();
  const lastModified = meta.generated_at ? new Date(meta.generated_at) : new Date();
  const videos = loadVideos();

  return [
    {
      url: `${SITE_ORIGIN}/`,
      lastModified,
      changeFrequency: "daily",
      priority: 1,
    },
    {
      url: `${SITE_ORIGIN}/privacy/`,
      lastModified,
      changeFrequency: "yearly",
      priority: 0.3,
    },
    ...videos.map((video) => ({
      url: `${SITE_ORIGIN}/v/${video.bvid}/`,
      lastModified,
      changeFrequency: "monthly" as const,
      priority: 0.6,
    })),
  ];
}

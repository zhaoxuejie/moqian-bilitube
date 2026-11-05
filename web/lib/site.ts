/**
 * 站点级配置：留空则不显示对应入口。
 *
 * url 填上后（例如 https://bilitube.example.com，不要结尾斜杠），
 * OpenGraph / canonical / robots.txt / sitemap.xml 会用真实域名生成。
 * 留空时回退到 localhost，本地构建不会报错。
 */
export const SITE = {
  url: "https://www.51bilitube.com",
  repo: "https://github.com/zhaoxuejie/moqian-bilitube",
  contact: "", // 可选：公开邮箱，例如 "hi@example.com"
  updatedAt: "2026.11.05",
};

export const SITE_ORIGIN = SITE.url || "http://localhost:3000";

/** 分享卡片与默认描述，多处复用 */
export const SITE_TITLE = "BiliTube · AI 视频精选";
export const SITE_DESCRIPTION =
  "从 B 站 AI 大模型视频里挑出值得花时间的那些：先按分区与时长的分位打分，再让模型读完弹幕与简介逐条判断。排序不看播放量。";

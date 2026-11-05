export type Card = {
  verdict: string;
  quality: number;
  summary: string;
  why: string;
  audience: string;
  prereq: string;
  difficulty: number;
  freshness: "evergreen" | "aging" | "outdated";
  topics: string[];
};

export type Video = {
  bvid: string;
  title: string;
  up: string | null;
  mid: number | null;
  duration: number | null;
  pubdate: number | null;
  tname: string;
  cover: string | null;
  view: number | null;
  favorite: number | null;
  coin: number | null;
  danmaku: number | null;
  reply: number | null;
  scores: { machine: number | null; content: number | null; total: number | null };
  flags: string[];
  card: Card | null;
};

export type Topic = { name: string; count: number };

export type SiteMeta = {
  generated_at?: string;
  videos?: number;
  with_cards?: number;
  topics?: number;
  candidates?: number;
  danmaku_rows?: number;
  covers?: number;
};

/** B 站封面支持在路径后缀里指定尺寸与格式，按需取缩略图，避免拉原图。 */
export function coverUrl(cover: string | null | undefined, width = 672): string | null {
  if (!cover) return null;
  const height = Math.round((width * 9) / 16);
  const base = cover.split("@")[0];
  return `${base}@${width}w_${height}h_1c.webp`;
}

export function formatDuration(seconds: number | null): string {
  const value = Math.max(0, seconds ?? 0);
  const hours = Math.floor(value / 3600);
  const minutes = Math.floor((value % 3600) / 60);
  if (hours > 0) return `${hours} 小时 ${minutes} 分`;
  return `${Math.max(1, minutes)} 分钟`;
}

/** 封面角标用的短时长：12:04 / 1:23:45 */
export function formatClock(seconds: number | null): string {
  const value = Math.max(0, seconds ?? 0);
  const hours = Math.floor(value / 3600);
  const minutes = Math.floor((value % 3600) / 60);
  const secs = value % 60;
  const pad = (input: number) => String(input).padStart(2, "0");
  if (hours > 0) return `${hours}:${pad(minutes)}:${pad(secs)}`;
  return `${minutes}:${pad(secs)}`;
}

export function formatCount(value: number | null | undefined): string {
  const number = value ?? 0;
  if (number >= 100000000) return `${(number / 100000000).toFixed(1)} 亿`;
  if (number >= 10000) return `${(number / 10000).toFixed(1)} 万`;
  return number.toLocaleString("en-US");
}

/** 千分位整数，用于页面上的硬指标。 */
export function formatNumber(value: number | null | undefined): string {
  return (value ?? 0).toLocaleString("en-US");
}

export function formatDate(pubdate: number | null): string {
  if (!pubdate) return "未知日期";
  const date = new Date(pubdate * 1000);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}.${month}.${day}`;
}

export function formatGeneratedAt(value: string | undefined): string {
  if (!value) return "未知";
  return value.replace("T", " ").slice(0, 16);
}

/** 内容类型决定卡片左上角的小标签；新闻/测评不值钱，不给强调色。 */
export const VERDICT_TONE: Record<string, "learn" | "watch" | "skip"> = {
  教程: "learn",
  实战: "learn",
  测评: "watch",
  新闻: "watch",
  搬运: "skip",
  水: "skip",
};

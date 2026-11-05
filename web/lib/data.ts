import fs from "node:fs";
import path from "node:path";
import type { SiteMeta, Topic, Video } from "./types";

const DATA_DIR = path.join(process.cwd(), "public", "data");

function readJson<T>(file: string): T {
  return JSON.parse(fs.readFileSync(path.join(DATA_DIR, file), "utf-8")) as T;
}

let videoCache: Video[] | null = null;
let topicCache: Topic[] | null = null;
let metaCache: SiteMeta | null = null;

export function loadVideos(): Video[] {
  if (!videoCache) videoCache = readJson<Video[]>("videos.json");
  return videoCache;
}

export function loadTopics(): Topic[] {
  if (!topicCache) topicCache = readJson<Topic[]>("topics.json");
  return topicCache;
}

export function loadMeta(): SiteMeta {
  if (!metaCache) metaCache = readJson<SiteMeta>("meta.json");
  return metaCache;
}

"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { FeatureCard, VideoCard } from "@/components/VideoCard";
import { SearchIcon } from "@/components/icons";
import { FAVORITES_EVENT, readFavorites } from "@/lib/favorites";
import type { Topic, Video } from "@/lib/types";

const PAGE_SIZE = 25;

/* 排序用平铺文字页签，标签尽量短 */
const SORTS = [
  { id: "total", label: "综合" },
  { id: "content", label: "内容" },
  { id: "machine", label: "互动" },
  { id: "new", label: "最新" },
];

/**
 * 页码序列：总数 ≤7 全展示；否则固定首末页，当前页左右各留一页，
 * 中间断档用 gap 占位（渲染成省略号）。
 */
function buildPages(current: number, total: number): (number | "gap")[] {
  if (total <= 7) {
    return Array.from({ length: total }, (_, index) => index + 1);
  }

  const pages = new Set<number>([1, total, current - 1, current, current + 1]);
  if (current <= 4) [2, 3, 4, 5].forEach((item) => pages.add(item));
  if (current >= total - 3) {
    [total - 1, total - 2, total - 3, total - 4].forEach((item) => pages.add(item));
  }

  const sorted = [...pages].filter((item) => item >= 1 && item <= total).sort((a, b) => a - b);
  const result: (number | "gap")[] = [];
  sorted.forEach((item, index) => {
    if (index > 0 && item - sorted[index - 1] > 1) result.push("gap");
    result.push(item);
  });
  return result;
}

function Skeleton() {
  return (
    <>
      {Array.from({ length: 6 }).map((_, index) => (
        <div className="card skeleton" key={index} aria-hidden="true">
          <div className="cover" />
          <div className="bar long" />
          <div className="bar short" />
        </div>
      ))}
    </>
  );
}

export default function VideoExplorer() {
  const [videos, setVideos] = useState<Video[]>([]);
  const [topics, setTopics] = useState<Topic[]>([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [topic, setTopic] = useState("");
  const [sort, setSort] = useState("total");
  const [page, setPage] = useState(1);
  const [allTopics, setAllTopics] = useState(false);
  const [onlySaved, setOnlySaved] = useState(false);
  const [saved, setSaved] = useState<string[]>([]);
  const listRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const skipScroll = useRef(true);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      fetch("/data/videos.json").then((response) => response.json()),
      fetch("/data/topics.json").then((response) => response.json()),
    ])
      .then(([videoList, topicList]) => {
        if (cancelled) return;
        setVideos(videoList as Video[]);
        setTopics(topicList as Topic[]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const requested = new URLSearchParams(window.location.search).get("topic");
    if (requested) setTopic(requested);
  }, []);

  // 让筛选结果可分享：主题变化时同步到地址栏，不产生历史记录。
  useEffect(() => {
    const url = new URL(window.location.href);
    if (topic) url.searchParams.set("topic", topic);
    else url.searchParams.delete("topic");
    window.history.replaceState(null, "", url);
  }, [topic]);

  // 收藏存在 localStorage，详情页点了收藏、别的标签页改了，这里都要同步
  useEffect(() => {
    const sync = () => setSaved(readFavorites());
    sync();
    window.addEventListener(FAVORITES_EVENT, sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener(FAVORITES_EVENT, sync);
      window.removeEventListener("storage", sync);
    };
  }, []);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      const typing =
        target?.tagName === "INPUT" ||
        target?.tagName === "TEXTAREA" ||
        target?.isContentEditable;
      if (event.key === "/" && !typing) {
        event.preventDefault();
        inputRef.current?.focus();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  const filtered = useMemo(() => {
    const keyword = query.trim().toLowerCase();
    const matched = videos.filter((video) => {
      if (onlySaved && !saved.includes(video.bvid)) return false;
      if (topic) {
        const list = video.card?.topics ?? [];
        if (!list.includes(topic)) return false;
      }
      if (!keyword) return true;
      const haystack = [
        video.title,
        video.up ?? "",
        video.tname,
        video.card?.summary ?? "",
        video.card?.why ?? "",
        (video.card?.topics ?? []).join(" "),
      ]
        .join(" ")
        .toLowerCase();
      return haystack.includes(keyword);
    });

    const sorted = [...matched];
    if (sort === "content") {
      sorted.sort((a, b) => (b.scores.content ?? 0) - (a.scores.content ?? 0));
    } else if (sort === "machine") {
      sorted.sort((a, b) => (b.scores.machine ?? 0) - (a.scores.machine ?? 0));
    } else if (sort === "new") {
      sorted.sort((a, b) => (b.pubdate ?? 0) - (a.pubdate ?? 0));
    } else {
      sorted.sort((a, b) => (b.scores.total ?? 0) - (a.scores.total ?? 0));
    }
    return sorted;
  }, [videos, query, topic, sort, onlySaved, saved]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const currentPage = Math.min(page, totalPages);
  const visible = filtered.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);

  const pristine = !query && !topic && !onlySaved && sort === "total" && currentPage === 1;
  const feature = pristine && visible.length > 0 ? visible[0] : null;
  const gridVideos = feature ? visible.slice(1) : visible;
  const hasFilters = Boolean(query || topic) || sort !== "total" || onlySaved;

  /* 翻页后滚回列表顶部。放到 effect 里等 React 提交完再测量：
     头条卡片只在第一页出现，切换时列表高度会变，提前测量会算错位置。 */
  useEffect(() => {
    if (skipScroll.current) {
      skipScroll.current = false;
      return;
    }
    const node = listRef.current;
    if (!node) return;
    const top = node.getBoundingClientRect().top + window.scrollY - 96;
    window.scrollTo({ top: Math.max(0, top), behavior: "smooth" });
  }, [page]);

  const goPage = (next: number) => {
    setPage(next);
  };

  const reset = () => {
    setQuery("");
    setTopic("");
    setOnlySaved(false);
    setSort("total");
    setPage(1);
  };

  return (
    <section className="shell discover" id="discover">
      {/* ── 标题 + 搜索 ── */}
      <div className="discover-head">
        <div>
          <h2>发现下一份灵感</h2>
          <p>循着兴趣，找到值得深入的内容。</p>
        </div>
        <label className="search-box">
          <SearchIcon />
          <input
            ref={inputRef}
            value={query}
            placeholder="搜索主题、视频或 UP 主"
            aria-label="搜索视频"
            onChange={(event) => {
              setQuery(event.target.value);
              setPage(1);
            }}
          />
          <span className="kbd">/</span>
        </label>
      </div>

      {/* ── 主题（带条数） ── */}
      <div className="discover-filters" id="topics">
        <div className={`topics${allTopics ? " open" : ""}`} role="group" aria-label="主题筛选">
          <button
            className="chip"
            data-active={!topic && !onlySaved}
            aria-pressed={!topic && !onlySaved}
            onClick={() => {
              setTopic("");
              setOnlySaved(false);
              setPage(1);
            }}
          >
            全部精选
          </button>
          <button
            className="chip"
            data-active={onlySaved}
            aria-pressed={onlySaved}
            onClick={() => {
              /* 与主题互斥：进入收藏视图时清掉主题筛选 */
              if (!onlySaved) setTopic("");
              setOnlySaved(!onlySaved);
              setPage(1);
            }}
          >
            我的收藏
            {saved.length ? <span className="chip-count">{saved.length}</span> : null}
          </button>
          {topics.map((item) => (
            <button
              className="chip"
              key={item.name}
              data-active={topic === item.name}
              aria-pressed={topic === item.name}
              onClick={() => {
                /* 主题与收藏互斥：选主题时自动退出收藏视图 */
                setTopic(topic === item.name ? "" : item.name);
                setOnlySaved(false);
                setPage(1);
              }}
            >
              {item.name}
              <span className="chip-count">{item.count}</span>
            </button>
          ))}
        </div>

        {topics.length > 6 ? (
          <button className="topic-toggle" onClick={() => setAllTopics(!allTopics)}>
            {allTopics ? "收起主题" : `展开全部 ${topics.length} 个`}
          </button>
        ) : null}
      </div>

      {loading ? (
        <div className="grid">
          <Skeleton />
        </div>
      ) : filtered.length === 0 ? (
        <div className="empty-state">
          <h3>{onlySaved ? "还没有收藏任何视频" : "没有匹配的视频"}</h3>
          <p>
            {onlySaved
              ? "在任意视频详情页点「收藏」，就会出现在这里——收藏只存在这台设备的浏览器里。"
              : "换个关键词试试，或者清掉筛选条件。"}
          </p>
        </div>
      ) : (
        <>
          {feature ? <FeatureCard video={feature} /> : null}

          {/* 列表标题 + 条数 + 排序，排序平铺在右侧 */}
          <div className="list-head">
            <div className="list-title">
              <h2>值得花时间的内容</h2>
              <p className="list-count">
                共 {filtered.length.toLocaleString("en-US")} 条
                {hasFilters ? (
                  <>
                    {" · "}
                    <button className="reset" onClick={reset}>
                      清除筛选
                    </button>
                  </>
                ) : null}
              </p>
            </div>
            <div className="list-sort" role="tablist" aria-label="排序方式">
              {SORTS.map((item) => (
                <button
                  key={item.id}
                  role="tab"
                  aria-selected={sort === item.id}
                  data-active={sort === item.id}
                  onClick={() => {
                    setSort(item.id);
                    setPage(1);
                  }}
                >
                  {item.label}
                </button>
              ))}

            </div>
          </div>

          <div className="grid" ref={listRef}>
            {gridVideos.map((video) => (
              <VideoCard key={video.bvid} video={video} />
            ))}
          </div>

          {totalPages > 1 ? (
            <nav className="pagination" aria-label="分页">
              <button
                className="arrow"
                aria-label="上一页"
                disabled={currentPage <= 1}
                onClick={() => goPage(currentPage - 1)}
              >
                ‹
              </button>
              {buildPages(currentPage, totalPages).map((item, index) =>
                item === "gap" ? (
                  <span className="gap" key={`gap-${index}`} aria-hidden="true">
                    …
                  </span>
                ) : (
                  <button
                    key={item}
                    data-active={item === currentPage}
                    aria-current={item === currentPage ? "page" : undefined}
                    aria-label={`第 ${item} 页`}
                    onClick={() => goPage(item)}
                  >
                    {item}
                  </button>
                ),
              )}
              <button
                className="arrow"
                aria-label="下一页"
                disabled={currentPage >= totalPages}
                onClick={() => goPage(currentPage + 1)}
              >
                ›
              </button>
            </nav>
          ) : null}
        </>
      )}
    </section>
  );
}

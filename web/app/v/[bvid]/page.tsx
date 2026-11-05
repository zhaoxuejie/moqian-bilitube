import Link from "next/link";
import type { Metadata } from "next";
import FavoriteButton from "@/components/FavoriteButton";
import { ArrowIcon } from "@/components/icons";
import { VideoCard } from "@/components/VideoCard";
import { loadVideos } from "@/lib/data";
import {
  formatCount,
  formatDate,
  formatDuration,
  type Video,
} from "@/lib/types";

export const dynamicParams = false;

export function generateStaticParams() {
  return loadVideos().map((video) => ({ bvid: video.bvid }));
}

/** 每条视频独立标题/描述/canonical，并用封面当分享卡片；否则 1360 页共用首页元信息。 */
export async function generateMetadata({
  params,
}: {
  params: Promise<{ bvid: string }>;
}): Promise<Metadata> {
  const { bvid } = await params;
  const video = loadVideos().find((item) => item.bvid === bvid);
  if (!video) {
    return { title: "未找到该视频", robots: { index: false } };
  }

  const description =
    video.card?.why ||
    video.card?.summary ||
    `${video.up ?? "B 站"} 的 AI 相关视频，按分区与时长分组打分，再读弹幕与简介给出判断。`;
  const path = `/v/${bvid}/`;
  const cover = video.cover?.replace(/^http:\/\//, "https://");
  const images = cover
    ? [{ url: cover, width: 672, height: 378, alt: video.title }]
    : [{ url: "/og.png", width: 1200, height: 630, alt: video.title }];

  return {
    title: `${video.title} · BiliTube`,
    description,
    alternates: { canonical: path },
    openGraph: {
      type: "article",
      title: video.title,
      description,
      url: path,
      images,
    },
    twitter: {
      card: "summary_large_image",
      title: video.title,
      description,
      images: images.map((image) => image.url),
    },
  };
}

const FRESHNESS_LABEL: Record<string, string> = {
  evergreen: "常青 · 现在看仍然成立",
  aging: "有时效 · 部分工具已变",
  outdated: "可能过时 · 结论需复核",
};

const DIFFICULTY_LABEL: Record<number, string> = {
  1: "入门",
  2: "轻量",
  3: "中等",
  4: "偏硬",
  5: "硬核",
};

function Bars({ video }: { video: Video }) {
  const content = video.scores.content ?? 0;
  const machine = video.scores.machine ?? 0;
  const total = video.scores.total ?? 0;
  return (
    <>
      <div className="scoreline">
        <span className="num">{total.toFixed(2)}</span>
        <span className="of">/ 100 综合</span>
      </div>
      <div className="bar hi">
        <span>内容</span>
        <span className="track">
          <i style={{ width: `${Math.min(100, content)}%` }} />
        </span>
        <span className="val">{content.toFixed(2)}</span>
      </div>
      <div className="bar">
        <span>互动</span>
        <span className="track">
          <i style={{ width: `${Math.min(100, machine)}%` }} />
        </span>
        <span className="val">{machine.toFixed(2)}</span>
      </div>
      <p className="score-legend">内容 40% · 互动 60%</p>
    </>
  );
}

export default async function VideoPage({ params }: { params: Promise<{ bvid: string }> }) {
  const { bvid } = await params;
  const videos = loadVideos();
  const video = videos.find((item) => item.bvid === bvid);

  if (!video) {
    return (
      <main className="shell detail">
        <p>未找到该视频。</p>
        <Link className="btn" href="/">
          返回精选
        </Link>
      </main>
    );
  }

  const card = video.card;
  const playerUrl = `https://player.bilibili.com/player.html?bvid=${video.bvid}&page=1&high_quality=0&danmaku=0&autoplay=0`;
  const primaryTopic = card?.topics?.[0];
  const related = primaryTopic
    ? videos
        .filter(
          (item) =>
            item.bvid !== video.bvid && (item.card?.topics ?? []).includes(primaryTopic),
        )
        .slice(0, 3)
    : [];

  return (
    <main className="shell detail">
      <div className="crumbs">
        <Link href="/">精选</Link>
        <span className="sep">/</span>
        <span>{video.tname || "未分区"}</span>
      </div>

      <h1>{video.title}</h1>

      <div className="subline">
        <span>{video.up ?? "未知 UP"}</span>
        <span className="sep" />
        <span>{formatDate(video.pubdate)}</span>
        <span className="sep" />
        <span>{formatDuration(video.duration)}</span>
        <span className="sep" />
        <span>{formatCount(video.view)} 播放</span>
        <span className="sep" />
        <span>{formatCount(video.danmaku)} 弹幕</span>
      </div>

      <div className="detail-body">
        <div>
          <div className="player">
            <iframe
              src={playerUrl}
              allowFullScreen
              referrerPolicy="no-referrer"
              title={video.title}
            />
          </div>

          {card ? (
            <section className="notes">
              <p className="label">编辑手记 · 大模型读完弹幕后的判断</p>
              <p className="pullquote">{card.why}</p>
              <p className="summary">{card.summary}</p>
              <dl className="kv">
                <dt>适合谁</dt>
                <dd>{card.audience}</dd>
                <dt>前置</dt>
                <dd>{card.prereq}</dd>
                <dt>难度</dt>
                <dd>
                  {DIFFICULTY_LABEL[card.difficulty] ?? "中等"} · {"●".repeat(card.difficulty)}
                  {"○".repeat(Math.max(0, 5 - card.difficulty))}
                </dd>
                <dt>时效</dt>
                <dd>{FRESHNESS_LABEL[card.freshness] ?? card.freshness}</dd>
                <dt>类型</dt>
                <dd>{card.verdict}</dd>
              </dl>
            </section>
          ) : (
            <section className="notes">
              <p className="label">编辑手记</p>
              <p className="summary">这条视频还没有生成卡片。</p>
            </section>
          )}

          {related.length ? (
            <section className="related">
              <h2>同一主题 · {primaryTopic}</h2>
              <div className="related-grid">
                {related.map((item) => (
                  <VideoCard key={item.bvid} video={item} />
                ))}
              </div>
            </section>
          ) : null}
        </div>

        <aside className="rail">
          <div className="block">
            <p className="label">评分</p>
            <Bars video={video} />
          </div>

          <div className="block">
            <p className="label">数据</p>
            <dl className="kv">
              <dt>播放</dt>
              <dd>{formatCount(video.view)}</dd>
              <dt>收藏</dt>
              <dd>{formatCount(video.favorite)}</dd>
              <dt>投币</dt>
              <dd>{formatCount(video.coin)}</dd>
              <dt>弹幕</dt>
              <dd>{formatCount(video.danmaku)}</dd>
              <dt>评论</dt>
              <dd>{formatCount(video.reply)}</dd>
              <dt>分区</dt>
              <dd>{video.tname || "未分区"}</dd>
            </dl>
          </div>

          {card?.topics?.length ? (
            <div className="block">
              <p className="label">主题</p>
              <div className="topics-list">
                {card.topics.map((item) => (
                  <Link key={item} href={`/?topic=${encodeURIComponent(item)}`}>
                    {item}
                  </Link>
                ))}
              </div>
            </div>
          ) : null}

          <div className="block actions">
            <FavoriteButton bvid={video.bvid} />
            <a
              className="btn"
              href={`https://www.bilibili.com/video/${video.bvid}`}
              target="_blank"
              rel="noreferrer"
            >
              在 B 站打开
              <ArrowIcon size={11} />
            </a>
          </div>
        </aside>
      </div>
    </main>
  );
}

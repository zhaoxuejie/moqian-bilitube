import Link from "next/link";
import { UserIcon } from "@/components/icons";
import { coverUrl, formatClock, type Video } from "@/lib/types";

/** 内容类型标签：教程 / 实战 / 测评… */
function verdict(video: Video): string {
  return video.card?.verdict ?? video.tname ?? "";
}

/** 头条上的短标签，按难度推导，避免写死文案 */
function depthTag(video: Video): string {
  const level = video.card?.difficulty ?? 3;
  if (level <= 2) return "入门友好";
  if (level === 3) return "需要一点基础";
  return "适合深入理解原理";
}

function Cover({ video, width }: { video: Video; width: number }) {
  const src = coverUrl(video.cover, width);
  return (
    <div className="cover">
      {src ? (
        <img
          src={src}
          alt=""
          loading="lazy"
          decoding="async"
          referrerPolicy="no-referrer"
        />
      ) : (
        <span className="cover-empty">{verdict(video) || "无封面"}</span>
      )}
      <span className="duration">{formatClock(video.duration)}</span>
    </div>
  );
}

export function VideoCard({ video }: { video: Video }) {
  const score = (video.scores.total ?? 0).toFixed(2);
  const topic = video.card?.topics?.[0] ?? "";

  return (
    <Link className="card" href={`/v/${video.bvid}/`}>
      <Cover video={video} width={672} />
      <p className="card-eyebrow">
        <span>{verdict(video)}</span>
        {topic ? <span className="sep" aria-hidden="true" /> : null}
        {topic ? <span>{topic}</span> : null}
      </p>
      <h3>{video.title}</h3>
      {video.card?.why ? <p className="card-why">{video.card.why}</p> : null}
      <div className="card-meta">
        <span className="up">
          <UserIcon />
          <span className="up-name">{video.up ?? "未知 UP"}</span>
        </span>
        <span className="score">
          <span className="unit">综合分</span>
          {score}
        </span>
      </div>
    </Link>
  );
}

export function FeatureCard({ video }: { video: Video }) {
  const score = (video.scores.total ?? 0).toFixed(2);
  const minutes = Math.max(1, Math.floor((video.duration ?? 0) / 60));
  const href = `/v/${video.bvid}/`;

  return (
    <article className="featured-card">
      <Link className="feature-media" href={href}>
        <Cover video={video} width={880} />
      </Link>

      <div className="feature-copy">
        <p className="feature-label">
          <span className="line" aria-hidden="true" />
          本期推荐
        </p>
        <Link href={href}>
          <h3 className="feature-title">{video.title}</h3>
        </Link>
        {video.card?.why ? <p className="feature-why">{video.card.why}</p> : null}
        <div className="feature-meta">
          <span>{video.up ?? "未知 UP"}</span>
          <span aria-hidden="true">·</span>
          <span>{minutes} 分钟</span>
        </div>
        <div className="feature-foot">
          <span className="feature-tag">{depthTag(video)}</span>
          <span className="feature-score">
            {score}
            <span className="of">/ 100</span>
          </span>
        </div>
      </div>
    </article>
  );
}

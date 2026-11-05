import VideoExplorer from "@/components/VideoExplorer";
import { loadMeta } from "@/lib/data";
import { formatNumber } from "@/lib/types";

export default function Home() {
  const meta = loadMeta();

  return (
    <main>
      <section className="shell hero">
        <div className="hero-grid">
          {/* 左：主张 */}
          <div className="hero-copy">
            <p className="hero-caption">
              <span className="line" aria-hidden="true" />
              Curated · Bilibili · AI 大模型
            </p>
            <h1>
              翻完 <span className="brand-text">{formatNumber(meta.candidates)}</span> 个 AI 视频，
              <br />
              留下这 <span className="brand-text">{formatNumber(meta.videos)}</span> 个。
            </h1>
            <p className="hero-lede">
              少一点寻找，多一点收获。
              <br />
              把时间留给值得看的 AI 视频。
            </p>
            <div className="hero-actions">
              <a className="btn-primary" href="#discover">
                探索精选 <span aria-hidden="true">↗</span>
              </a>
              <span className="hero-hint">按质量筛选 · 带着问题学习</span>
            </div>
          </div>

          {/* 右：浅翠绿面板 */}
          <aside className="hero-aside">
            <p className="aside-caption">一个更安静的学习入口</p>
            <p className="aside-statement">
              好内容，值得被看见。
              <br />
              你的注意力，也值得被珍惜。
            </p>
            <dl className="aside-metrics">
              <div>
                <dt>通过筛选的视频</dt>
                <dd>
                  {formatNumber(meta.videos)}
                  <span className="unit">条</span>
                </dd>
              </div>
              <div>
                <dt>值得探索的主题</dt>
                <dd>
                  {formatNumber(meta.topics)}
                  <span className="unit">个</span>
                </dd>
              </div>
              <div>
                <dt>进入筛选的候选</dt>
                <dd>
                  {formatNumber(meta.candidates)}
                  <span className="unit">条</span>
                </dd>
              </div>
              <div>
                <dt>读过的弹幕</dt>
                <dd>
                  {formatNumber(meta.danmaku_rows)}
                  <span className="unit">条</span>
                </dd>
              </div>
            </dl>
          </aside>
        </div>
      </section>

      <VideoExplorer />
    </main>
  );
}

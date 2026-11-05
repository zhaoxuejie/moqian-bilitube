import Link from "next/link";

export default function NotFound() {
  return (
    <main className="shell page">
      <div className="crumbs">
        <Link href="/">精选</Link>
        <span className="sep">/</span>
        <span>未找到</span>
      </div>

      <h1>这个页面不存在</h1>
      <p className="page-lede">
        链接可能写错了，或者这个视频已经被 UP 主删除、设为私密。
        回到精选页，从确定还在的内容里挑一条吧。
      </p>

      <div className="page-actions">
        <Link className="btn" href="/">
          回到精选
        </Link>
      </div>
    </main>
  );
}

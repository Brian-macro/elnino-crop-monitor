import { Wechat } from "@/components/Common";
export default function Page() {
  const base = process.env.NEXT_PUBLIC_BASE_PATH || "";
  return (
    <main className="brian-page">
      <div className="brian-intro">
        <img
          className="brian-portrait"
          src={`${base}/images/brian-avatar.webp`}
          alt="Brian头像"
        />
        <div>
          <span className="quiet-eyebrow">关于 Brian</span>
          <h1>Brian的宏观研究笔记</h1>
          <p>宏观的本质，是跨资产套利。</p>
        </div>
      </div>
      <section className="brian-manifesto">
        <p>在不同宏观阶段，寻找赔率最高的资产与行业，</p>
        <p>在对的时间，吃到对的行业 β，</p>
        <p>最终形成属于宏观策略的 α。</p>
      </section>
      <section className="brian-subscribe">
        <div>
          <h2>与我一起，观察宏观。</h2>
          <p>扫描二维码，关注公众号。</p>
        </div>
        <Wechat large />
      </section>
    </main>
  );
}

"use client";
import { useData, Source, day, num, base } from "@/lib/data";
import { Loading, SourceState } from "./Common";
import SourcePolicy from "./SourcePolicy";
type Doc = {
  document_id: string;
  source: string;
  source_url: string;
  raw_path: string;
  sha256: string;
  publication_date: string | null;
  available_date: string;
  download_timestamp: string;
  publication_date_basis: string;
  title: string;
};
export default function Methodology() {
  const { data, error } = useData<{ sources: Source[]; documents: Doc[] }>(
    "sources",
  );
  if (!data) return <Loading error={error} />;
  return (
    <main className="document">
      <div className="page-heading">
        <div>
          <div className="eyebrow">数据与研究方法</div>
          <h1>数据说明</h1>
          <p>来源清晰，口径一致，历史版本可追溯</p>
        </div>
      </div>
      <SourcePolicy />
      <section id="research-audit">
        <h2>研究口径与适用范围</h2>
        <p>
          本站用于描述性复盘与来源浏览，尚不是可直接回测的交易策略或气候因果模型。图中价格按自然月对照，产量/库存按各国市场年度归属，两者是背景对应，不是精确收获期或同一收盘时刻对齐。
        </p>
        <p>
          ONI采用NOAA发布的ERSSTv6一位小数表；T为事后回溯首个暖季中心月，不能当作实时确认信号。现行官方ENSO诊断采用RONI。
          <a
            href="https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso/oni/v6/"
            target="_blank"
            rel="noreferrer"
          >
            NOAA定义 ↗
          </a>
        </p>
        <p>
          WASDE小麦/玉米/水稻全球用量含世界进出口差额调整，PSD页面使用各国国内消费合计，因此全球库存消费比分母并不完全相同。数据源切换是对照，不是无缝拼接。
          <a
            href="https://www.usda.gov/oce/commodity/wasde/wasde0826.pdf"
            target="_blank"
            rel="noreferrer"
          >
            WASDE脚注 ↗
          </a>
        </p>
        <p>
          期货月均排除OHLC不一致报价、未完成月份和低样本月份；至少10个有效日，国内月成交至少100手。这是最低研究样本筛选，不代表完整交易日覆盖、可成交性或换月后投资收益。
        </p>
        <p>
          前五＋其他是展示摘要，不是气候暴露排名；东南亚总量不能代替各国生育期分析。库存对价格的影响还取决于出口可用性、需求、汇率、关税与政策。大豆豆二偏进口压榨链、粳米只是稻米的一类，不能由全部中国产量直接解释其价格。
        </p>
      </section>
      <details className="technical-details">
        <summary>查看数据源状态与更新记录</summary>
        <div className="source-grid">
          {data.sources.map((s) => (
            <article className="source-item" key={s.source}>
              <h3>{s.name}</h3>
              <SourceState source={s} />
              <p>
                报告发布频率：{s.freq} · 记录：{num(s.rows_ingested, 0)}
                <br />
                最近检查：{day(s.last_checked)}
                <br />
                最近成功：{day(s.last_success)}
                <br />
                发布日期：{day(s.last_publication_date)}
                <br />
                最新观测：{day(s.latest_observation_date)}
              </p>
              <a href={s.url} target="_blank" rel="noreferrer">
                官方网站 ↗
              </a>
              {s.error && (
                <details>
                  <summary>覆盖范围与更新日志</summary>
                  <p>{s.error}</p>
                </details>
              )}
            </article>
          ))}
        </div>
      </details>
      <section>
        <h2>实产、预测与历史估计</h2>
        <p>
          Actual 仅接受明确官方实产公告。Forecast
          按报告目标年和发布时点保存。PSD 历史数据是最新修订估计，保存在独立
          Estimate 表，不能作为当年的历史预测，也不直接冒充最终实产。国家产量预测优先采用本土可比成对值，缺少本年或上年值、年度映射或产品定义未验证时，两年同时回退 PSD，并标明原因。中国玉米、大豆、糖优先 CASDE，小麦优先 CropWatch；农业展望长期预测独立保存。
          PSD近年Forecast分类是保守的年份规则，可能同时包含暂定估计和预测，不冒充源站明确的Final标签。
        </p>
        <p>
          Forecast vintage 按 source document、内容
          SHA256、目标年、地区、指标与口径保存。同一 URL
          内容改变产生新版本，不能回填到旧可得日期；报告发布日期与下载时间分别记录。As
          of 筛选使用
          available_date，未知日刊用首次观察，月刊的月末可得日期只是保守假设，见下方证据台账。
        </p>
      </section>
      <section>
        <h2>数据口径与单位</h2>
        <p>
          产量同比默认采用上年同源报告值，优先来自同一报告；上年仍为 Forecast
          时保留 Forecast 标签，不改称 Estimate 或 Actual。严格 Estimate /
          Actual
          基准可单独选择。比较限定相邻目标年、同一国家/地区、年度口径和产品定义，基准可得日期不晚于当前记录。上年产量为0时同比不适用。
        </p>
        <p>
          研究名单按作物的生产规模筛选，东南亚为独立汇总地区，成员国家可下钻。国家名称通过规范ID关联地图，保留原始来源名称。
          <a
            href={`${base}/api/asia_coverage.json`}
            target="_blank"
            rel="noreferrer"
          >
            亚洲数据覆盖台账 ↗
          </a>{" "}
          逐项列出当前数量、基准、类型、同比和缺失原因。
        </p>
        <p>
          产量 Mt；单产 t/ha；面积 Mha。Marketing Year 按起始年展示，Calendar
          Year 是自然年。稻谷 Paddy、精米
          Milled、早稻、冬小麦和未注明折算口径的食糖独立保存，无法匹配时不计算同比、共识或预测误差。
        </p>
        <p>
          Global与地区产量采用本土优先组合：各国本年和上年同时选择同一本土来源或同时回退 PSD，再分别加和计算同比。存在EU合计时剔除成员，地区研究篮子不重复加回Global。历史复盘默认采用该组合产量；PSD/WASDE供需表独立参考，不能把本土产量与USDA库存、消费当成同源供需表。WASDE
          World行仅作对照。共识不参与主序列拼接；对照区要求同年度、同口径、45天内至少两家独立机构，USDA
          PSD/WASDE只算一家。
        </p>
      </section>
      <section>
        <h2>气候与研究计算</h2>
        <p>
          ONI 暖事件使用NOAA公布的ERSSTv6一位小数表，要求≥5 个连续重叠三月季达到
          +0.5°C。历史百分位使用完整已归档指数样本的经验分布。2026 年 NOAA
          官方监测转向 RONI，本页仍保留经典 ONI
          以便历史比较。NOAA气候观测独立于农业预测来源；本站“预测”指农业产量预测，ONI阈值强度不是气候预测。
        </p>
        <p>
          Yield anomaly 和产量趋势缺口采用之前 10
          年、至少5个有效样本的线性趋势，避免使用本年和未来信息；历史原始序列可能是后来修订值。事件窗
          T±12 月以暖事件起点为 T，属于描述性复盘。
        </p>
        <p>
          World Bank 是月度现货/出口基准；国内 NBS
          是旬度调查报价，月均仅基于实际抓到的报价，不保证完整月样本。Raw
          价格按币种分轴；Indexed 使用首个共同可得月份 =100；Z-score
          按所选窗口分别标准化。相关性基于连续月均报价变化、至少12对样本，滞后正值表示海外领先中国。不填补缺月。
        </p>
      </section>
      <section>
        <h2>数据覆盖边界</h2>
        <p>
          2027 年没有可验证预测则 N/A。农业展望公开摘要仅有部分 2026 和 2035
          数量，并非完整中间年度矩阵；CropWatch历史格式与覆盖不全。历史复盘已接入内外盘期货；强麦近年、外盘稻米及部分早期年份仍缺失。地区天气、作物历、进口平价与精确市场定价比例尚无可用数据。大豆、稻米、糖的不同产品规格不能仅通过币种转换比较。
        </p>
        <p>
          网络请求或解析失败保留上次有效数据并显示 Data Stale / Partial
          Coverage。过期阈值按源更新频率设置。静态 API 随 ETL
          构建更新。预测来源每日北京时间14:17检查，检查不代表每日有新报告；历史产量、气候与价格基础库手动维护。运行状态以本页 Last Checked 和观测日期为准。
        </p>
      </section>
      <section>
        <h2>数据接口</h2>
        <p>
          {[
            "overview",
            "wheat",
            "corn",
            "soybean",
            "rice",
            "sugar",
            "elnino",
            "sources",
          ].map((k) => (
            <span key={k}>
              <a
                href={`${base}/api/${k}.json`}
                target="_blank"
                rel="noreferrer"
              >
                <code>{k}.json</code> ↗
              </a>
              {" · "}
            </span>
          ))}
        </p>
      </section>
      <section>
        <h2>原始来源台账</h2>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Source / Document</th>
                <th>Publication</th>
                <th>Available</th>
                <th>Download</th>
                <th>Date Evidence / SHA256</th>
              </tr>
            </thead>
            <tbody>
              {data.documents.map((d) => (
                <tr key={d.document_id}>
                  <td>
                    <a href={d.source_url} target="_blank" rel="noreferrer">
                      {d.source} ↗
                    </a>
                    <details>
                      <summary>{d.title || "Source file"}</summary>
                      <p>{d.raw_path}</p>
                    </details>
                  </td>
                  <td>{day(d.publication_date)}</td>
                  <td>{day(d.available_date)}</td>
                  <td>{day(d.download_timestamp)}</td>
                  <td>
                    <details>
                      <summary>{d.sha256.slice(0, 12)}…</summary>
                      <p>
                        {d.publication_date_basis}
                        <br />
                        {d.sha256}
                      </p>
                    </details>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}

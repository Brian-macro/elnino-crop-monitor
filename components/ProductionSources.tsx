import { day, sources } from '@/lib/data';
import { zhCountry } from '@/lib/labels';

export type ProductionEvidence = {
  source: string;
  configured_source?: string;
  source_url?: string;
  available_date?: string;
  source_target_year?: number;
  fallback_reason: string | null;
};

export const fallbackLabel = (reason?: string | null) => ({
  missing_local_pair: '缺少本土同口径两年数据',
  no_local_source: '尚无已验证的本土主来源',
  no_comparable_local_pairs: '该年度无可用本土成对数据',
  paddy_to_milled_crosswalk_unverified: '稻谷转精米口径未验证',
  definition_unverified: '产品或年度口径未验证',
}[reason || ''] || '本土数据尚不满足组合条件');

export default function ProductionSources({ evidence, baselineUrl }: {
  evidence: Record<string, ProductionEvidence>;
  baselineUrl?: string | null;
}) {
  return <details className="technical-details">
    <summary>各国实际产量来源与 PSD 回退</summary>
    <p>下表列出已配置本土来源的国家在所选年度的实际采用结果。其余国家沿用明确的 PSD 基线；注册来源不代表该年度已采用。</p>
    <div className="table-scroll"><table><thead><tr>
      <th>国家</th><th>实际来源</th><th>状态 / 原因</th><th>本土目标年</th>
    </tr></thead><tbody>{Object.entries(evidence).map(([country, row]) =>
      <tr key={country}><td>{zhCountry(country)}</td>
        <td>{row.source_url ? <a href={row.source_url} target="_blank" rel="noreferrer">{sources[row.source] || row.source} ↗</a> : sources[row.source] || row.source}</td>
        <td>{row.source === 'usda_psd' ? `PSD 回退：${fallbackLabel(row.fallback_reason)}` : `同源成对采用 · 可得 ${day(row.available_date)}`}</td>
        <td>{row.source_target_year ?? '—'}</td>
      </tr>)}</tbody></table></div>
    {baselineUrl && <a href={baselineUrl} target="_blank" rel="noreferrer">PSD 历史与回退基线 ↗</a>}
  </details>;
}

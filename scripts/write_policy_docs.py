"""Generate the source matrix without overwriting the reviewed stitching methodology."""
from pathlib import Path
import json
from policy import policy_bundle


def main():
    bundle = policy_bundle()
    lines = ["# 来源配置矩阵", "", f"政策版本：{bundle['version']}", "",
             "本表为配置，不代表对应年度已采用；本国同口径目标年产量优先，缺上年只影响同比。实际接入与采用见NATIONAL_SOURCE_COVERAGE.md及网页数据说明。方法见DATA_STITCHING.md。", "",
             "| 作物 | 国家/地区 | 历史基础 | 预测优先 | 注册本土来源 | 选择说明 |",
             "|---|---|---|---|---|---|"]
    for row in bundle['source_matrix']:
        lines.append(f"| {row['crop']} | {row['unit']} | {row['history']} | {row['forecast']} | {row['configured_local_source'] or '—'} | {row['fallback_reason'] or '有本国预测数据用本国预测数据，无则用PSD'} |")
    path = Path(__file__).resolve().parents[1] / 'docs' / 'SOURCE_MATRIX.md'
    path.write_text("\n".join(lines) + "\n", encoding='utf-8')
    print(path)
    actual_path = path.parents[1] / 'public' / 'api' / 'national_coverage.json'
    if actual_path.exists():
        coverage = json.loads(actual_path.read_text(encoding='utf-8'))
        lines = ['# 本国数据库实际覆盖', '', '由入库数据与首页实际选择生成；数据库存在、适配器已配置、目标年已采用是三件不同的事。', '',
                 '生成时间：' + coverage['generated_at'], '',
                 '| 作物 | 国家/地区 | 权威入口 | 本国已入库年 | 最新目标年采用 | 缺口 |',
                 '|---|---|---|---|---|---|']
        for row in coverage['rows']:
            year = max(row['years'],key=int)
            selected = row['years'][year]
            authority = f"[{row['authority']}]({row['authority_url']})" if row['authority_url'] else '待核验'
            years = ', '.join(map(str,row['available_years'])) or '无同口径记录'
            reason = selected.get('comparison_reason') or selected.get('reason') or '已采用'
            lines.append(f"| {row['crop']} | {row['country']} | {authority} | {years} | {year}: {selected['source']} | {reason} |")
        path.with_name('NATIONAL_SOURCE_COVERAGE.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')


if __name__ == '__main__':
    main()

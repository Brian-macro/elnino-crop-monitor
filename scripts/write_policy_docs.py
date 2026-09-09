"""Generate the source matrix without overwriting the reviewed stitching methodology."""
from pathlib import Path
from policy import policy_bundle


def main():
    bundle = policy_bundle()
    lines = ["# 来源配置矩阵", "", f"政策版本：{bundle['version']}", "",
             "本表为配置，不代表对应年度已采用；实际选择遵循“有本国预测数据用本国预测数据，无则用PSD”。方法见DATA_STITCHING.md。", "",
             "| 作物 | 国家/地区 | 历史基础 | 预测优先 | 注册本土来源 | 选择说明 |",
             "|---|---|---|---|---|---|"]
    for row in bundle['source_matrix']:
        lines.append(f"| {row['crop']} | {row['unit']} | {row['history']} | {row['forecast']} | {row['configured_local_source'] or '—'} | {row['fallback_reason'] or '有本国预测数据用本国预测数据，无则用PSD'} |")
    path = Path(__file__).resolve().parents[1] / 'docs' / 'SOURCE_MATRIX.md'
    path.write_text("\n".join(lines) + "\n", encoding='utf-8')
    print(path)


if __name__ == '__main__':
    main()

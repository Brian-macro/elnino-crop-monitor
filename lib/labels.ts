// 共享标签与工具：中英文映射、涨跌配色（A股约定：红涨绿跌）、数字格式化

export const CROP_ZH: Record<string, string> = {
  wheat: "小麦",
  corn: "玉米",
  soybean: "大豆",
  rice: "水稻(精米)",
  sugar: "糖(原糖)",
};

export const COUNTRY_ZH: Record<string, string> = {
  Global: "全球",
  "Southeast Asia": "东南亚",
  "EU-15": "欧盟15国",
  "EU-25": "欧盟25国",
  "Union of Soviet Socialist Repu": "苏联（历史）",
  "Cuba": "古巴",
  "France": "法国",
  "Germany, Federal Republic of": "德国",
  "Germany": "德国",
  China: "中国",
  "United States": "美国",
  Brazil: "巴西",
  Argentina: "阿根廷",
  India: "印度",
  "European Union": "欧盟",
  Russia: "俄罗斯",
  Ukraine: "乌克兰",
  Australia: "澳大利亚",
  Canada: "加拿大",
  Thailand: "泰国",
  Mexico: "墨西哥",
  "South Africa": "南非",
  Kazakhstan: "哈萨克斯坦",
  Paraguay: "巴拉圭",
  Indonesia: "印度尼西亚",
  Vietnam: "越南",
  Bangladesh: "孟加拉国",
  Philippines: "菲律宾",
  Turkey: "土耳其",
  Pakistan: "巴基斯坦",
  Japan: "日本",
  "Korea, South": "韩国",
  "Korea, North": "朝鲜",
  Mongolia: "蒙古",
  Taiwan: "中国台湾",
  "Hong Kong": "中国香港",
  Macau: "中国澳门",
  Burma: "缅甸",
  Myanmar: "缅甸",
  Cambodia: "柬埔寨",
  Laos: "老挝",
  Malaysia: "马来西亚",
  Singapore: "新加坡",
  Brunei: "文莱",
  "Timor-Leste": "东帝汶",
};

export function zhCountry(en: string): string {
  return COUNTRY_ZH[en] ?? en;
}

/** 红涨绿跌；正数红，负数绿 */
export function yoyColor(yoy: number | null): string {
  if (yoy == null) return "#666";
  if (yoy > 0) return "#c0392b";
  if (yoy < 0) return "#1e8449";
  return "#666";
}

export function fmtYoy(yoy: number | null): string {
  if (yoy == null) return "—";
  return (yoy > 0 ? "+" : "") + yoy.toFixed(1) + "%";
}

export function fmtMt(v: number | null): string {
  if (v == null) return "—";
  return v.toFixed(1);
}

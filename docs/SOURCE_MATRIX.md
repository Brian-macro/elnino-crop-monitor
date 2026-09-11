# 来源配置矩阵

政策版本：2026-09-11-national-databases-v3

本表为配置，不代表对应年度已采用；本国同口径目标年产量优先，缺上年只影响同比。实际接入与采用见NATIONAL_SOURCE_COVERAGE.md及网页数据说明。方法见DATA_STITCHING.md。

| 作物 | 国家/地区 | 历史基础 | 预测优先 | 注册本土来源 | 选择说明 |
|---|---|---|---|---|---|
| wheat | Global | usda_psd | local_composite | — | 有本国预测数据用本国预测数据，无则用PSD |
| wheat | China | usda_psd | cropwatch | cropwatch | 有本国预测数据用本国预测数据，无则用PSD |
| wheat | United States | usda_psd | us_nass | us_nass | 有本国预测数据用本国预测数据，无则用PSD |
| wheat | Brazil | usda_psd | conab | conab | 有本国预测数据用本国预测数据，无则用PSD |
| wheat | Argentina | usda_psd | bcr | bcr | 有本国预测数据用本国预测数据，无则用PSD |
| wheat | India | usda_psd | dafw | dafw | 有本国预测数据用本国预测数据，无则用PSD |
| wheat | European Union | usda_psd | ec | ec | 有本国预测数据用本国预测数据，无则用PSD |
| wheat | Russia | usda_psd | usda_psd | — | no_local_source |
| wheat | Ukraine | usda_psd | uga | uga | 有本国预测数据用本国预测数据，无则用PSD |
| wheat | Australia | usda_psd | abares | abares | 有本国预测数据用本国预测数据，无则用PSD |
| wheat | Canada | usda_psd | aafc | aafc | 有本国预测数据用本国预测数据，无则用PSD |
| wheat | Mexico | usda_psd | mx_siap | mx_siap | 有本国预测数据用本国预测数据，无则用PSD |
| wheat | South Africa | usda_psd | usda_psd | — | no_local_source |
| wheat | Kazakhstan | usda_psd | kz_bns | kz_bns | 有本国预测数据用本国预测数据，无则用PSD |
| wheat | Paraguay | usda_psd | usda_psd | — | no_local_source |
| wheat | Bangladesh | usda_psd | usda_psd | — | no_local_source |
| wheat | Pakistan | usda_psd | pk_pbs | pk_pbs | 有本国预测数据用本国预测数据，无则用PSD |
| wheat | Turkey | usda_psd | usda_psd | — | no_local_source |
| wheat | Japan | usda_psd | jp_maff | jp_maff | 有本国预测数据用本国预测数据，无则用PSD |
| wheat | United Kingdom | usda_psd | uk_defra | uk_defra | 有本国预测数据用本国预测数据，无则用PSD |
| corn | Global | usda_psd | local_composite | — | 有本国预测数据用本国预测数据，无则用PSD |
| corn | China | usda_psd | casde | casde | 有本国预测数据用本国预测数据，无则用PSD |
| corn | United States | usda_psd | us_nass | us_nass | 有本国预测数据用本国预测数据，无则用PSD |
| corn | Brazil | usda_psd | conab | conab | 有本国预测数据用本国预测数据，无则用PSD |
| corn | Argentina | usda_psd | bcr | bcr | 有本国预测数据用本国预测数据，无则用PSD |
| corn | India | usda_psd | dafw | dafw | 有本国预测数据用本国预测数据，无则用PSD |
| corn | European Union | usda_psd | ec | ec | 有本国预测数据用本国预测数据，无则用PSD |
| corn | Russia | usda_psd | usda_psd | — | no_local_source |
| corn | Ukraine | usda_psd | uga | uga | 有本国预测数据用本国预测数据，无则用PSD |
| corn | Canada | usda_psd | aafc | aafc | 有本国预测数据用本国预测数据，无则用PSD |
| corn | Mexico | usda_psd | usda_psd | mx_siap | agricultural_to_marketing_year_unverified |
| corn | South Africa | usda_psd | cec | cec | 有本国预测数据用本国预测数据，无则用PSD |
| corn | Kazakhstan | usda_psd | kz_bns | kz_bns | 有本国预测数据用本国预测数据，无则用PSD |
| corn | Paraguay | usda_psd | usda_psd | — | no_local_source |
| corn | Bangladesh | usda_psd | usda_psd | — | no_local_source |
| corn | Pakistan | usda_psd | usda_psd | pk_pbs | agricultural_to_marketing_year_unverified |
| corn | Turkey | usda_psd | usda_psd | — | no_local_source |
| corn | Korea, North | usda_psd | usda_psd | — | no_local_source |
| corn | Southeast Asia | usda_psd | local_composite | — | 有本国预测数据用本国预测数据，无则用PSD |
| rice | Global | usda_psd | local_composite | — | 有本国预测数据用本国预测数据，无则用PSD |
| rice | China | usda_psd | usda_psd | cropwatch | paddy_to_milled_crosswalk_unverified |
| rice | United States | usda_psd | usda_psd | us_nass | paddy_to_milled_crosswalk_unverified |
| rice | Brazil | usda_psd | usda_psd | conab | paddy_to_milled_crosswalk_unverified |
| rice | Argentina | usda_psd | usda_psd | — | no_local_source |
| rice | India | usda_psd | dafw | dafw | 有本国预测数据用本国预测数据，无则用PSD |
| rice | European Union | usda_psd | usda_psd | — | no_local_source |
| rice | Russia | usda_psd | usda_psd | — | no_local_source |
| rice | Paraguay | usda_psd | usda_psd | — | no_local_source |
| rice | Bangladesh | usda_psd | usda_psd | — | no_local_source |
| rice | Pakistan | usda_psd | usda_psd | — | no_local_source |
| rice | Turkey | usda_psd | usda_psd | — | no_local_source |
| rice | Japan | usda_psd | usda_psd | — | no_local_source |
| rice | Korea, South | usda_psd | usda_psd | — | no_local_source |
| rice | Korea, North | usda_psd | usda_psd | — | no_local_source |
| rice | Taiwan | usda_psd | usda_psd | tw_afa | paddy_to_milled_crosswalk_unverified |
| rice | Southeast Asia | usda_psd | local_composite | — | 有本国预测数据用本国预测数据，无则用PSD |
| soybean | Global | usda_psd | local_composite | — | 有本国预测数据用本国预测数据，无则用PSD |
| soybean | China | usda_psd | casde | casde | 有本国预测数据用本国预测数据，无则用PSD |
| soybean | United States | usda_psd | us_nass | us_nass | 有本国预测数据用本国预测数据，无则用PSD |
| soybean | Brazil | usda_psd | conab | conab | 有本国预测数据用本国预测数据，无则用PSD |
| soybean | Argentina | usda_psd | bcr | bcr | 有本国预测数据用本国预测数据，无则用PSD |
| soybean | India | usda_psd | dafw | dafw | 有本国预测数据用本国预测数据，无则用PSD |
| soybean | European Union | usda_psd | ec | ec | 有本国预测数据用本国预测数据，无则用PSD |
| soybean | Russia | usda_psd | usda_psd | — | no_local_source |
| soybean | Ukraine | usda_psd | uga | uga | 有本国预测数据用本国预测数据，无则用PSD |
| soybean | Canada | usda_psd | aafc | aafc | 有本国预测数据用本国预测数据，无则用PSD |
| soybean | Mexico | usda_psd | usda_psd | mx_siap | agricultural_to_marketing_year_unverified |
| soybean | South Africa | usda_psd | cec | cec | 有本国预测数据用本国预测数据，无则用PSD |
| soybean | Kazakhstan | usda_psd | usda_psd | — | no_local_source |
| soybean | Paraguay | usda_psd | usda_psd | — | no_local_source |
| soybean | Bangladesh | usda_psd | usda_psd | — | no_local_source |
| soybean | Turkey | usda_psd | usda_psd | — | no_local_source |
| soybean | Japan | usda_psd | jp_maff | jp_maff | 有本国预测数据用本国预测数据，无则用PSD |
| soybean | Korea, South | usda_psd | usda_psd | — | no_local_source |
| soybean | Korea, North | usda_psd | usda_psd | — | no_local_source |
| soybean | Southeast Asia | usda_psd | local_composite | — | 有本国预测数据用本国预测数据，无则用PSD |
| sugar | Global | usda_psd | local_composite | — | 有本国预测数据用本国预测数据，无则用PSD |
| sugar | China | usda_psd | casde | casde | 有本国预测数据用本国预测数据，无则用PSD |
| sugar | United States | usda_psd | usda_psd | — | no_local_source |
| sugar | Brazil | usda_psd | usda_psd | — | no_local_source |
| sugar | Argentina | usda_psd | usda_psd | — | no_local_source |
| sugar | India | usda_psd | usda_psd | — | no_local_source |
| sugar | European Union | usda_psd | usda_psd | — | no_local_source |
| sugar | Russia | usda_psd | usda_psd | — | no_local_source |
| sugar | Ukraine | usda_psd | usda_psd | — | no_local_source |
| sugar | Australia | usda_psd | usda_psd | — | no_local_source |
| sugar | Mexico | usda_psd | usda_psd | — | no_local_source |
| sugar | South Africa | usda_psd | usda_psd | — | no_local_source |
| sugar | Pakistan | usda_psd | usda_psd | — | no_local_source |
| sugar | Turkey | usda_psd | usda_psd | — | no_local_source |
| sugar | Japan | usda_psd | usda_psd | — | no_local_source |
| sugar | United Kingdom | usda_psd | usda_psd | uk_defra | refined_to_raw_crosswalk_unverified |
| sugar | Southeast Asia | usda_psd | local_composite | — | 有本国预测数据用本国预测数据，无则用PSD |

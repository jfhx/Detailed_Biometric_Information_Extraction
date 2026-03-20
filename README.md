# 详细生物信息提取项目

本项目用于从 `source_text_report.xlsx` 中读取 `source_url` 链接，抓取网页正文和正文表格内容，调用本地 `DeepSeek-V3` 模型接口进行结构化抽取，并输出英文结果表。

## 项目功能

- 输入文件必须包含列：`data_source`、`source_url`
- 自动抓取网页正文与表格，并过滤导航栏/页脚等噪音
- 调用内网模型接口：`http://159.226.80.101:1045/v1/chat/completions`
- 使用严格 JSON 提示词，支持一条 URL 输出单条或多条 `location` 记录，并严格区分“多地区共用一个汇总人数”的单条记录与“多地区分别有人数”的多条记录
- `event_type` 使用固定标准枚举，并强化总结类与单次爆发类的区分
- 输出 Excel 与 CSV 两份结果
- 字段统一英文输出
- 支持日志、异常处理、重试机制

## 输出字段

- `data_source`
- `source_url`
- `pathogen_type`
- `pathogen`
- `subtype`
- `location`
- `continent`
- `country`
- `province`
- `original_location`
- `original_country`
- `imported_location`
- `imported_country`
- `start_date`
- `start_date_year`
- `start_date_month`
- `start_date_day`
- `end_date`
- `end_date_year`
- `end_date_month`
- `end_date_day`
- `host`
- `infection_num`
- `death_num`
- `event_type`
- `original text`

## 新字段含义

- `location`：本条记录的病毒发生地/疫情发生地。必须尽量严格按照原文地点来写，可以是小地区、城市、省份、国家、边境地区、农场、营地等，不一定是国家。
- `location` 可以是单个发生地区，也可以是多个发生地区。
- 如果原文提到多个小地区，但感染人数和死亡人数只是这些小地区合在一起的一个汇总总数，没有分别给出每个小地区自己的感染人数/死亡人数，那么这几个小地区必须保留在**同一条记录**里，并在 `location` 中用分号 `;` 隔开。
- 如果原文分别给出了多个发生地区各自对应的感染人数和死亡人数，或者语义上明确支持它们是彼此独立的地点级事件记录，那么应拆分为多条记录，每条记录写一个地点自己的数据。
- 如果原文明确提到了某个发生地区，但没有给出该地区单独的感染人数/死亡人数，而该地区又应被保留为独立记录，那么该条记录的 `infection_num`、`death_num` 可以留空。
- `continent`：`location` 对应的大洲。优先使用原文；如果原文只给了小地区，模型只能在把握很高时再做推断。
- `country`：`location` 对应的国家。优先使用原文；若原文未直说，只能依据 `location` 做保守推断。
- `province`：`location` 对应的省/州/更细一级行政区。优先使用原文，没有就留空。
- `original_location`：感染初始地区，即病例在当前 `location` 被报告前，最初感染发生的地点。
- `original_country`：`original_location` 所属国家。优先使用原文，没有时才根据 `original_location` 保守推断。
- `imported_location`：由当前 `location` 继续传播到的下游地区。如果原文没有明确提及，就留空。
- `imported_country`：`imported_location` 所属国家。优先使用原文，没有时才根据 `imported_location` 保守推断。

## event_type 标准定义

`event_type` 字段只能输出以下 7 个标准值之一，不能输出别名、自由文本或自造标签：

- `sporadic_case`
- `cluster`
- `outbreak`
- `epidemic`
- `endemic`
- `pandemic`
- `Retrospective/periodic review of outbreak cases`

### event_type 各类型含义

- `sporadic_case`：散发病例。指个别、零散、无明显流行病学关联的病例，未形成局部传播。
- `cluster`：聚集性病例。指在较小空间、较短时间内出现相互关联的多个病例，例如家庭、学校、医院、村庄内聚集，但范围通常比正式暴发更小。
- `outbreak`：暴发。指在明确地区和有限时间窗口内，病例数明显高于预期，属于一次相对清晰、边界明确的急性公共卫生事件。
- `epidemic`：流行。指超出基线水平的传播已经扩展到更大人群或更广地区，例如城市、省、国家层面的持续扩散。
- `endemic`：地方性流行 / 地方病。指疾病长期稳定存在于某地，围绕相对可预期的基线波动，而不是一次短期突然升高的事件。
- `pandemic`：大流行。指跨国界、跨洲传播，涉及多个国家或大陆的广泛传播。
- `Retrospective/periodic review of outbreak cases`：总结性阶段性回顾总结爆发病例案件。指对较长时间跨度内多个病例、多个季节、多个阶段或多轮暴发进行累计式、历史性、阶段性或回顾性总结，而不是单次、短时间窗口内的独立急性事件。

### event_type 判断优先级

- 每条记录的 `event_type` 必须针对当前这条记录本身的 `location`、`infection_num`、`death_num`、时间范围和原文证据来判断。
- 不要根据病原体的一般流行特征去判断，而要根据当前记录对应的具体事件模式来判断。
- 对急性传播事件，可以粗略理解为严重程度或传播范围通常从低到高为：
  - `sporadic_case` < `cluster` < `outbreak` < `epidemic` < `pandemic`
- `endemic` 不属于一次次短期升级链条，而是长期稳定存在的背景状态。
- 如果当前记录本质上是长期累计、阶段性回顾、历史总结或多轮暴发汇总，应优先判为 `Retrospective/periodic review of outbreak cases`，而不是 `outbreak`。

### Retrospective/periodic review of outbreak cases 与 outbreak 的关键区别

- 属于 `Retrospective/periodic review of outbreak cases` 的典型特征：
  - 原文在总结较长时间范围内的累计病例或死亡，例如 `since 2001`、`from 2018 to 2025`、`to date`、`overall`、`cumulative`、`historical review`
  - 原文是在做阶段性汇总、定期回顾、事后复盘、历史累计总结
  - 记录反映的是多个时期、多个波次、多个暴发案例的合并总结，而不是单次急性事件
- 不属于 `Retrospective/periodic review of outbreak cases` 的情况：
  - 文章描述的是某个明确地点、明确时间窗口内突然出现的病例聚集
  - 文章描述的是单次、边界清晰的局部暴发事件
  - 这种情况下通常应判为 `cluster`、`outbreak` 或更高层级的 `epidemic`

### WHO 示例说明

例如这个链接：

- `https://www.who.int/emergencies/disease-outbreak-news/item/2026-DON594`

文中提到：

- `To date, since 2001 Bangladesh has documented 348 NiV disease cases, including 250 deaths, corresponding to an overall case fatality rate of 72%.`

这句话表达的是：自 2001 年以来到当前时间点，孟加拉国在很长时间跨度内累计记录的病例总数。这类证据不是一次短时间窗口中的单次暴发，而是长期累计总结。

因此，如果某条记录是根据这句累计总结生成的，那么该记录的 `event_type` 应标注为：

- `Retrospective/periodic review of outbreak cases`

而不应标注为：

- `outbreak`
- `cluster`
- `epidemic`

如果同一篇文章里同时存在“当前一次具体暴发事件”和“历史累计总结”，那么应该按记录分别判断：

- 针对当前急性事件生成的记录，使用对应的急性事件类型，例如 `outbreak`
- 针对多年累计汇总生成的记录，使用 `Retrospective/periodic review of outbreak cases`

## infection_num / death_num 对应规则

- `infection_num` 和 `death_num` 只对应当前这一条记录里的 `location`。
- 如果当前这条记录的 `location` 是由多个小地区用分号 `;` 拼接而成，那么 `infection_num` 和 `death_num` 对应的是这个**整条分号拼接 location 的汇总总数**，不是每个小地区各自都有这组人数。
- 它们默认**不对应** `original_location` 和 `imported_location`。
- 如果原文对 `original_location` 或 `imported_location` 也单独给出了感染数/死亡数，或者该地点应被单独当作一个发生地视角保留，那么要**新增一条记录**，并把那个地点放到新的 `location` 字段中。
- 如果某个链路地点需要保留为独立记录，但原文没有给它单独的人数，则该记录的 `infection_num`、`death_num` 可以为空。

## 多条记录拆分逻辑

- 一条 URL 可以输出多条记录。
- 每条记录都必须只有一个明确的 `location` 范围，但这个 `location` 范围可以是一个地点，也可以是多个共用同一组汇总人数的小地点组合。
- 同一条记录中的 `infection_num`、`death_num` 必须与该 `location` 一一对应。
- 如果原文只是列出了多个小地区，并给出了这些小地区合并后的感染人数/死亡人数总和，那么应只保留**一条记录**，把这些小地区写进同一个 `location` 字段，并用分号 `;` 隔开。
- 这种“多个小地区 + 一个汇总总数”的情况，**不能**机械拆分成多条记录，否则会把同一组汇总人数错误地重复到多个小地区上，导致总数失真。
- 只有当原文对不同地点分别给出了感染人数/死亡人数，或者明确可以判断为地点级的独立事件时，才拆分成多条记录。
- 如果多个地点里，只有一部分地点在原文中给出了单独人数，另一部分地点没有给出，那么有单独人数的地点照常填写；没有单独人数但又应保留为独立记录的地点，其 `infection_num`、`death_num` 留空即可。
- 如果文章描述了传播链，例如 `A -> B -> C`：
  - 第一条记录可以是 `location=B`，`original_location=A`，`imported_location=C`
  - 第二条记录可以是 `location=A`，`original_location=A`，`imported_location=B`
  - 第三条记录可以是 `location=C`，`original_location=A`，`imported_location=` 空
- 如果某个 URL 里有多个发生地、多个输入地、多个输出地，就继续拆分，直到每条记录里的 `location` 与 `infection_num`、`death_num` 关系清晰。

### `location` 汇总场景示例

- 原文：`As of 25 January 2026, a cumulative total of 14 confirmed cases, including nine deaths ... were reported ... from Jinka, Malle and Dasench woredas in South Ethiopia Region and Hawassa in Sidama Region.`
- 正确理解：这句话给出的是多个小地区的**合并汇总病例和死亡总数**，不是每个小地区各自的病例和死亡。
- 因此应输出为**一条记录**，例如：
  - `location = Jinka, South Ethiopia Region; Malle, South Ethiopia Region; Dasench woredas, South Ethiopia Region; Hawassa, Sidama Region`
  - `infection_num = 14`
  - `death_num = 9`
- 不应拆成四条都写 `14` 和 `9` 的记录。

## 网络说明

- 模型部署在内网环境。
- 运行前请确认代理（如 Clash）不会影响内网访问。
- 脚本会访问 `source_url` 中的网页，请确保运行节点可访问这些网址。

## 本地安装与运行

安装依赖：

```bash
pip install -r requirements.txt
```

小批量测试（推荐先跑）：

```bash
python main.py --limit 5
```

显式指定输出文件的本地运行命令：

```bash
python main.py --limit 5 --output-excel out/biometric_extracted_result.xlsx --output-csv out/biometric_extracted_result.csv --log-file out/logs/pipeline.log --endpoint http://159.226.80.101:1045/v1/chat/completions --model DeepSeek-V3
```

全量运行：

```bash
python main.py
```



本地输出默认在：

- `C:\Users\imcas\Desktop\Detailed_Biometric_Information_Extraction\out\biometric_extracted_result.xlsx`
- `C:\Users\imcas\Desktop\Detailed_Biometric_Information_Extraction\out\biometric_extracted_result.csv`
- `C:\Users\imcas\Desktop\Detailed_Biometric_Information_Extraction\out\logs\pipeline.log`



## 集群 PBS 运行

已提供两个 PBS 脚本文件：

- `run_bio_info_extract_limit5.pbs`：先试跑前 5 条 URL（用于验收提取质量）
- `run_bio_info_extract.pbs`：全量运行

脚本使用的关键路径：

- 项目目录：`/data7/sunxiuqiang/Detailed_Biometric_Information_Extraction`
- 输入文件：`/data7/sunxiuqiang/Detailed_Biometric_Information_Extraction/source_text_report.xlsx`
- 标准输出日志：`/data7/sunxiuqiang/Detailed_Biometric_Information_Extraction/task_run.log`
- 错误日志：`/data7/sunxiuqiang/Detailed_Biometric_Information_Extraction/task_error.log`



### window 转linux 系统的命令行
```bash
dos2unix run_bio_info_extract_1000.pbs
dos2unix run_bio_info_extract_gvn.pbs
```

试跑（前 5 条 URL）：
```bash
cd /data7/sunxiuqiang/Detailed_Biometric_Information_Extraction
qsub run_bio_info_extract_1000.pbs
```

全量运行：
```bash
cd /data7/sunxiuqiang/Detailed_Biometric_Information_Extraction
qsub run_bio_info_extract_gvn.pbs
```

如果你想直接在集群登录节点手动运行，也可以使用：
```bash
cd /data7/sunxiuqiang/Detailed_Biometric_Information_Extraction
python main.py \
  --input /data7/sunxiuqiang/Detailed_Biometric_Information_Extraction/source_text_report.xlsx \
  --output-excel /data7/sunxiuqiang/Detailed_Biometric_Information_Extraction/out/biometric_extracted_result.xlsx \
  --output-csv /data7/sunxiuqiang/Detailed_Biometric_Information_Extraction/out/biometric_extracted_result.csv \
  --log-file /data7/sunxiuqiang/Detailed_Biometric_Information_Extraction/out/logs/pipeline.log \
  --endpoint http://159.226.80.101:1045/v1/chat/completions \
  --model DeepSeek-V3 \
  --timeout-seconds 180 \
  --max-retries 3 \
  --request-interval-seconds 0.2
```



查看任务状态：
```bash
qstat -u sunxiuqiang
```

查看日志：
```bash
tail -f /data7/sunxiuqiang/Detailed_Biometric_Information_Extraction/task_run.log
tail -f /data7/sunxiuqiang/Detailed_Biometric_Information_Extraction/task_error.log
tail -f /data7/sunxiuqiang/Detailed_Biometric_Information_Extraction/task_run_limit5.log
tail -f /data7/sunxiuqiang/Detailed_Biometric_Information_Extraction/task_error_limit5.log
```

集群结果默认输出到：
- `/data7/sunxiuqiang/Detailed_Biometric_Information_Extraction/out/biometric_extracted_result.xlsx`
- `/data7/sunxiuqiang/Detailed_Biometric_Information_Extraction/out/biometric_extracted_result.csv`
- `/data7/sunxiuqiang/Detailed_Biometric_Information_Extraction/out/logs/pipeline.log`


## 主要文件说明
- `main.py`：命令行入口
- `biometric_extractor/pipeline.py`：主流程编排
- `biometric_extractor/fetcher.py`：网页内容抓取与正文/表格抽取
- `biometric_extractor/prompts.py`：详细英文提示词模板
- `biometric_extractor/llm_client.py`：本地模型接口调用
- `biometric_extractor/postprocess.py`：结果解析、清洗、标准化
- `biometric_extractor/io_utils.py`：输入输出处理
- `biometric_extractor/logging_utils.py`：日志初始化

## 多国家记录说明

对于单条 URL 中包含多个发生地、感染初始地区、传播地区且感染数/死亡数不同的情况，系统会输出多条记录。每条记录都以 `location` 为主键视角，并让 `infection_num`、`death_num` 只对应当前这条记录的 `location`。

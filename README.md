# 详细生物信息提取项目

本项目用于从 `source_text_report.xlsx` 中读取 `source_url` 链接，抓取网页正文和正文表格内容，调用本地 `DeepSeek-V3` 模型接口进行结构化抽取，并输出英文结果表。

## 项目功能

- 输入文件必须包含列：`data_source`、`source_url`
- 自动抓取网页正文与表格，并过滤导航栏/页脚等噪音
- 调用内网模型接口：`http://159.226.80.101:1045/v1/chat/completions`
- 使用严格 JSON 提示词，支持一条 URL 拆分多条 `location` 记录
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
- `continent`：`location` 对应的大洲。优先使用原文；如果原文只给了小地区，模型只能在把握很高时再做推断。
- `country`：`location` 对应的国家。优先使用原文；若原文未直说，只能依据 `location` 做保守推断。
- `province`：`location` 对应的省/州/更细一级行政区。优先使用原文，没有就留空。
- `original_location`：感染初始地区，即病例在当前 `location` 被报告前，最初感染发生的地点。
- `original_country`：`original_location` 所属国家。优先使用原文，没有时才根据 `original_location` 保守推断。
- `imported_location`：由当前 `location` 继续传播到的下游地区。如果原文没有明确提及，就留空。
- `imported_country`：`imported_location` 所属国家。优先使用原文，没有时才根据 `imported_location` 保守推断。

## infection_num / death_num 对应规则

- `infection_num` 和 `death_num` 只对应当前这一条记录里的 `location`。
- 它们默认**不对应** `original_location` 和 `imported_location`。
- 如果原文对 `original_location` 或 `imported_location` 也单独给出了感染数/死亡数，或者该地点应被单独当作一个发生地视角保留，那么要**新增一条记录**，并把那个地点放到新的 `location` 字段中。
- 如果某个链路地点需要保留为独立记录，但原文没有给它单独的人数，则该记录的 `infection_num`、`death_num` 可以为空。

## 多条记录拆分逻辑

- 一条 URL 可以输出多条记录。
- 每条记录都必须只有一个明确的 `location`。
- 同一条记录中的 `infection_num`、`death_num` 必须与该 `location` 一一对应。
- 如果文章描述了传播链，例如 `A -> B -> C`：
  - 第一条记录可以是 `location=B`，`original_location=A`，`imported_location=C`
  - 第二条记录可以是 `location=A`，`original_location=A`，`imported_location=B`
  - 第三条记录可以是 `location=C`，`original_location=A`，`imported_location=` 空
- 如果某个 URL 里有多个发生地、多个输入地、多个输出地，就继续拆分，直到每条记录里的 `location` 与 `infection_num`、`death_num` 关系清晰。

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
dos2unix run_bio_info_extract.pbs
dos2unix run_bio_info_extract_limit5.pbs
```

试跑（前 5 条 URL）：
```bash
cd /data7/sunxiuqiang/Detailed_Biometric_Information_Extraction
qsub run_bio_info_extract_limit5.pbs
```

全量运行：
```bash
cd /data7/sunxiuqiang/Detailed_Biometric_Information_Extraction
qsub run_bio_info_extract.pbs
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

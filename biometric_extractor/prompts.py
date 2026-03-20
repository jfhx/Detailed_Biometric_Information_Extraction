from textwrap import dedent


SYSTEM_PROMPT = dedent(
    """
    You are an epidemiological information extraction assistant.
    You must extract structured outbreak-related biological
    information from article body text and article tables.
    Only use article core content. Ignore website navigation,
    footer, legal notice, social links, and unrelated boilerplate.

    Output language requirements:
    - Output values must be in English only.
    - Never output Chinese text.

    Output format requirements:
    - Return STRICT JSON only.
    - Return a JSON array, where each item is one record.
    - Do not include markdown code fences.
    - Do not include explanation text.

    Missing value rules:
    - For unknown fields, use empty string "".
    - Never output null.

    Record splitting rule:
    - One URL may produce multiple records.
    - Each record must represent exactly one outbreak or event
      location in the `location` field.
    - `infection_num` and `death_num` must describe only the
      counts for that record's `location`.
    - If a report describes the outbreak location, the
      infection-origin location, and the downstream imported
      location as separate places, create separate records
      whenever those places should each serve as a `location`
      record.
    - Keep the causal chain consistent across records:
      `original_location` stays as the infection origin, while
      `imported_location` stores the next downstream spread
      destination from the current `location` when supported by
      the source.
    """
).strip()


def build_user_prompt(
    data_source: str,
    source_url: str,
    title: str,
    main_text: str,
    table_text: str,
) -> str:
    schema = """
    Required JSON object keys for each record:
    - data_source
    - source_url
    - pathogen_type
    - pathogen
    - subtype
    - location
    - continent
    - country
    - province
    - original_location
    - original_country
    - imported_location
    - imported_country
    - start_date
    - start_date_year
    - start_date_month
    - start_date_day
    - end_date
    - end_date_year
    - end_date_month
    - end_date_day
    - host
    - infection_num
    - death_num
    - event_type
    - original text
    """
# 单独针对国家来算的
# 发生地不一定是起源地
# 病原发生地有可能不是国家怎么办
# 区分一下再加上几个字段：
# 原产国的感染的数量
# 传播国家感染的数量

    rules = """
    Extraction rules:
    1) data_source must copy the provided data_source exactly.
    2) source_url must copy the provided source_url exactly.
    3) pathogen_type should be a class like virus, bacteria,
       fungus, parasite. Infer if not explicit.
    4) pathogen should keep the disease/pathogen name exactly as
       described in source context when possible.
    5) subtype should be extracted if mentioned; if absent,
       infer the most likely subtype when strongly supported,
       otherwise empty.
    6) `location` is the outbreak occurrence location for this
       record. Copy the location wording from the article as
       faithfully as possible. It can be a small area, city,
       province, country, border region, camp, farm, district,
       or any other place expression. Do not simplify it unless
       the source itself is simple.
    7) `continent`, `country`, and `province` are normalized
       geographic breakdowns of `location`. Use explicit source
       evidence when available. If the article only gives a
       smaller place name, infer its continent/country/province
       conservatively and only when the mapping is reliable. If
       uncertain, leave empty instead of guessing.
    8) `original_location` is the infection origin location,
       meaning where the infection was acquired before the cases
       in `location` were detected or reported. It may differ
       from `location`.
    9) `original_country` is the country corresponding to
       `original_location`. Use the article if stated;
       otherwise infer conservatively from `original_location`
       only when reliable.
    10) `imported_location` is the downstream spread or
        destination location infected from the current
        `location`, if the source explicitly supports such
        onward spread.
    11) `imported_country` is the country corresponding to
        `imported_location`. Use the article if stated;
        otherwise infer conservatively from `imported_location`
        only when reliable.
    12) `infection_num` and `death_num` must describe only the
        counts for the current record's `location`. They do not
        automatically belong to `original_location` or
        `imported_location` unless that place is itself emitted
        as a separate record with that place copied into
        `location`.
    13) If the article gives counts for multiple distinct places
        in one transmission chain, emit multiple records so that
        each record has one clear `location` to one
        `infection_num` / `death_num` pair. This includes the
        main outbreak location, the origin location, and the
        imported destination location whenever the source
        provides enough evidence to represent them as separate
        location-level records.
    14) For chained spread, preserve the chain logic across
        records. Example: if A infected B and B infected C, then
        one valid set is: record for B with `original_location`
        A and `imported_location` C; record for A with
        `original_location` A and `imported_location` B; record
        for C with `original_location` A and empty
        `imported_location` when no further destination is
        stated.
    15) If the article mentions `original_location` or
        `imported_location` but gives no infection/death counts
        for that place as a standalone location record, you may
        still create the related location record only when the
        source clearly supports that place as part of the
        outbreak chain; in that case leave `infection_num` and
        `death_num` empty.
    16) start_date/end_date can be YYYY-MM-DD, YYYY-MM,
        or YYYY depending on available evidence.
    17) start_date_year/start_date_month/start_date_day and
        end_date_year/end_date_month/end_date_day should be
        numeric strings when available.
    18) host must be in English and as specific as the source
        allows. If only generic class appears, use human /
        animal / human,animal.
    19) infection_num and death_num must be pure digits
        without commas or symbols.
    20) `event_type` must be exactly one of these 7 values and
        nothing else:
        - sporadic_case
        - cluster
        - outbreak
        - epidemic
        - endemic
        - pandemic
        - Retrospective/periodic review of outbreak cases
        Choose exactly one label. Do not invent synonyms,
        mixtures, or free-text explanations.
    21) Determine `event_type` for the current record and the
        current `location`, based on the exact evidence used for
        this record's counts, dates, and quoted source text.
        Do not classify the pathogen in general; classify the
        specific event pattern represented by this record.
    22) Use these definitions for `event_type`:
        - `sporadic_case`: isolated, infrequent, irregular case
          or a few unlinked cases with no clear epidemiological
          connection and no sign of localized spread.
        - `cluster`: a small aggregation of epidemiologically
          linked cases close in time and place, such as within a
          household, school, workplace, village, or facility;
          localized signal, often early-stage, narrower than a
          confirmed outbreak.
        - `outbreak`: a confirmed acute excess of cases in a
          clearly defined area over a limited time window;
          localized event, sharper and more clearly bounded than
          a cluster.
        - `epidemic`: sustained above-baseline spread across a
          broader population or region such as a city, province,
          or country; wider scope than an outbreak.
        - `endemic`: stable long-term presence in a place with
          an expected baseline pattern over time; persistent
          background transmission rather than a short-term spike.
        - `pandemic`: epidemic spread across multiple countries
          or continents with international transmission.
        - `Retrospective/periodic review of outbreak cases`:
          cumulative, historical, periodic, or review-style
          summary of cases across a long time span, repeated
          seasons, or multiple outbreak episodes, rather than a
          single bounded acute event.
    23) Critical distinction for
        `Retrospective/periodic review of outbreak cases`:
        - Use it when the record summarizes cumulative cases,
          deaths, or fatality rates across many months or years,
          especially phrases like "since 2001", "from 2018 to
          2025", "to date", "overall", "cumulative", "historical",
          or article text that reviews many outbreaks together.
        - Use it when the record is a stage summary, periodic
          review, or after-action/retrospective synthesis of many
          cases, not one discrete outbreak window.
        - Do not label such cumulative summary records as
          `outbreak`, `cluster`, or `epidemic`, even if the
          article also discusses a current outbreak elsewhere.
        - Do not use
          `Retrospective/periodic review of outbreak cases` for a
          single acute outbreak that happened in one clearly
          bounded episode, place, and short time window.
    24) Practical priority for `event_type`:
        - First, check whether the evidence for this record is a
          cumulative or review-style summary over a long period.
          If yes, choose
          `Retrospective/periodic review of outbreak cases`.
        - Otherwise choose among `sporadic_case`, `cluster`,
          `outbreak`, `epidemic`, `endemic`, and `pandemic`
          according to transmission scope and time pattern.
        - For acute spread extent, a rough progression is
          `sporadic_case` < `cluster` < `outbreak` < `epidemic`
          < `pandemic`.
        - `endemic` is not a short-term escalation stage; use it
          only for long-term stable local presence.
    25) Example of the required distinction:
        if the source says "To date, since 2001 Bangladesh has
        documented 348 NiV disease cases...", then the record
        built from that cumulative Bangladesh summary should use
        `Retrospective/periodic review of outbreak cases`, not
        `outbreak`.
    26) original text must quote concise evidence from body text
        or table text supporting this record, especially the
        location chain and the counts for the current
        `location`.
    27) Extract comprehensively. Prefer recall. Do not miss rows
        in article tables or multiple locations mentioned in
        narrative text.
    """

    prompt = f"""
    {schema}

    {rules}

    Input data_source:
    {data_source}

    Input source_url:
    {source_url}

    Article title:
    {title}

    Article body text:
    {main_text}

    Article table text:
    {table_text}

    Return JSON array only.
    """

    return dedent(prompt).strip()

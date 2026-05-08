# -*- coding: utf-8 -*-
"""
Project Sekai – Element Detection Rule Registry (Template)

This registry is a single-source-of-truth for chart elements used in:
  - pattern-signal detection (Step 4.1),
  - mapping tags -> official PJ Sekai elements (Step 4.2),
  - severity & SectionMetrics-based inference (Step 5.1),
  - tips generation & selection (Steps 5.2–6).

All descriptions are taken from the official element definition table
(<File>要素名.docx</File>). Numerical thresholds and detector logic must be
implemented in the detector code; here we only specify metadata and TODOs.
"""

RULES = {
    # ------------------------------------------------------------------
    # Chart meta / high-level elements
    # ------------------------------------------------------------------

    "long_duration": {
        "jp_name": "長時間",
        "category": "chart_meta",
        "description": """楽曲再生時間が2分30秒以上の譜面。""",
        "detection_notes": """TODO:
- Use song metadata (duration_sec) to flag charts whose再生時間 >= 150秒.
- Does not depend on SVG geometry; pure chart meta condition.""",
        "metric_keys": ["song_duration_sec"],
        "tag_candidates": ["long_duration"],
        "severity_hooks": ["stamina"],
    },

    "swing_rhythm": {
        "jp_name": "ハネリズム",
        "category": "rhythm",
        "description": """12分や24分などの1桁打数連打が主体の譜面。
曲の一部分におよそ4小節以上のハネリズムがある楽曲を含む。""",
        "detection_notes": """TODO:
- Detect segments where inter-note intervals correspond to 12分/24分系のスウィング。
- Require ~4小節以上の継続でこのリズムが主体になっているセクションのみをカウント。
- Use beat-grid quantization (SectionMetrics or raw beat times).""",
        "metric_keys": ["beat_intervals", "section_length_beats"],
        "tag_candidates": ["swing_rhythm", "difficult_rhythm"],
        "severity_hooks": ["rhythm"],
    },

    "irregular_meter": {
        "jp_name": "変拍子",
        "category": "rhythm",
        "description": """5拍子や7拍子等の2～4拍子を組み合わせた拍子や、
楽曲の途中で拍子が変わる可変拍子を含む譜面。""",
        "detection_notes": """TODO:
- From metadata or timing points, detect sections with 5/4, 7/4, 3/4+4/4 など複合拍子。
- Alternatively, detect non-regular beat distances in timing grid if meter info is missing.
- Mark chart if non-4拍子区間が一定長さ以上存在。""",
        "metric_keys": ["time_signature_changes", "measure_structure"],
        "tag_candidates": ["irregular_time_signature", "rhythm_complex"],
        "severity_hooks": ["rhythm"],
    },

    "scroll_speed_change": {
        "jp_name": "速度変化",
        "category": "scroll",
        "description": """通称ソフラン。
曲中で譜面内スクロール速度倍率が変化するギミックを持つ譜面。
フェードアウトで終了する楽曲など、譜面の最後のノーツから
LIVE CLEAR表示までの余白のためだけに速度変化が用いられている譜面は除く。""",
        "detection_notes": """TODO:
- Use timing/scroll metadata or inferred pixel/beat ratio from SVG to detect speed changes.
- Ignore purely-ending fade-out speed ups/downs (only余白での変化).
- Count number and strength of speed changes (bpm_delta_ratio / scroll_multiplier).""",
        "metric_keys": ["bpm_delta_ratio", "bpm_shift_count", "scroll_events"],
        "tag_candidates": ["bpm_shift", "sudden_speedup", "sudden_slowdown", "soflan"],
        "severity_hooks": ["rhythm", "readability"],
    },

    "chart_stop": {
        "jp_name": "譜面停止",
        "category": "scroll",
        "description": """曲中で譜面内スクロールが擬似停止するギミックを持つ譜面。""",
        "detection_notes": """TODO:
- Detect intervals where effective scroll speed ≈ 0 while音楽は継続。
- Use gap between y positions vs. beats; if beats progress but SVG y does not, treat as停止。
- Count停滞箇所 and their durations for severity.""",
        "metric_keys": ["chart_stop_count", "chart_stop_durations"],
        "tag_candidates": ["chart_stop", "fake_stop"],
        "severity_hooks": ["rhythm", "readability"],
    },

    "high_density": {
        "jp_name": "物量",
        "category": "density",
        "description": """流れてくるノーツの密度が高い譜面。""",
        "detection_notes": """TODO:
- Use SectionMetrics.npb / nps vs chart平均 to quantify密度。
- Flag sections where npb or nps is above certain倍率 for一定長さ。
- Aggregate over chart to decide if全体として物量傾向が強い。""",
        "metric_keys": ["npb", "nps", "avg_npb_chart", "avg_nps_chart", "peak_npb_chart", "peak_nps_chart"],
        "tag_candidates": ["stream", "high_density"],
        "severity_hooks": ["stream", "stamina"],
    },

    "localized_spike": {
        "jp_name": "局所難",
        "category": "density",
        "description": """楽曲の一部分だけ難易度が極端に高くなる譜面。""",
        "detection_notes": """TODO:
- Compare各セクションの難度指標 (npb, nps, overlap_ratio, etc.) vs chart平均。
- Identifyセクション where difficulty metrics exceedしきい値 while他区間は平常レベル。
- Use these差をもとに局所難スコアを算出。""",
        "metric_keys": ["npb", "nps", "overlap_ratio", "section_difficulty_index"],
        "tag_candidates": ["burst.start", "burst.end", "localized_difficulty"],
        "severity_hooks": ["burst", "stream"],
    },

    "low_visibility": {
        "jp_name": "視認難",
        "category": "visual",
        "description": """特殊なロングや隣接同時押しなど、
ノーツ自体の視認性が悪い譜面。""",
        "detection_notes": """TODO:
- Detect overlapping / nearly-overlapping note shapes in SVG (stacked chords, overlapping longs).
- Count隣接同時押し・特殊ロング形状 that hide other notes.
- Combine with lane_count, note_width patterns to estimate視認性。""",
        "metric_keys": ["overlap_ratio", "chord_stack_count", "thin_long_count"],
        "tag_candidates": ["low_visibility", "stacked_chords"],
        "severity_hooks": ["readability"],
    },

    "recognition_hard": {
        "jp_name": "認識難",
        "category": "visual",
        "description": """サイズの大きいノーツと小さいノーツが混合しており、
視認性が悪い配置がある譜面。""",
        "detection_notes": """TODO:
- From SVG widths, detect charts where note width variance is高く、同一タイミングに大・小ノーツ混在。
- Identifyセクション where such混在が連続し、拍単位での判断が難しい。
- Metric: spacing_variance, note_width_variance, simultaneous_big_small_chords。""",
        "metric_keys": ["note_width_variance", "spacing_variance"],
        "tag_candidates": ["recognition_hard", "visual_mismatch"],
        "severity_hooks": ["readability"],
    },

    "slide_hard": {
        "jp_name": "スライド難",
        "category": "long_note",
        "description": """左右に大きく動くロングによってコンボが途切れやすい譜面。""",
        "detection_notes": """TODO:
- Analyzeロングノーツの軌跡; measure lane movement量 andカーブ急さ。
- Countロング中のlane_cross_rate, hold_coverage combined with other notes。
- Flag charts with多くの大移動ロング or高急カーブ率。""",
        "metric_keys": ["hold_coverage", "slide_cross_lane_rate", "lane_cross_rate"],
        "tag_candidates": ["slide_complex", "longnote_movement"],
        "severity_hooks": ["slide_difficulty"],
    },

    "flick_hard": {
        "jp_name": "フリック難",
        "category": "flick",
        "description": """連続フリックや、ロング終点フリックなどによって
コンボが途切れやすい譜面。""",
        "detection_notes": """TODO:
- Countフリックノーツ密度 (flick_density) and長い連続フリック列。
- Detectロング終点に付いたフリック数 and their局所密度。
- Combine with bpm to estimateフリックの処理速度。""",
        "metric_keys": ["flick_density", "trace_flick_count", "flick_run_lengths"],
        "tag_candidates": ["flick_run", "endpoint_flick"],
        "severity_hooks": ["flick_difficulty"],
    },

    "trace_hard": {
        "jp_name": "トレース難",
        "category": "trace",
        "description": """左右に大きく動くトレースや、
タップに付随したトレースによる擬似フリック配置、擦り配置など、
トレースによってコンボが途切れやすい譜面。""",
        "detection_notes": """TODO:
- Detectトレースノーツの軌跡 and移動距離, especially横断するもの。
- Count疑似フリック型トレース, 擦り型 (連続トレースフリック)。
- Use metrics: trace_flick_count, slide_cross_lane_rate for traces specifically。""",
        "metric_keys": ["trace_flick_count", "slide_cross_lane_rate", "trace_density"],
        "tag_candidates": ["trace", "trace_flick", "trace_sweep"],
        "severity_hooks": ["trace_difficulty"],
    },

    "rhythm_hard": {
        "jp_name": "リズム難",
        "category": "rhythm",
        "description": """リズムの変化や緩急が激しく、リズムが取りにくい譜面。""",
        "detection_notes": """TODO:
- Measure variation in拍間隔, mix of 8分/12分/16分/24分, off-beat placements。
- Detectセクション where note timingはBGMのメインビートから外れがち。
- Combine features: beat_interval_variance, offbeat_ratio, syncopation_index。""",
        "metric_keys": ["beat_interval_variance", "syncopation_index"],
        "tag_candidates": ["difficult_rhythm", "offbeat_heavy"],
        "severity_hooks": ["rhythm"],
    },

    "tiny_notes": {
        "jp_name": "極小ノーツ",
        "category": "visual",
        "description": """ノーツ幅が1～2レーン分しかなく、タップミスをしやすい譜面。
幅1～2レーンのロングも含む。""",
        "detection_notes": """TODO:
- From SVG note widths, count notes (tap & long) with width≦2 lanes。
- Evaluate distribution; flag if極小ノーツが多く、特に密集して出現する区間。""",
        "metric_keys": ["tiny_note_count", "tiny_long_count"],
        "tag_candidates": ["tiny_notes"],
        "severity_hooks": ["readability"],
    },

    "trill": {
        "jp_name": "トリル",
        "category": "pattern",
        "description": """2ノーツを1組とした線対称配置が続く交互配置がある譜面。
移動トリル、交差トリル等と呼ばれる派生形も含む。""",
        "detection_notes": """TODO:
- Detect sequences A-B-A-B-... (lane pair) with length>=7打 (or configurable) andほぼ一定の間隔。
- Allow variants where中心線に対して左右対称 or nearly-symmetric。
- Extend to移動トリル/交差トリル where laneペアが時間とともに動く。""",
        "metric_keys": ["trill_sequences"],
        "tag_candidates": ["trill_vertical", "trill_moving"],
        "severity_hooks": ["trill"],
    },

    "random_run": {
        "jp_name": "乱打",
        "category": "pattern",
        "description": """ノーツ配置が対称配置になっておらず、
規則性のない連打配置がある譜面。""",
        "detection_notes": """TODO:
- In fast note sequences, compute lane-sequence entropy;高い場合を乱打とみなす。
- 排他: exclude明確なパターン (階段, トリル) を引いた残差。
- Measure run length & 密度 for severity。""",
        "metric_keys": ["run_entropy", "fast_run_density"],
        "tag_candidates": ["run_random", "jackless_stream"],
        "severity_hooks": ["stream", "stamina"],
    },

    "stairs": {
        "jp_name": "階段",
        "category": "pattern",
        "description": """階段状に配置されたノーツがある譜面。
2連階段や螺旋階段などの派生形も含む。""",
        "detection_notes": """TODO:
- Detect monotonically increasing or decreasing lane sequences (e.g. 1-2-3-4, 4-3-2-1) of一定長さ。
- Include2連階段 (同方向2回続く) and螺旋階段 (左右に折り返す階段) as variants。
- Analyze both片手階段 and両手階段 depending on lane spread。""",
        "metric_keys": ["stairs_sequences"],
        "tag_candidates": ["stair_single", "stair_spiral"],
        "severity_hooks": ["stairs"],
    },

    "jack": {
        "jp_name": "縦連",
        "category": "pattern",
        "description": """同一レーンに短い間隔でノーツが流れてくる、
3連打以上の交互連打が必要な配置がある譜面。""",
        "detection_notes": """TODO:
- Find sequences where the same lane has >=3 notes with短い間隔 (16分以上の頻度など)。
- Exclude cases where2本指で交互処理が必要ない (微縦連側に分類するなど)。
- Use per-lane jack_density for severity。""",
        "metric_keys": ["jack_sequences"],
        "tag_candidates": ["jack", "lane_trill"],
        "severity_hooks": ["jack"],
    },

    "micro_jack": {
        "jp_name": "微縦連",
        "category": "pattern",
        "description": """同一レーンに短い間隔でノーツが流れてくる、
片手2~3連打が推奨される配置がある譜面。""",
        "detection_notes": """TODO:
- Detect同一レーンの2～3連続ノーツ with間隔は短いがjackほど長くない。
- Distinguish from full縦連 by run length (2~3打) and context。
- Useful as局所的負荷 rather than長時間負荷。""",
        "metric_keys": ["micro_jack_sequences"],
        "tag_candidates": ["micro_jack"],
        "severity_hooks": ["jack"],
    },

    "kunoji": {
        "jp_name": "くの字",
        "category": "pattern",
        "description": """等間隔かつBPM100の16分より速い5連打のうち、
1打目と5打目が同時押しの折り返し階段配置がある譜面。
同時押し→縦連3打→同時押しなどのような、2本指で叩くときに
くの字配置と同様の処理が必要な配置も含む。""",
        "detection_notes": """TODO:
- Detect5打 pattern: 同時押し → 3打単押し (縦連/階段) → 同時押し, with high BPM 16分相当以上の速度。
- Allow equivalent構造 where打順は同じだがlane配置が異なるバリエーション。
- Metric: count occurrences and local density。""",
        "metric_keys": ["kunoji_patterns"],
        "tag_candidates": ["kunoji"],
        "severity_hooks": ["jack", "stairs"],
    },

    "left_right_swing": {
        "jp_name": "左右振り",
        "category": "pattern",
        "description": """左右に激しく振られる配置が原因で
実際の物量以上に忙しく感じたり、ノーツ抜けが起こりやすかったりする譜面。
出張が必要な配置も含む。""",
        "detection_notes": """TODO:
- Measure lane distance between successive notes for each hand.
- Detect patterns where hand alternates between端レーン or大きい距離で往復。
- Identify出張 (片手で大きく跨ぐ) パターン as high-cost swings。""",
        "metric_keys": ["hand_span", "swing_rate"],
        "tag_candidates": ["left_right_swing", "large_jumps"],
        "severity_hooks": ["readability", "stamina"],
    },

    "mixed_rhythm_hard": {
        "jp_name": "混フレ",
        "category": "pattern",
        "description": """HARD譜面のみ。
左右の手でそれぞれ違うリズムで叩かせるような配置がある譜面。""",
        "detection_notes": """TODO:
- For HARD対象のみ適用。
- Assign notes to左右の手 and check ifそれぞれの打鍵リズムが異なる拍パターンを持つ。
- Metric: fraction of chart where left/right have非同期リズム。""",
        "metric_keys": ["hand_rhythm_divergence"],
        "tag_candidates": ["hand_desync"],
        "severity_hooks": ["rhythm"],
    },

    "bon_odori": {
        "jp_name": "盆踊り",
        "category": "pattern",
        "description": """HARD譜面・EXPERT譜面のみ。
フリックの混ざった単押しと同時押しが連続する配置がある譜面。""",
        "detection_notes": """TODO:
- Detect sequences where単押し / 同時押し / フリックが交互に現れる特殊パターン。
- Typically上下方向 or左右方向への振りを伴う; count those runs。
- Only apply in HARD/EXPERT charts。""",
        "metric_keys": ["bon_odori_patterns"],
        "tag_candidates": ["bon_odori"],
        "severity_hooks": ["flick_difficulty", "readability"],
    },

    "moving_double_tap": {
        "jp_name": "移動2連打",
        "category": "pattern",
        "description": """EXPERT譜面のみ。
短い間隔で片手2連打が必要な配置のうち、同時押しが必要かつ
片手2連打の1打目と2打目が異なるレーンに移動する配置がある譜面。
片手2連打側がフリックの同時押しや両側同時フリックの場合も含む。
また、2連打側のノーツの片方がもう片方のノーツと半分以上重なっている場合は、
微縦連として扱う。""",
        "detection_notes": """TODO:
- In EXPERT charts, detect2連打 where同時押し＋レーン移動が含まれる片手構造。
- Distinguish from微縦連 when重なり率 < 50% (per definition)。
- Includeフリック付き2連打 variants。""",
        "metric_keys": ["moving_double_tap_sequences"],
        "tag_candidates": ["moving_double_tap"],
        "severity_hooks": ["jack", "readability"],
    },

    "hand_swap_cross": {
        "jp_name": "持ち替え・交差",
        "category": "pattern",
        "description": """EXPERT譜面・MASTER譜面のみ。
ロングや連続トレースを取った手と反対側にタップ・フリック・ロング始点・
ロング上にないトレースがあり、同一ロング・連続トレースの持ち替えまたは
交差が要求される配置がある譜面。
ロング同士の交差や合流・トレースによるロングの持ち替え誘導など、
誘導通りに叩くことで交差が発生しない配置は除く。""",
        "detection_notes": """TODO:
- Track which hand holds whichロング/トレース, and detect when同一オブジェクトを途中で持ち替え or 交差しないと取れない配置がある。
- Exclude cases where公式の誘導通りに辿れば交差不要な配置。
- Metric: count of required hand-swap events per chart。""",
        "metric_keys": ["hand_swap_events"],
        "tag_candidates": ["hand_cross", "longnote_hand_swap"],
        "severity_hooks": ["trace_difficulty", "slide_difficulty"],
    },

    "multi_press": {
        "jp_name": "多点押し",
        "category": "pattern",
        "description": """Lv.37のMASTER譜面のみ。
同時に3つ以上のノーツを叩く配置がある譜面。
判定のあるロングが3つ以上重なっているが、2本指で処理が可能な配置は除く。""",
        "detection_notes": """TODO:
- For Lv.37 MASTER only。
- Detect chords with3ノーツ以上 simultaneously that実質的に3本以上の指が必要。
- Exclude重なりロングのみで2本指処理が可能なケース。""",
        "metric_keys": ["multi_press_chords"],
        "tag_candidates": ["multi_press"],
        "severity_hooks": ["chord_complexity"],
    },

    "five_key": {
        "jp_name": "5k",
        "category": "layout",
        "description": """Lv.37のMASTER譜面・APPEND譜面のみ。
登場する鍵盤数の最大値が5つで、薬指や親指を想定運指に含む配置をもつ譜面。""",
        "detection_notes": """TODO:
- Count同時に利用されるレーン数; max == 5。
- Check譜面構造から薬指/親指使用が前提となるような鍵盤配置を推定。
- Typically multi-lane chords or高速トリルを伴う。""",
        "metric_keys": ["max_simultaneous_lanes"],
        "tag_candidates": ["five_key_layout"],
        "severity_hooks": ["layout_complexity"],
    },

    "six_key": {
        "jp_name": "6k",
        "category": "layout",
        "description": """Lv.37のMASTER譜面・APPEND譜面のみ。
登場する鍵盤数の最大値が6つで、薬指や親指を想定運指に含む配置をもつ譜面。""",
        "detection_notes": """TODO:
- Similar to 5k but max_simultaneous_lanes == 6。
- Use for charts where実質6鍵想定の配置が出現。""",
        "metric_keys": ["max_simultaneous_lanes"],
        "tag_candidates": ["six_key_layout"],
        "severity_hooks": ["layout_complexity"],
    },

    "endpoint_judgement": {
        "jp_name": "終点判定",
        "category": "long_note",
        "description": """Lv.37のMASTER譜面・APPEND譜面のみ。
終点判定をもつロングがある譜面。""",
        "detection_notes": """TODO:
- From game data or internal representation, flagロング終点に特別な判定がある箇所。
- May correlate with precise release timing requirements or終点フリック。""",
        "metric_keys": ["strict_release_longs"],
        "tag_candidates": ["endpoint_strict"],
        "severity_hooks": ["slide_difficulty"],
    },

    "personal_variance": {
        "jp_name": "個人差",
        "category": "meta",
        "description": """人によって難しさが非常に大きく分かれる譜面。""",
        "detection_notes": """TODO:
- This is primarily評価レイヤ; detection may combine複数要素の極端な組み合わせ
  (体力, 認識難, フリック難, ハネリズム等).
- Could be post-hoc tagged via player stats or manual labels rather than SVG解析のみ。""",
        "metric_keys": [],
        "tag_candidates": ["personal_variance"],
        "severity_hooks": [],
    },
}

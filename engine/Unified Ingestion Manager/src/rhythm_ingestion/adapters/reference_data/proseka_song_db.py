import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional


@dataclass
class ProsekaSongRecord:
    song_id: str
    title: str
    producer: str
    level_easy: Optional[int]
    level_normal: Optional[int]
    level_hard: Optional[int]
    level_expert: Optional[int]
    level_master: Optional[int]
    level_append: Optional[int]
    combo_expert: Optional[int]
    combo_master: Optional[int]
    combo_append: Optional[int]
    duration_ms: int
    bpm: Optional[float]


class ProsekaSongDb:
    """
    Lightweight loader for [Proseka Song DB.csv](https://onedrive.live.com/personal/d5d62a1ef303ba22/_layouts/15/doc.aspx?resid=e0a2491e-af63-4803-89d4-890211b40edf&cid=d5d62a1ef303ba22&EntityRepresentationId=9004f91b-b4a7-421b-8831-0ca524bd3ac1).
    The CSV header is:

        楽曲名,ID,ボカロP,Easy,Normal,Hard,Expert,Master,Append,
        コンボ(Expert),コンボ(Master),コンボ(Append),時間,BPM

    [1](https://onedrive.live.com/personal/d5d62a1ef303ba22/_layouts/15/doc.aspx?resid=e0a2491e-af63-4803-89d4-890211b40edf&cid=d5d62a1ef303ba22)
    """

    def __init__(self, csv_path: str) -> None:
        self._records: Dict[str, ProsekaSongRecord] = {}
        self._load(Path(csv_path))

    def _load(self, path: Path) -> None:
        with path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Skip completely empty lines
                if not row.get("ID"):
                    continue

                song_id = str(row["ID"]).strip()

                # Parse helpers
                def _int_or_none(v: str) -> Optional[int]:
                    v = v.strip()
                    if not v or v == "-":
                        return None
                    try:
                        return int(v)
                    except ValueError:
                        return None

                def _float_or_none(v: str) -> Optional[float]:
                    v = v.strip()
                    if not v:
                        return None
                    try:
                        return float(v)
                    except ValueError:
                        return None

                title = row["楽曲名"].strip()
                producer = row["ボカロP"].strip()

                level_easy = _int_or_none(row["Easy"])
                level_normal = _int_or_none(row["Normal"])
                level_hard = _int_or_none(row["Hard"])
                level_expert = _int_or_none(row["Expert"])
                level_master = _int_or_none(row["Master"])
                level_append = _int_or_none(row["Append"])

                combo_expert = _int_or_none(row["コンボ(Expert)"])
                combo_master = _int_or_none(row["コンボ(Master)"])
                combo_append = _int_or_none(row["コンボ(Append)"])

                duration_ms = self._parse_duration_to_ms(row["時間"])
                bpm = _float_or_none(row["BPM"])

                rec = ProsekaSongRecord(
                    song_id=song_id,
                    title=title,
                    producer=producer,
                    level_easy=level_easy,
                    level_normal=level_normal,
                    level_hard=level_hard,
                    level_expert=level_expert,
                    level_master=level_master,
                    level_append=level_append,
                    combo_expert=combo_expert,
                    combo_master=combo_master,
                    combo_append=combo_append,
                    duration_ms=duration_ms,
                    bpm=bpm,
                )
                self._records[song_id] = rec

    @staticmethod
    def _parse_duration_to_ms(s: str) -> int:
        """
        Parse strings like '02m 03s' into milliseconds.

        The CSV uses a 'mm m ss s' format, e.g. '02m 03s'. [1](https://onedrive.live.com/personal/d5d62a1ef303ba22/_layouts/15/doc.aspx?resid=e0a2491e-af63-4803-89d4-890211b40edf&cid=d5d62a1ef303ba22)
        If parsing fails, return 0.
        """
        if not s:
            return 0
        s = s.strip()
        minutes = 0
        seconds = 0
        try:
            # Very simple parser: split on space, expect 'Xm' 'Ys'
            parts = s.split()
            for part in parts:
                if part.endswith("m"):
                    minutes = int(part[:-1])
                elif part.endswith("s"):
                    seconds = int(part[:-1])
            total_sec = minutes * 60 + seconds
            return int(total_sec * 1000)
        except Exception:
            return 0

    def get(self, song_id: str) -> Optional[ProsekaSongRecord]:
        return self._records.get(str(song_id).strip())

    # Convenience: get combo for a given Proseka difficulty name
    def get_combo_for_difficulty(
        self, rec: ProsekaSongRecord, difficulty_name: str
    ) -> Optional[int]:
        """
        difficulty_name is expected to be one of: 'Easy','Normal','Hard',
        'Expert','Master','Append'. For Proseka, the DB only has explicit
        combo counts for Expert/Master/Append. [1](https://onedrive.live.com/personal/d5d62a1ef303ba22/_layouts/15/doc.aspx?resid=e0a2491e-af63-4803-89d4-890211b40edf&cid=d5d62a1ef303ba22)
        """
        d = difficulty_name.lower()
        if d == "expert":
            return rec.combo_expert
        if d == "master":
            return rec.combo_master
        if d == "append":
            return rec.combo_append
        # For Easy/Normal/Hard there is no combo column; return None.
        return None

    def get_level_for_difficulty(
        self, rec: ProsekaSongRecord, difficulty_name: str
    ) -> Optional[int]:
        d = difficulty_name.lower()
        if d == "easy":
            return rec.level_easy
        if d == "normal":
            return rec.level_normal
        if d == "hard":
            return rec.level_hard
        if d == "expert":
            return rec.level_expert
        if d == "master":
            return rec.level_master
        if d == "append":
            return rec.level_append
        return None
``

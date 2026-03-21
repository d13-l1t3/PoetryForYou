import json
from pathlib import Path

from sqlmodel import Session, select

from app.db import Poem, engine


def seed_poems_if_empty() -> int:
    data_path = Path(__file__).resolve().parents[1] / "data" / "poems_seed.json"
    if not data_path.exists():
        return 0

    with Session(engine) as session:
        existing = session.exec(select(Poem.id)).first()
        if existing is not None:
            return 0

        poems = json.loads(data_path.read_text(encoding="utf-8"))
        for p in poems:
            tags = ",".join(p.get("tags", []))
            session.add(
                Poem(
                    language=p["language"],
                    title=p["title"],
                    author=p["author"],
                    text=p["text"],
                    tags=tags,
                    difficulty=int(p.get("difficulty", 2)),
                )
            )
        session.commit()
        return len(poems)


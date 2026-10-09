"""GA engine. PURE module: standard library only.

Rules (see AI_RULES.md): nothing in this package may import FastAPI, Pydantic,
SQLAlchemy, or anything from app.api / app.db / app.services / app.schemas.
Plain data in, plain data out, so it can be tested and benchmarked alone.
"""

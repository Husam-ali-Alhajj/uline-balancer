"""Input contract. Mirrors contracts/problem_input.schema.json (keep them in sync)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator
from pydantic_core import InitErrorDetails, PydanticCustomError

MAX_TASKS = 50  # decision D2 (suggested value); change here and in the JSON schema
EPS = 1e-9


class Task(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=40)
    time: float = Field(gt=0)
    predecessors: list[str] = Field(default_factory=list)

    @field_validator("predecessors")
    @classmethod
    def _unique_predecessors(cls, value: list[str]) -> list[str]:
        if len(set(value)) != len(value):
            raise ValueError("predecessors must not contain duplicates")
        return value


class GASettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    population_size: int = Field(default=50, ge=10, le=500)
    max_generations: int = Field(default=100, ge=10, le=1000)
    crossover_rate: float = Field(default=0.8, ge=0, le=1)
    mutation_rate: float = Field(default=0.1, ge=0, le=1)
    elitism_count: int = Field(default=2, ge=0, le=20)
    tournament_size: int = Field(default=3, ge=2, le=20)
    stagnation_limit: int = Field(default=30, ge=1)
    seed: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _fit_population(self) -> GASettings:
        """tournament_size <= population_size and elitism_count < population_size.

        Errors are raised per field, so the API reports ga_settings.tournament_size or
        ga_settings.elitism_count in the standard error format.
        """
        errors = []
        if self.tournament_size > self.population_size:
            errors.append(("tournament_size", self.tournament_size,
                           f"must not be larger than population_size ({self.population_size})"))
        if self.elitism_count >= self.population_size:
            errors.append(("elitism_count", self.elitism_count,
                           f"must be smaller than population_size ({self.population_size})"))
        if errors:
            raise ValidationError.from_exception_data(
                "GASettings",
                [
                    InitErrorDetails(
                        type=PydanticCustomError("value_error", message), loc=(field,), input=value
                    )
                    for field, value, message in errors
                ],
            )
        return self


class ProblemInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, max_length=100)
    tasks: list[Task] = Field(min_length=1, max_length=MAX_TASKS)
    working_time_per_day: float = Field(gt=0)
    break_time_per_day: float = Field(default=0, ge=0)
    production_per_day: int = Field(ge=1)
    workers: int | None = Field(default=None, ge=1)
    ga_settings: GASettings = Field(default_factory=GASettings)

    @property
    def cycle_time(self) -> float:
        return (self.working_time_per_day - self.break_time_per_day) / self.production_per_day

    @model_validator(mode="after")
    def _check_instance(self) -> ProblemInput:
        if self.break_time_per_day >= self.working_time_per_day:
            raise ValueError("break and down time must be smaller than the working time per day")

        names = [t.name for t in self.tasks]
        duplicates = sorted({n for n in names if names.count(n) > 1})
        if duplicates:
            raise ValueError(f"duplicate task names: {', '.join(duplicates)}")

        known = set(names)
        for task in self.tasks:
            for pred in task.predecessors:
                if pred == task.name:
                    raise ValueError(f"task '{task.name}' cannot be its own predecessor")
                if pred not in known:
                    raise ValueError(f"task '{task.name}' has unknown predecessor '{pred}'")

        # cycle detection (Kahn's algorithm)
        indegree = {t.name: len(t.predecessors) for t in self.tasks}
        successors: dict[str, list[str]] = {n: [] for n in names}
        for task in self.tasks:
            for pred in task.predecessors:
                successors[pred].append(task.name)
        ready = [n for n, d in indegree.items() if d == 0]
        visited = 0
        while ready:
            current = ready.pop()
            visited += 1
            for nxt in successors[current]:
                indegree[nxt] -= 1
                if indegree[nxt] == 0:
                    ready.append(nxt)
        if visited != len(names):
            stuck = sorted(n for n, d in indegree.items() if d > 0)
            raise ValueError(f"precedence graph contains a cycle involving: {', '.join(stuck)}")

        cycle_time = self.cycle_time
        for task in self.tasks:
            if task.time > cycle_time + EPS:
                raise ValueError(
                    f"task '{task.name}' ({task.time:g} min) is longer than the cycle time "
                    f"({cycle_time:g} min)"
                )
        # IE formulas doc section 2: max(t_i) <= C <= total work content
        total_work = sum(task.time for task in self.tasks)
        if cycle_time > total_work + EPS:
            raise ValueError(
                f"the cycle time ({cycle_time:g} min) is longer than the total work content "
                f"({total_work:g} min); increase the production per day"
            )
        return self

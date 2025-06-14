"""
scenario_calculations_template.py
=================================
Standalone helper script for experimenting with scenario-table calculations **outside** the normal
Flask application.

The goal is to make it easy to:
1. Pull the raw data you need from the database (milestones, goals, scenario parameter values …).
2. Do your own calculations in plain Python / Jupyter / pandas.
3. Persist the results back into the database (``solved_parameter_values`` and, optionally,
   ``milestone_values_by_age``).

The module purposefully **does not** contain any of your business logic – it only takes care of
I/O with the existing database so that you can concentrate on the maths.

Because it is totally self-contained you can safely delete or replace it without affecting the
rest of the code-base.
"""

from __future__ import annotations

from typing import Dict, Iterable, List

from flask import Flask, current_app, has_app_context
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# ---------------------------------------------------------------
# 1. Import the existing application models
# ---------------------------------------------------------------
# They already live in *backend/app* and share the same metadata.  We only need the model
# classes – we will **NOT** start the full web server.
# ---------------------------------------------------------------

import sys
from pathlib import Path

# Add the parent directory to sys.path so we can import from app
sys.path.append(str(Path(__file__).parent.parent))

from backend.app.models.milestone import Milestone  # type: ignore
from backend.app.models.net_worth import MilestoneValueByAge  # type: ignore
from backend.app.models.goal import Goal  # type: ignore
from backend.app.models.scenario_parameter_value import ScenarioParameterValue  # type: ignore
from backend.app.models.solved_parameter_value import SolvedParameterValue  # type: ignore

from backend.app.database import db  # type: ignore  # SQLAlchemy() instance that defines `metadata`
from backend.app import create_app

# ---------------------------------------------------------------
# 2. Low-level DB helpers
# ---------------------------------------------------------------
class DBConnector:
    def __init__(self):
        # When you import this module it will connect to the *real* finance.db.  If that is not what you
        # want set this global *before* importing the module.
        self.OVERRIDE_DATABASE_URI: str | None = None

        # lazily created SQLAlchemy session factory
        self._SessionFactory: sessionmaker | None = None

    def _create_app_context(self) -> Flask:
        """Ensure a **single** application context is active on the current thread.

        • When this helper is invoked *inside* a Flask request handler there is already an
          application context on the stack – in that case we simply reuse it and *do not* push
          a second one (otherwise Flask will complain when the outer handler pops its context).

        • When called from a background script / Jupyter notebook there is *no* active context;
          we create a minimal app via `create_app()` and push a fresh context so that the model
          classes work as expected.
        """

        if has_app_context():
            # Re-use the existing context to avoid double-push/pop mismatches.
            return current_app._get_current_object()  # type: ignore[attr-defined]

        # ---- no active context → create one lazily ------------------------
        app: Flask = create_app()

        if self.OVERRIDE_DATABASE_URI:
            app.config["SQLALCHEMY_DATABASE_URI"] = self.OVERRIDE_DATABASE_URI

        app.app_context().push()
        return app

    def get_session(self) -> Session:
        """Return a *plain* SQLAlchemy session bound to the configured database.

        Unlike the Flask-SQLAlchemy `db.session` object this is a vanilla SQLAlchemy session that
        works perfectly fine outside of a Flask request/context (and across threads).  We build
        it lazily the first time the function is called.
        """

        if self._SessionFactory is None:
            # Ensure application context exists so that the metadata is bound
            app_ctx = self._create_app_context()  # returns the active app (needed for tests)

            # Reuse the same database URL that the Flask app was configured with. We avoid
            # touching `db.engine` directly here because the Flask-SQLAlchemy extension may
            # not yet have initialised an engine for *this* application instance (especially
            # during unit tests).  Pulling the URI straight from the app config is safe and
            # side-steps "current app is not registered with this SQLAlchemy instance" errors.

            from flask import current_app  # late import to keep module-level deps minimal

            engine = create_engine(current_app.config["SQLALCHEMY_DATABASE_URI"])
            self._SessionFactory = sessionmaker(bind=engine)
        return self._SessionFactory()

    # ---------------------------------------------------------------------------
    # 3. Data retrieval helpers
    # ---------------------------------------------------------------------------

    def fetch_all_data(self, session: Session, *, scenario_id: int | None = None) -> Dict[str, List]:
        """Fetch raw data from the database.

        Parameters
        ----------
        session: Session
            An active SQLAlchemy session (use :func:`get_session`).
        scenario_id: int | None
            When provided, the query will *only* return milestones/goals/… that belong to the
            given *scenario*.  When *None* everything is returned.
        """

        # Base query for milestones – most of the other tables reference those so we often want
        # the same filter.
        milestone_query = session.query(Milestone)
        if scenario_id is not None:
            milestone_query = milestone_query.filter(Milestone.scenario_id == scenario_id)
        milestones: List[Milestone] = milestone_query.all()

        milestone_ids = [m.id for m in milestones] if scenario_id is not None else None

        goals_query = session.query(Goal)
        spv_query = session.query(ScenarioParameterValue)
        mva_query = session.query(MilestoneValueByAge)

        if milestone_ids is not None:
            goals_query = goals_query.filter(Goal.milestone_id.in_(milestone_ids))
            spv_query = spv_query.filter(ScenarioParameterValue.milestone_id.in_(milestone_ids))
            mva_query = mva_query.filter(MilestoneValueByAge.milestone_id.in_(milestone_ids))

        data = {
            "milestones": milestones,
            "milestone_values_by_age": mva_query.all(),
            "goals": goals_query.all(),
            "scenario_parameter_values": spv_query.all(),
        }
        return data

    # ---------------------------------------------------------------------------
    # 4. Persistence helpers
    # ---------------------------------------------------------------------------

    def upsert_solved_parameter_values(self, session: Session, records: Iterable[dict]) -> None:
        """Insert *or* update rows in ``solved_parameter_values``.

        Each *record* must at least include the columns listed in the unique constraint on the
        table (see :pyclass:`app.models.solved_parameter_value.SolvedParameterValue`).  Any
        additional keys are ignored.

        Example
        -------
        >>> upsert_solved_parameter_values(session, [
        ...     {
        ...         "milestone_id": 1,
        ...         "scenario_id": 1,
        ...         "sub_scenario_id": 1,
        ...         "goal_parameter": "amount",
        ...         "scenario_parameter": "age_at_occurrence",
        ...         "scenario_value": "35",
        ...         "solved_value": 123456.78,
        ...     }
        ... ])
        """

        for rec in records:
            # Try to find an existing row that matches the unique constraint
            obj = (
                session.query(SolvedParameterValue)
                .filter_by(
                    milestone_id=rec["milestone_id"],
                    goal_parameter=rec["goal_parameter"],
                    scenario_parameter=rec["scenario_parameter"],
                    scenario_value=rec["scenario_value"],
                )
                .first()
            )

            if obj is None:
                # Cast to proper kwargs (ignore surplus keys)
                allowed_keys = {c.name for c in SolvedParameterValue.__table__.columns}
                kwargs = {k: v for k, v in rec.items() if k in allowed_keys}
                obj = SolvedParameterValue(**kwargs)  # type: ignore[arg-type]
            else:
                obj.solved_value = rec["solved_value"]

            session.add(obj)

        session.commit()

    def upsert_milestone_values_by_age(self, session: Session, records: Iterable[dict]) -> None:
        """Insert *or* update rows in ``milestone_values_by_age``.

        Expected *record* keys: ``milestone_id``, ``age``, ``value``.
        """

        for rec in records:
            obj = (
                session.query(MilestoneValueByAge)
                .filter_by(milestone_id=rec["milestone_id"], age=rec["age"])
                .first()
            )

            if obj is None:
                obj = MilestoneValueByAge(**rec)  # type: ignore[arg-type]
            else:
                obj.value = rec["value"]

            session.add(obj)

        session.commit()

# ---------------------------------------------------------------------------
# 5. Quick smoke test when executed as a script
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    db_connector = DBConnector()
    sess = db_connector.get_session()
    data = db_connector.fetch_all_data(sess)
    print("Milestones               :", len(data["milestones"]))
    print("Goals                    :", len(data["goals"]))
    print("Scenario Params          :", len(data["scenario_parameter_values"]))
    print("Milestone Values by Age  :", len(data["milestone_values_by_age"]))

    # Show the first milestone as a sanity check (if any)
    if data["milestones"]:
        print("\nFirst milestone:")
        print(data["milestones"][0].to_dict())

    
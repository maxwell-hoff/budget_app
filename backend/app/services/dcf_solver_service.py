def run_dcf_solver() -> None:
    """Run the DCF-based solver end-to-end.

    Importing *backend.scripts.dcf_solver* (and therefore *DBConnector*) at
    module-import time would lead to a circular import because DBConnector
    itself references ``backend.app``.  To sidestep this we do the import
    inside the function right before execution.  This keeps the public API
    unchanged while eliminating the start-up crash.
    """

    # Local import – avoids circular dependency during Flask app startup
    from backend.scripts.dcf_solver import DCFSolverRunner  # noqa: WPS433 (allowed here)

    runner = DCFSolverRunner()
    runner.run() 
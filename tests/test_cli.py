from egeo.cli import build_parser


def test_optimize_command_parser():
    parser = build_parser()

    args = parser.parse_args([
        "optimize",
        "example.md"
    ])

    assert args.cmd == "optimize"
    assert args.input == "example.md"
    assert args.out_dir == "geo-output"
    assert args.schema_type == "Article"
    assert args.format == "markdown"
    assert args.runtime == "python"


def test_optimize_command_custom_options():
    parser = build_parser()

    args = parser.parse_args([
        "optimize",
        "content.md",
        "--out-dir",
        "output",
        "--schema-type",
        "FAQPage",
        "--format",
        "html",
        "--runtime",
        "other"
    ])

    assert args.input == "content.md"
    assert args.out_dir == "output"
    assert args.schema_type == "FAQPage"
    assert args.format == "html"
    assert args.runtime == "other"


def test_loop_mark_records_owner_application(tmp_path, monkeypatch, capsys):
    import shutil
    from datetime import datetime, timedelta, timezone
    from pathlib import Path

    from egeo import decide, workspace
    from egeo.cli import main

    monkeypatch.setenv("EGEO_HOME", str(tmp_path))
    shutil.copy(Path(__file__).resolve().parents[1] / "examples" / "project.yaml", tmp_path / workspace.PROJECT_CONFIG_NAME)
    workspace.bootstrap(tmp_path)
    project = workspace.load_project_config(tmp_path)
    now = datetime.now(timezone.utc)
    query = project["queries"][0]["text"]
    for days in (3, 2, 1):
        decide.append_jsonl(
            decide._query_stream(tmp_path, query),
            {"ts": (now - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ"), "query": query, "target_position": None},
        )

    assert main(["loop", "decide"]) == 0
    out = capsys.readouterr().out
    proposal_id = decide.load_ledger(tmp_path)[0]["id"]
    assert f"egeo loop mark {proposal_id} applied" in out

    assert main(["loop", "mark", proposal_id, "applied", "--note", "PR 1"]) == 0
    assert "-> applied" in capsys.readouterr().out
    state = decide.ledger_state(decide.load_ledger(tmp_path))[0]
    assert state["status"] == "applied" and state["applied_ts"] is not None

    assert main(["loop", "mark", "missing-id", "applied"]) == 1
    assert "no proposal with id" in capsys.readouterr().err
    assert main(["loop", "mark", proposal_id, "applied", "--at", "not-a-date"]) == 1
    assert len(decide.load_ledger(tmp_path)) == 2

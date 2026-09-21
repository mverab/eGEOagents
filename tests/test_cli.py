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


def test_rank_command_parser():
    parser = build_parser()
    args = parser.parse_args(["rank", "--limit", "2"])
    assert args.cmd == "rank"
    assert args.limit == 2

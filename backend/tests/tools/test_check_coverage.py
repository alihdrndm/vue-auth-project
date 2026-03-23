import check_coverage


def report(files: dict[str, tuple[int, int, int, int]]) -> check_coverage.Report:
    return {
        "files": {
            path: {
                "summary": {
                    "num_statements": statements,
                    "covered_lines": covered,
                    "num_branches": branches,
                    "covered_branches": covered_branches,
                }
            }
            for path, (statements, covered, branches, covered_branches) in files.items()
        }
    }


def test_files_are_grouped_by_package_under_src() -> None:
    packages = check_coverage.totals_by_package(
        report({"src/einvoice/a.py": (10, 9, 4, 4), "src\\einvoice\\b.py": (10, 10, 0, 0)})
    )
    assert packages["einvoice"].line_percent() == 95.0
    assert packages["einvoice"].branch_percent() == 100.0


def test_einvoice_needs_90_percent_lines_and_85_percent_branches() -> None:
    packages = check_coverage.totals_by_package(report({"src/einvoice/a.py": (100, 89, 100, 84)}))
    assert check_coverage.problems(packages) == [
        "einvoice: lines 89.0% < 90%",
        "einvoice: branches 84.0% < 85%",
    ]


def test_other_packages_need_75_percent_lines() -> None:
    packages = check_coverage.totals_by_package(
        report({"src/eingang/a.py": (100, 74, 10, 0), "src/accounts/a.py": (100, 75, 10, 0)})
    )
    assert check_coverage.problems(packages) == ["eingang: lines 74.0% < 75%"]


def test_empty_packages_pass() -> None:
    packages = check_coverage.totals_by_package(report({"src/llm/__init__.py": (0, 0, 0, 0)}))
    assert check_coverage.problems(packages) == []


def test_package_of_splits_both_separators_on_every_os() -> None:
    windows_path = chr(92).join(["src", "einvoice", "detect.py"])
    assert check_coverage.package_of(windows_path) == "einvoice"
    assert check_coverage.package_of("src/eingang/settings.py") == "eingang"

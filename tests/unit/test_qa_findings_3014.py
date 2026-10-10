"""
Regression tests for the v3.0.14 QA-report fixes (findings SDK-01 .. SDK-46).

Each test is named after the finding it pins. The CLI tests run the real
`main()` in-process, with HOME pointed at a temp directory: that is where
`workspace create` writes by default.
"""

import copy
import json
import os
import sys
from decimal import Decimal
from pathlib import Path

import pytest

import mediaplanpy
from mediaplanpy import cli
from mediaplanpy.exceptions import MediaPlanError
from mediaplanpy.models import Campaign, MediaPlan
from mediaplanpy.workspace import WorkspaceManager

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _plan_dict(**campaign_overrides):
    campaign = {
        "id": "campaign_qa",
        "name": "QA Campaign",
        "start_date": "2026-01-01",
        "end_date": "2026-03-31",
        "budget_total": 250000,
        "budget_currency": "USD",
    }
    campaign.update(campaign_overrides)
    return {
        "meta": {
            "id": "mediaplan_qa",
            "schema_version": "v3.0",
            "name": "QA plan",
            "created_by_name": "qa",
            "created_at": "2026-01-01T00:00:00Z",
        },
        "campaign": campaign,
        "lineitems": [
            {
                "id": "li_1",
                "name": "LI 1",
                "start_date": "2026-01-01",
                "end_date": "2026-02-01",
                "cost_total": 10000,
            }
        ],
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("USERPROFILE", raising=False)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _run_cli(monkeypatch, *argv):
    monkeypatch.setattr(sys, "argv", ["mediaplanpy", *argv])
    return cli.main()


def _create_workspace(monkeypatch, *extra):
    assert _run_cli(monkeypatch, "workspace", "create", "--name", "QA", *extra) == 0
    settings = next((Path(os.environ["HOME"]) / "mediaplanpy").glob("*_settings.json"))
    return json.loads(settings.read_text()), settings


class TestCLI:

    def test_sdk01_table_output_reads_prefixed_columns(self, home, monkeypatch, capsys):
        config, settings = _create_workspace(monkeypatch)
        manager = WorkspaceManager()
        manager.load(workspace_path=str(settings))
        MediaPlan.from_dict(_plan_dict()).save(manager)
        capsys.readouterr()

        assert (
            _run_cli(monkeypatch, "list", "campaigns", "--workspace_id", config["workspace_id"])
            == 0
        )
        row = next(line for line in capsys.readouterr().out.splitlines() if "campaign_qa" in line)
        assert "$250,000" in row and "2026-01-01" in row and "2026-03-31" in row

        assert (
            _run_cli(monkeypatch, "list", "mediaplans", "--workspace_id", config["workspace_id"])
            == 0
        )
        row = next(line for line in capsys.readouterr().out.splitlines() if "mediaplan_qa" in line)
        assert "v3.0" in row and row.rstrip().endswith("1")  # line item count

    def test_sdk02_database_block_uses_backend_keys(self, home, monkeypatch):
        config, _ = _create_workspace(monkeypatch, "--database", "true")
        database = config["database"]
        assert database["enabled"] is True
        assert {"table_name", "username", "password_env_var"} <= set(database)
        assert not {"table", "user", "password"} & set(database)

    def test_sdk17_validate_missing_workspace_exits_3(self, home, monkeypatch):
        assert (
            _run_cli(monkeypatch, "workspace", "validate", "--workspace_id", "workspace_nope") == 3
        )

    def test_sdk36_plan_files_found_under_mediaplans(self, tmp_path):
        (tmp_path / "mediaplans").mkdir()
        (tmp_path / "mediaplans" / "a.json").write_text("{}")
        (tmp_path / "legacy.json").write_text("{}")
        assert [p.name for p in cli._plan_files(tmp_path, "json")] == ["a.json", "legacy.json"]

    def test_sdk45_explicit_path_is_honoured(self, home, monkeypatch):
        # "./workspace.json" was the argparse default, and the one value ignored
        assert _run_cli(monkeypatch, "workspace", "create", "--path", "./workspace.json") == 0
        assert (home / "workspace.json").exists()


# ---------------------------------------------------------------------------
# Models, formulas, storage
# ---------------------------------------------------------------------------


class TestModels:

    def test_sdk05_validate_model_with_no_objective(self):
        campaign = Campaign(
            id="c", name="c", start_date="2026-01-01", end_date="2026-02-01", budget_total=1
        )
        assert campaign.objective is None
        assert isinstance(campaign.validate_model(), list)

    def test_sdk16_delete_lineitem_validate_true(self):
        plan = MediaPlan.from_dict(_plan_dict())
        assert plan.delete_lineitem("li_1", validate=True) is True
        assert plan.lineitems == []

    def test_sdk23_recalculation_reaches_every_downstream_metric(self):
        data = _plan_dict()
        data["dictionary"] = {
            "standard_metrics": {
                "metric_clicks": {
                    "formula_type": "conversion_rate",
                    "base_metric": "metric_impressions",
                },
                "metric_conversions": {
                    "formula_type": "conversion_rate",
                    "base_metric": "metric_clicks",
                },
            }
        }
        data["lineitems"][0].update(
            metric_impressions=2000000, metric_clicks=40000, metric_conversions=400
        )
        lineitem = MediaPlan.from_dict(data).lineitems[0]
        result = lineitem.set_metric_value("cost_total", Decimal("20000"))
        assert result["metric_impressions"] == pytest.approx(Decimal("4000000"))
        assert result["metric_clicks"] == pytest.approx(Decimal("80000"))
        assert result["metric_conversions"] == pytest.approx(Decimal("800"))

    def test_sdk27_new_custom_metric_keeps_dictionary_valid(self):
        plan = MediaPlan.from_dict(_plan_dict())
        plan.select_metric_formula("metric_custom3", formula_type="cost_per_unit")
        from mediaplanpy.models.dictionary import CustomMetricConfig

        assert isinstance(plan.dictionary.custom_metrics["metric_custom3"], CustomMetricConfig)
        assert plan.dictionary.is_field_enabled("metric_custom3") is True
        plan.validate_model()

    def test_sdk39_is_field_enabled_always_bool(self):
        plan = MediaPlan.from_dict(_plan_dict())
        assert (
            plan.dictionary is None or plan.dictionary.is_field_enabled("metric_custom1") is False
        )
        from mediaplanpy.models.dictionary import Dictionary

        empty = Dictionary()
        assert empty.is_field_enabled("metric_custom1") is False
        assert empty.is_field_enabled("cost_custom1") is False

    def test_sdk32_constant_formula_does_not_inherit_parameters(self):
        from mediaplanpy.excel.importer import _build_metric_formulas_from_import

        line_item = {
            "cost_total": 1000.0,
            "metric_impressions": 100.0,
            "metric_reach": 50.0,
            "metric_formulas": {
                "metric_impressions": {
                    "formula_type": "power_function",
                    "base_metric": "cost_total",
                },
                "metric_reach": {"formula_type": "constant"},
            },
        }
        formulas = _build_metric_formulas_from_import(
            line_item, {"metric_impressions_param1": 0.5}, {}
        )
        assert formulas["metric_impressions"]["parameter1"] == 0.5
        assert "parameter1" not in formulas["metric_reach"]


class TestStorage:

    @pytest.fixture
    def workspace(self, tmp_path):
        manager = WorkspaceManager()
        _, path = manager.create(
            settings_path_name=str(tmp_path), storage_path_name=str(tmp_path / "store")
        )
        manager.load(workspace_path=path)
        return manager

    def test_sdk22_v2_plan_is_migrated_on_load(self, workspace, tmp_path):
        data = json.loads((FIXTURES / "mediaplan_v2_migration.json").read_text())
        plans_dir = tmp_path / "store" / "mediaplans"
        plans_dir.mkdir(parents=True)
        (plans_dir / f"{data['meta']['id']}.json").write_text(json.dumps(data))

        plan = MediaPlan.load(workspace, media_plan_id=data["meta"]["id"])
        assert plan.campaign.target_audiences, "v2 audience fields were not migrated"

    def test_sdk12_delete_unsaved_plan_reports_success(self, workspace):
        result = MediaPlan.from_dict(_plan_dict()).delete(workspace)
        assert result["success"] is True
        assert result["files_found"] == 0

    def test_sdk40_list_campaigns_has_no_sort_helper(self, workspace):
        MediaPlan.from_dict(_plan_dict()).save(workspace)
        for include_stats in (True, False):
            df = workspace.list_campaigns(include_stats=include_stats, return_dataframe=True)
            assert "meta_is_current_sort" not in df.columns

    def test_sdk46_migrate_media_plan_defaults_to_current(self, workspace):
        data = json.loads((FIXTURES / "mediaplan_v2_migration.json").read_text())
        migrated = workspace.migrate_media_plan(data)
        assert migrated["meta"]["schema_version"].lstrip("v") == mediaplanpy.__schema_version__

    def test_sdk24_strings_map_to_text(self):
        from mediaplanpy.storage.schema_columns import python_type_to_sql

        assert python_type_to_sql(str) == "TEXT"

    def test_sdk35_unknown_extension_raises_value_error(self):
        from mediaplanpy.storage.formats import get_format_handler_instance

        with pytest.raises(ValueError):
            get_format_handler_instance("plan.txt")


# ---------------------------------------------------------------------------
# Exceptions and workspace
# ---------------------------------------------------------------------------


class TestExceptions:

    @pytest.mark.parametrize(
        "name",
        [
            "MediaPlanNotFoundError",
            "SQLQueryError",
            "UnsupportedVersionError",
            "VersionCompatibilityError",
        ],
    )
    def test_sdk07_exported_at_package_level(self, name):
        assert issubclass(getattr(mediaplanpy, name), MediaPlanError)
        assert name in mediaplanpy.__all__

    def test_sdk08_sql_query_error_is_media_plan_error(self):
        assert issubclass(mediaplanpy.SQLQueryError, MediaPlanError)

    def test_sdk26_loader_raises_exported_classes(self):
        from mediaplanpy.workspace import loader

        assert loader.WorkspaceInactiveError is mediaplanpy.WorkspaceInactiveError
        assert loader.FeatureDisabledError is mediaplanpy.FeatureDisabledError

    def test_sdk37_invalid_file_raises_validation_error(self, tmp_path):
        from mediaplanpy.exceptions import WorkspaceValidationError

        path = tmp_path / "ws.json"
        path.write_text(json.dumps({"workspace_name": "no id"}))
        with pytest.raises(WorkspaceValidationError):
            WorkspaceManager().load(workspace_path=str(path))

    def test_sdk38_disabled_database_not_upgraded(self, tmp_path):
        from mediaplanpy.workspace.upgrader import WorkspaceUpgrader

        manager = WorkspaceManager()
        _, path = manager.create(settings_path_name=str(tmp_path))
        manager.load(workspace_path=path)
        assert manager.get_resolved_config()["database"]["enabled"] is False
        assert WorkspaceUpgrader(manager)._should_upgrade_database() is False


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


class TestSchema:

    def test_sdk25_currency_pattern_matches_model(self):
        from mediaplanpy import schema

        bad = _plan_dict(budget_currency="Dollars")
        assert any("budget_currency" in e for e in schema.validate(bad))
        assert schema.validate(_plan_dict(budget_currency="usd")) == []

    def test_sdk33_manager_defaults_to_current_version(self):
        from mediaplanpy import SchemaManager

        assert "target_audiences" in SchemaManager.get_schema("campaign")["properties"]

    def test_sdk34_validate_mediaplan_returns_bool(self):
        from mediaplanpy import SchemaManager, schema

        assert SchemaManager.validate_against_schema(schema.get_example(), "mediaplan") is True
        assert SchemaManager.validate_against_schema({"meta": {}}, "mediaplan") is False

    def test_sdk41_bundle_for_unsupported_version_raises(self):
        from mediaplanpy.schema import get_schema_bundle

        with pytest.raises(FileNotFoundError):
            get_schema_bundle("1.0")

    def test_sdk42_dictionary_schema_loadable_by_filename(self):
        from mediaplanpy.schema import default_registry

        for filename in default_registry.load_all_schemas("3.0"):
            assert default_registry.load_schema("3.0", filename)

    def test_sdk44_not_found_message_hides_install_path(self):
        from mediaplanpy import schema

        with pytest.raises(FileNotFoundError) as excinfo:
            schema.get_schema("mediaplan", version="1.0")
        assert os.path.dirname(mediaplanpy.__file__) not in str(excinfo.value)


def test_sdk19_documented_extras_exist():
    tomllib = pytest.importorskip("tomllib")
    pyproject = Path(__file__).parent.parent.parent / "pyproject.toml"
    extras = tomllib.loads(pyproject.read_text())["project"]["optional-dependencies"]
    assert {"database", "excel", "parquet", "s3"} <= set(extras)

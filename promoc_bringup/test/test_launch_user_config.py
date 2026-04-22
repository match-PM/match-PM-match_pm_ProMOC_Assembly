"""Tests for user-config loading on the messstand branch."""

from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
PROMOC_BRINGUP_ROOT = ROOT / "promoc_bringup"
if str(PROMOC_BRINGUP_ROOT) not in sys.path:
    sys.path.insert(0, str(PROMOC_BRINGUP_ROOT))

from promoc_bringup.launch_utils import get_config_path, load_user_config, load_yaml_config  # noqa: E402


def test_load_user_config_maps_legacy_user_keys():
    tmp_root = ROOT / "camera_nodes" / "test" / "fixtures" / "_tmp_mtf" / "legacy_user_config"
    tmp_root.mkdir(exist_ok=True)
    config_dir = tmp_root / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "user_config.yaml").write_text(
        "\n".join(
            [
                "user:",
                "  name: LegacyStudent",
                "  measurement_base_path: ~/MessungenLegacy",
            ]
        ),
        encoding="utf-8",
    )

    config = load_user_config(str(tmp_root))

    assert config["measurement"]["operator"] == "LegacyStudent"
    assert config["measurement"]["base_path"] == "~/MessungenLegacy"


def test_load_user_config_keeps_raw_capture_defaults_overridable():
    tmp_root = ROOT / "camera_nodes" / "test" / "fixtures" / "_tmp_mtf" / "raw_user_config"
    tmp_root.mkdir(exist_ok=True)
    config_dir = tmp_root / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "user_config.yaml").write_text(
        "\n".join(
            [
                "mtf:",
                "  use_raw_capture: false",
                "  capture_required_raw: false",
            ]
        ),
        encoding="utf-8",
    )

    config = load_user_config(str(tmp_root))

    assert config["mtf"]["use_raw_capture"] is False
    assert config["mtf"]["capture_required_raw"] is False


def test_ids_camera_profile_starts_in_raw_bayer_mode():
    camera_cfg_path = get_config_path(
        str(ROOT / "promoc_bringup"),
        "cameras/ids_u3_3800cp_hq.yaml",
    )
    config, error = load_yaml_config(camera_cfg_path)

    assert error is None
    assert config["camera_params"]["pixel_format"] == "BayerRG12"
    assert config["camera_params"]["mtf_capture_pixel_format"] == "BayerRG12"
    assert config["camera_params"]["mtf_capture_bayer_pattern"] == "RGGB"

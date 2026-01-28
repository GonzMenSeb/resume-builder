"""Tests for configuration module."""

from pathlib import Path

import pytest

from resume_generator.config import (
    COLOR_PALETTE_VALUES,
    ClaudeModel,
    ColorPalette,
    ResumeLanguage,
    Settings,
    find_config_file,
    get_default_config_template,
    get_settings,
    load_yaml_config,
)


class TestColorPalette:
    """Tests for ColorPalette enum."""

    def test_all_palette_values_exist(self) -> None:
        for palette in ColorPalette:
            assert palette in COLOR_PALETTE_VALUES

    def test_palette_values_are_valid_hex(self) -> None:
        for palette, (primary, secondary) in COLOR_PALETTE_VALUES.items():
            assert primary.startswith("#"), f"{palette}: primary must start with #"
            assert secondary.startswith("#"), f"{palette}: secondary must start with #"
            assert len(primary) == 7, f"{palette}: primary must be 7 chars"
            assert len(secondary) == 7, f"{palette}: secondary must be 7 chars"

    def test_classic_palette_values(self) -> None:
        primary, secondary = COLOR_PALETTE_VALUES[ColorPalette.CLASSIC]
        assert primary == "#2C3E50"
        assert secondary == "#3498DB"

    def test_burgundy_palette_values(self) -> None:
        primary, _ = COLOR_PALETTE_VALUES[ColorPalette.BURGUNDY]
        assert primary == "#800020"


class TestSettings:
    """Tests for Settings class."""

    def test_default_settings(self) -> None:
        settings = Settings()
        assert settings.max_pages == 1
        assert settings.max_bullet_words == 25
        assert settings.color_palette == ColorPalette.CLASSIC
        assert settings.claude_model == ClaudeModel.SONNET
        assert settings.output_language == ResumeLanguage.EN

    def test_custom_max_pages(self) -> None:
        settings = Settings(max_pages=2)
        assert settings.max_pages == 2

    def test_max_pages_validation(self) -> None:
        with pytest.raises(ValueError):
            Settings(max_pages=0)
        with pytest.raises(ValueError):
            Settings(max_pages=4)

    def test_custom_max_bullet_words(self) -> None:
        settings = Settings(max_bullet_words=30)
        assert settings.max_bullet_words == 30

    def test_max_bullet_words_validation(self) -> None:
        with pytest.raises(ValueError):
            Settings(max_bullet_words=5)
        with pytest.raises(ValueError):
            Settings(max_bullet_words=60)

    def test_get_effective_colors_default_palette(self) -> None:
        settings = Settings()
        primary, secondary = settings.get_effective_colors()
        assert primary == "#2C3E50"
        assert secondary == "#3498DB"

    def test_get_effective_colors_custom_palette(self) -> None:
        settings = Settings(color_palette=ColorPalette.BURGUNDY)
        primary, secondary = settings.get_effective_colors()
        assert primary == "#800020"
        assert secondary == "#4A4A4A"

    def test_get_effective_colors_custom_colors(self) -> None:
        settings = Settings(primary_color="#FF5500", secondary_color="#0055FF")
        primary, secondary = settings.get_effective_colors()
        assert primary == "#FF5500"
        assert secondary == "#0055FF"

    def test_custom_colors_override_palette(self) -> None:
        settings = Settings(
            color_palette=ColorPalette.BURGUNDY,
            primary_color="#AABBCC",
            secondary_color="#DDEEFF",
        )
        primary, secondary = settings.get_effective_colors()
        assert primary == "#AABBCC"
        assert secondary == "#DDEEFF"


class TestFindConfigFile:
    """Tests for find_config_file function."""

    def test_find_config_file_not_found(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            "resume_generator.config.CONFIG_SEARCH_PATHS",
            [tmp_path / "nonexistent.yaml"],
        )
        result = find_config_file()
        assert result is None

    def test_find_config_file_in_current_dir(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        config_file = tmp_path / "resume-gen.yaml"
        config_file.write_text("max_pages: 2")
        monkeypatch.chdir(tmp_path)

        monkeypatch.setattr("resume_generator.config.CONFIG_SEARCH_PATHS", [config_file])

        result = find_config_file()
        assert result == config_file

    def test_find_config_file_returns_first_match(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        first_config = tmp_path / "first.yaml"
        second_config = tmp_path / "second.yaml"
        first_config.write_text("max_pages: 1")
        second_config.write_text("max_pages: 2")

        monkeypatch.setattr("resume_generator.config.CONFIG_SEARCH_PATHS", [first_config, second_config])

        result = find_config_file()
        assert result == first_config


class TestLoadYamlConfig:
    """Tests for load_yaml_config function."""

    def test_load_nonexistent_file(self) -> None:
        result = load_yaml_config(Path("/nonexistent/path.yaml"))
        assert result == {}

    def test_load_none_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("resume_generator.config.find_config_file", lambda: None)
        result = load_yaml_config(None)
        assert result == {}

    def test_load_valid_yaml(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.yaml"
        config_file.write_text("max_pages: 2\nmax_bullet_words: 30")

        result = load_yaml_config(config_file)
        assert result["max_pages"] == 2
        assert result["max_bullet_words"] == 30

    def test_load_empty_yaml(self, tmp_path: Path) -> None:
        config_file = tmp_path / "empty.yaml"
        config_file.write_text("")

        result = load_yaml_config(config_file)
        assert result == {}


class TestGetSettings:
    """Tests for get_settings factory function."""

    def test_get_settings_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("resume_generator.config.find_config_file", lambda: None)
        settings = get_settings()
        assert settings.max_pages == 1

    def test_get_settings_with_config_file(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.yaml"
        config_file.write_text("max_pages: 3\ncolor_palette: navy")

        settings = get_settings(config_path=config_file)
        assert settings.max_pages == 3
        assert settings.color_palette == ColorPalette.NAVY

    def test_get_settings_partial_config(self, tmp_path: Path) -> None:
        config_file = tmp_path / "partial.yaml"
        config_file.write_text("max_pages: 2")

        settings = get_settings(config_path=config_file)
        assert settings.max_pages == 2
        assert settings.max_bullet_words == 25  # default


class TestGetDefaultConfigTemplate:
    """Tests for get_default_config_template function."""

    def test_template_contains_key_settings(self) -> None:
        template = get_default_config_template()
        assert "max_pages:" in template
        assert "max_bullet_words:" in template
        assert "color_palette:" in template
        assert "claude_model:" in template
        assert "output_language:" in template

    def test_template_is_valid_yaml(self, tmp_path: Path) -> None:
        template = get_default_config_template()
        config_file = tmp_path / "test.yaml"
        config_file.write_text(template)

        result = load_yaml_config(config_file)
        assert isinstance(result, dict)
        assert result["max_pages"] == 1
        assert result["max_bullet_words"] == 25

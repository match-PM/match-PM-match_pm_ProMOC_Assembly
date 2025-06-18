import os
import sys
from typing import Any


class PMCLibLoader:
    """Smart loader für PMCLib - automatische Erkennung von lokaler vs. Mock PMCLib"""

    def __init__(self):
        self.use_mock = False
        self.pmclib_source = "unknown"
        self._setup_paths()

    def _setup_paths(self):
        """Setup der Python-Pfade für PMCLib"""
        # Aktueller Ordner
        current_dir = os.path.dirname(os.path.abspath(__file__))

        # Pfad zur lokalen match_pm_xBot PMCLib
        local_pmclib_path = os.path.join(current_dir, 'match_pm_xBot')

        # Prüfe ob lokale PMCLib verfügbar ist
        if os.path.exists(local_pmclib_path) and os.path.isdir(local_pmclib_path):
            # Prüfe ob es eine echte Installation ist (nicht nur leerer Ordner)
            xbot_commands_file = os.path.join(
                local_pmclib_path, 'xbot_commands.py')
            if os.path.exists(xbot_commands_file):
                if local_pmclib_path not in sys.path:
                    sys.path.insert(0, local_pmclib_path)
                print(f"✅ Found local PMCLib at: {local_pmclib_path}")
                return True
            else:
                print(
                    f"⚠️ Directory exists but xbot_commands.py not found: {local_pmclib_path}")
        else:
            print(f"ℹ️ Local PMCLib directory not found: {local_pmclib_path}")
            print("   This is expected if using mock or installed PMCLib")

        return False

    def load_pmclib(self):
        """Lade PMCLib (lokal oder Mock)"""
        try:
            # Versuche lokale PMCLib zu laden (falls nicht in .gitignore)
            if self._check_local_pmclib_available():
                from match_pm_xBot import xbot_commands as bot
                from match_pm_xBot import system_commands as sys_cmd
                # from match_pm_xBot import pmc_types  # Falls verfügbar

                self.pmclib_source = "local_match_pm_xBot"
                self.use_mock = False
                print("✅ Successfully loaded local match_pm_xBot PMCLib")

                return bot, sys_cmd, None
            else:
                raise ImportError("Local PMCLib not available")

        except ImportError as e:
            print(f"ℹ️ Local PMCLib not available: {e}")

            try:
                # Fallback: Versuche installierte PMCLib
                from pmclib import xbot_commands as bot
                from pmclib import system_commands as sys_cmd
                from pmclib import pmc_types

                self.pmclib_source = "installed_pmclib"
                self.use_mock = False
                print("✅ Successfully loaded installed PMCLib")

                return bot, sys_cmd, pmc_types

            except ImportError as e2:
                print(f"ℹ️ Installed PMCLib not available: {e2}")

                # Final fallback: Mock
                from . import mock_pmclib

                self.pmclib_source = "mock"
                self.use_mock = True
                print("⚠️ Using mock PMCLib for development")

                return mock_pmclib.xbot_commands, mock_pmclib.system_commands, mock_pmclib.pmc_types

    def _check_local_pmclib_available(self) -> bool:
        """Prüfe ob lokale PMCLib verfügbar und funktionsfähig ist"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        local_pmclib_path = os.path.join(current_dir, 'match_pm_xBot')

        # Prüfe ob Verzeichnis existiert
        if not os.path.exists(local_pmclib_path):
            return False

        # Prüfe ob wichtige Dateien vorhanden sind
        required_files = ['xbot_commands.py', 'system_commands.py']
        for file in required_files:
            if not os.path.exists(os.path.join(local_pmclib_path, file)):
                print(f"⚠️ Required file missing: {file}")
                return False

        return True

    def get_status(self) -> dict:
        """Status-Info über geladene PMCLib"""
        return {
            'source': self.pmclib_source,
            'is_mock': self.use_mock,
            'available': self.pmclib_source != "unknown",
            'local_path_exists': self._check_local_pmclib_available()
        }


# Global instance
_pmclib_loader = PMCLibLoader()
bot, sys_cmd, pmc_types = _pmclib_loader.load_pmclib()


def get_pmclib_status() -> dict:
    """Hole Status der geladenen PMCLib"""
    return _pmclib_loader.get_status()

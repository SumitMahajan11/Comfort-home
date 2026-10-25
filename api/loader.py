"""
api/loader.py

Startup artifact loader and cryptographic checksum verifier.
Enforces AGENTS.md Rule 1 and Prompt Requirements:
- Verifies every file in data/export/manifest.json against its recorded sha256.
- Refuses to start (raises RuntimeError) if any file is missing or has a checksum mismatch.
- Loads all static artifacts into memory for zero-latency, read-only API requests.
"""

import os
import json
import hashlib
import logging
from typing import Dict, Any, Optional

from api.config import (
    MANIFEST_PATH,
    EXPORT_DIR,
    COSTS_DIR,
    LOCALES_DIR
)

logger = logging.getLogger("climateadapt.api.loader")

class ArtifactStore:
    def __init__(self):
        self.manifest_checksum: str = ""
        self.manifest_data: Dict[str, Any] = {}
        self.cache: Dict[str, Any] = {}
        self.dsr_rates: Dict[str, Any] = {}
        self.materials: Dict[str, Any] = {}
        self.tariffs: Dict[str, Any] = {}
        self.locales: Dict[str, Dict[str, Any]] = {}
        self.is_loaded: bool = False

    def verify_and_load(self, manifest_path: str = MANIFEST_PATH, export_dir: str = EXPORT_DIR):
        """
        Loads manifest.json, verifies all recorded sha256 hashes, and loads JSON files into memory.
        Raises RuntimeError if verification fails.
        """
        if not os.path.exists(manifest_path):
            raise RuntimeError(f"Startup Aborted: Manifest file not found at {manifest_path}")

        manifest_bytes = open(manifest_path, "rb").read()
        self.manifest_checksum = hashlib.sha256(manifest_bytes).hexdigest()
        self.manifest_data = json.loads(manifest_bytes.decode("utf-8"))

        files_meta = self.manifest_data.get("files", {})
        if not files_meta:
            raise RuntimeError(f"Startup Aborted: No files declared in manifest {manifest_path}")

        logger.info(f"Verifying {len(files_meta)} artifact files against manifest sha256 checksums...")

        mismatches = []
        for filename, meta in files_meta.items():
            filepath = os.path.join(export_dir, filename)
            if not os.path.exists(filepath):
                mismatches.append(f"Missing file: {filename}")
                continue
            
            content_bytes = open(filepath, "rb").read()
            computed_sha = hashlib.sha256(content_bytes).hexdigest()
            expected_sha = meta.get("sha256")
            
            if computed_sha != expected_sha:
                mismatches.append(f"Checksum mismatch for {filename}: expected {expected_sha}, got {computed_sha}")
                continue

            # Load into memory cache
            try:
                self.cache[filename] = json.loads(content_bytes.decode("utf-8"))
            except Exception as e:
                mismatches.append(f"Corrupt JSON in {filename}: {str(e)}")

        if mismatches:
            err_msg = "Startup Aborted: Data artifact integrity verification failed:\n" + "\n".join(mismatches)
            logger.error(err_msg)
            raise RuntimeError(err_msg)

        logger.info(f"Verification successful: {len(self.cache)} export files loaded into memory cache.")

        # Load Cost Data
        dsr_path = os.path.join(COSTS_DIR, "dsr_rates.json")
        if os.path.exists(dsr_path):
            dsr_raw = json.load(open(dsr_path, "r", encoding="utf-8"))
            if isinstance(dsr_raw, list):
                self.dsr_rates = {item["item_id"]: item for item in dsr_raw if isinstance(item, dict) and "item_id" in item}
            else:
                self.dsr_rates = dsr_raw
        
        materials_path = os.path.join(COSTS_DIR, "materials.json")
        if os.path.exists(materials_path):
            self.materials = json.load(open(materials_path, "r", encoding="utf-8"))

        tariffs_path = os.path.join(COSTS_DIR, "tariffs.json")
        if os.path.exists(tariffs_path):
            self.tariffs = json.load(open(tariffs_path, "r", encoding="utf-8"))

        # Load Locales
        en_path = os.path.join(LOCALES_DIR, "en.json")
        if os.path.exists(en_path):
            self.locales["en"] = json.load(open(en_path, "r", encoding="utf-8"))
        
        hi_path = os.path.join(LOCALES_DIR, "hi.json")
        if os.path.exists(hi_path):
            self.locales["hi"] = json.load(open(hi_path, "r", encoding="utf-8"))

        self.is_loaded = True

    def get_json(self, filename: str) -> Optional[Any]:
        return self.cache.get(filename)

    def get_pareto(self, city: str, building_type: str) -> Optional[Any]:
        filename = f"pareto_{city}_{building_type}.json"
        return self.cache.get(filename)

    def get_monthly_indoor(self, city: str, building_type: str, design_id: str) -> Optional[Any]:
        filename = f"monthly_indoor_{city}_{building_type}_{design_id}.json"
        return self.cache.get(filename)

    def get_shap(self, city: str, building_type: str) -> Optional[Any]:
        filename = f"shap_{city}_{building_type}.json"
        return self.cache.get(filename)

    def get_comfort_norms(self, city: str) -> Optional[Any]:
        norms_data = self.cache.get("city_comfort_norms.json", {})
        return norms_data.get(city)

    def get_all_comfort_norms(self) -> Dict[str, Any]:
        return self.cache.get("city_comfort_norms.json", {})

    def get_surrogate_metrics(self, building_type: str) -> Optional[Any]:
        filename = f"surrogate_metrics_{building_type}.json"
        return self.cache.get(filename)

    def get_applicability(self) -> Optional[Any]:
        return self.cache.get("applicability.json")

    def get_locale(self, lang: str = "en") -> Dict[str, Any]:
        return self.locales.get(lang, self.locales.get("en", {}))

# Global singleton
_STORE = ArtifactStore()

def get_store() -> ArtifactStore:
    return _STORE

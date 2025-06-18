#!/usr/bin/env python3
"""
Schema Validation Script for VLLM Evaluation System

This script validates dataset manifests and configuration files against
predefined JSON schemas to ensure data integrity and consistency.
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Optional

import yaml
from jsonschema import Draft7Validator

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Constants
MIN_DESCRIPTION_LENGTH = 10
MIN_QUALITY_THRESHOLD = 0.1
MAX_QUALITY_THRESHOLD = 0.9
DEFAULT_BATCH_SIZE = 32
DEFAULT_FEWSHOT = 8

# Dataset Manifest Schema
DATASET_MANIFEST_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["name", "version", "description", "splits", "schema"],
    "properties": {
        "name": {
            "type": "string",
            "pattern": "^[a-z0-9_-]+$",
            "description": "Dataset name (lowercase, alphanumeric, underscore, hyphen)",
        },
        "version": {
            "type": "string",
            "pattern": "^\\d+\\.\\d+(\\.\\d+)?$",
            "description": "Semantic version (e.g., 1.0, 1.0.1)",
        },
        "description": {
            "type": "string",
            "minLength": MIN_DESCRIPTION_LENGTH,
            "description": "Dataset description",
        },
        "license": {"type": "string", "description": "Dataset license"},
        "language": {
            "type": "array",
            "items": {"type": "string", "pattern": "^[a-z]{2}$"},
            "description": "ISO 639-1 language codes",
        },
        "domain": {
            "type": "string",
            "enum": ["general", "medical", "legal", "technical", "academic", "conversational"],
            "description": "Dataset domain",
        },
        "task_type": {
            "type": "string",
            "enum": [
                "text_generation",
                "question_answering",
                "classification",
                "summarization",
                "translation",
            ],
            "description": "Primary task type",
        },
        "source": {
            "type": "object",
            "required": ["type", "path"],
            "properties": {
                "type": {"type": "string", "enum": ["huggingface", "local", "url", "s3"]},
                "path": {"type": "string"},
                "revision": {"type": "string"},
            },
        },
        "splits": {
            "type": "object",
            "minProperties": 1,
            "patternProperties": {
                "^(train|validation|test|dev)$": {
                    "type": "object",
                    "required": ["file", "size", "sha256"],
                    "properties": {
                        "file": {"type": "string", "description": "Relative path to data file"},
                        "size": {
                            "type": "integer",
                            "minimum": 1,
                            "description": "Number of samples",
                        },
                        "sha256": {
                            "type": "string",
                            "pattern": "^[a-f0-9]{64}$",
                            "description": "SHA-256 hash of the file",
                        },
                    },
                }
            },
        },
        "schema": {
            "type": "object",
            "required": ["input_field", "output_field"],
            "properties": {
                "input_field": {"type": "string", "description": "Field name for input text"},
                "output_field": {"type": "string", "description": "Field name for expected output"},
                "context_field": {
                    "type": "string",
                    "description": "Field name for context (optional)",
                },
                "metadata_fields": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Additional metadata fields",
                },
            },
        },
        "deduplication": {
            "type": "object",
            "properties": {
                "enabled": {"type": "boolean"},
                "method": {"type": "string", "enum": ["minhash_lsh", "exact_match", "semantic"]},
                "threshold": {"type": "number", "minimum": 0, "maximum": 1},
                "cross_split": {"type": "boolean"},
            },
        },
        "quality_checks": {
            "type": "object",
            "properties": {
                "min_length": {"type": "integer", "minimum": 1},
                "max_length": {"type": "integer", "minimum": 1},
                "language_detection": {"type": "boolean"},
                "profanity_filter": {"type": "boolean"},
            },
        },
        "evaluation": {
            "type": "object",
            "properties": {
                "deepeval": {
                    "type": "object",
                    "properties": {
                        "enabled": {"type": "boolean"},
                        "metrics": {"type": "array", "items": {"type": "string"}},
                    },
                },
                "evalchemy": {
                    "type": "object",
                    "properties": {
                        "enabled": {"type": "boolean"},
                        "tasks": {"type": "array", "items": {"type": "string"}},
                    },
                },
            },
        },
    },
}

# Evalchemy Config Schema
EVALCHEMY_CONFIG_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["benchmarks", "model_configs"],
    "properties": {
        "description": {"type": "string"},
        "version": {"type": "string"},
        "benchmarks": {
            "type": "object",
            "patternProperties": {
                "^[a-z0-9_]+$": {
                    "type": "object",
                    "required": ["enabled", "tasks"],
                    "properties": {
                        "enabled": {"type": "boolean"},
                        "tasks": {"type": "array", "items": {"type": "string"}},
                        "num_fewshot": {"type": "integer", "minimum": 0},
                        "batch_size": {"type": "integer", "minimum": 1},
                        "device": {"type": "string", "enum": ["cuda", "cpu", "auto"]},
                        "limit": {"type": ["integer", "null"], "minimum": 1},
                        "description": {"type": "string"},
                        "metrics": {"type": "array", "items": {"type": "string"}},
                        "output_path": {"type": "string"},
                        "log_samples": {"type": "boolean"},
                        "priority": {"type": "string", "enum": ["high", "medium", "low"]},
                    },
                }
            },
        },
        "model_configs": {
            "type": "object",
            "patternProperties": {
                "^[a-z0-9_]+$": {
                    "type": "object",
                    "required": ["model_args"],
                    "properties": {
                        "model_args": {"type": "string"},
                        "batch_size": {"type": ["string", "integer"]},
                        "device": {"type": "string"},
                    },
                }
            },
        },
    },
}


class SchemaValidator:
    """Schema validator for VLLM evaluation system files"""

    def __init__(self):
        self.schemas = {
            "dataset_manifest": DATASET_MANIFEST_SCHEMA,
            "evalchemy_config": EVALCHEMY_CONFIG_SCHEMA,
        }
        self.errors = []
        self.warnings = []

    def validate_file(self, file_path: Path, schema_type: str) -> bool:
        """Validate a single file against its schema"""
        try:
            # Load file content
            if file_path.suffix.lower() in [".yaml", ".yml"]:
                data = yaml.safe_load(file_path.read_text(encoding="utf-8"))
            elif file_path.suffix.lower() == ".json":
                data = json.loads(file_path.read_text(encoding="utf-8"))
            else:
                self.errors.append(f"Unsupported file format: {file_path}")
                return False

            # Get schema
            if schema_type not in self.schemas:
                self.errors.append(f"Unknown schema type: {schema_type}")
                return False

            schema = self.schemas[schema_type]

            # Validate against schema
            validator = Draft7Validator(schema)
            validation_errors = list(validator.iter_errors(data))

            if validation_errors:
                self.errors.append(f"Validation errors in {file_path}:")
                for error in validation_errors:
                    error_path = " -> ".join(str(p) for p in error.absolute_path)
                    self.errors.append(f"  {error_path}: {error.message}")
                return False

            # Additional custom validations
            self._custom_validations(file_path, data, schema_type)

            logger.info(f"✅ {file_path} passed validation")
            return True

        except Exception as e:
            self.errors.append(f"Error validating {file_path}: {e!s}")
            return False

    def _custom_validations(self, file_path: Path, data: dict[str, Any], schema_type: str):
        """Perform custom validations beyond JSON schema"""

        if schema_type == "dataset_manifest":
            self._validate_dataset_manifest(file_path, data)
        elif schema_type == "evalchemy_config":
            self._validate_evalchemy_config(file_path, data)

    def _validate_dataset_manifest(self, file_path: Path, data: dict[str, Any]):
        """Custom validations for dataset manifests"""

        # Check if referenced files exist
        base_dir = file_path.parent.parent  # Assuming manifests are in datasets/manifests/

        for split_name, split_info in data.get("splits", {}).items():
            file_path_rel = split_info.get("file")
            if file_path_rel:
                full_path = base_dir / file_path_rel
                if not full_path.exists():
                    self.warnings.append(
                        f"Referenced file does not exist for split '{split_name}': {full_path}"
                    )

        # Check language codes
        languages = data.get("language", [])
        valid_language_codes = {
            "en",
            "ko",
            "ja",
            "zh",
            "es",
            "fr",
            "de",
            "it",
            "pt",
            "ru",
            "ar",
            "hi",
            "th",
            "vi",
            "id",
            "ms",
            "tl",
            "sw",
            "tr",
            "pl",
        }

        for lang in languages:
            if lang not in valid_language_codes:
                self.warnings.append(f"Unknown language code: {lang}")

        # Check deduplication settings
        dedup = data.get("deduplication", {})
        if dedup.get("enabled") and dedup.get("method") == "minhash_lsh":
            threshold = dedup.get("threshold", 0.8)
            if threshold < MIN_QUALITY_THRESHOLD or threshold > MAX_QUALITY_THRESHOLD:
                self.warnings.append(f"Unusual deduplication threshold: {threshold}")

    def _validate_evalchemy_config(self, file_path: Path, data: dict[str, Any]):  # noqa: ARG002
        """Custom validations for Evalchemy configurations"""

        # Check for enabled benchmarks
        enabled_benchmarks = []
        for name, config in data.get("benchmarks", {}).items():
            if config.get("enabled", False):
                enabled_benchmarks.append(name)

        if not enabled_benchmarks:
            self.warnings.append("No benchmarks are enabled")

        # Check resource requirements
        for name, config in data.get("benchmarks", {}).items():
            if config.get("enabled", False):
                batch_size = config.get("batch_size", 1)
                if batch_size > DEFAULT_BATCH_SIZE:
                    self.warnings.append(f"Large batch size for {name}: {batch_size}")

                device = config.get("device", "cpu")
                if device == "cuda" and batch_size > DEFAULT_FEWSHOT:
                    self.warnings.append(f"High GPU memory usage expected for {name}")

    def validate_directory(self, directory: Path, pattern: str = "*.yaml") -> bool:
        """Validate all files matching pattern in directory"""
        success = True

        for file_path in directory.glob(pattern):
            if file_path.is_file():
                # Determine schema type based on file location and name
                schema_type = self._determine_schema_type(file_path)

                if schema_type:
                    if not self.validate_file(file_path, schema_type):
                        success = False
                else:
                    logger.info(f"⏭️  Skipping {file_path} (no schema defined)")

        return success

    def _determine_schema_type(self, file_path: Path) -> Optional[str]:
        """Determine schema type based on file path and name"""

        # Dataset manifests
        if "manifests" in file_path.parts and file_path.name.endswith("_manifest.yaml"):
            return "dataset_manifest"

        # Evalchemy configs
        if file_path.name == "eval_config.json":
            return "evalchemy_config"

        return None

    def print_summary(self):
        """Print validation summary"""
        print("\n" + "=" * 60)
        print("VALIDATION SUMMARY")
        print("=" * 60)

        if self.errors:
            print(f"\n❌ ERRORS ({len(self.errors)}):")
            for error in self.errors:
                print(f"  {error}")

        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  {warning}")

        if not self.errors and not self.warnings:
            print("\n✅ All validations passed!")
        elif not self.errors:
            print(f"\n✅ Validation passed with {len(self.warnings)} warnings")
        else:
            print(
                f"\n❌ Validation failed with {len(self.errors)} errors and {len(self.warnings)} warnings"
            )


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Validate VLLM evaluation system schemas",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python validate_schemas.py datasets/
  python validate_schemas.py datasets/manifests/ --pattern "*.yaml"
  python validate_schemas.py eval/evalchemy/configs/eval_config.json
        """,
    )

    parser.add_argument("path", type=str, help="Path to file or directory to validate")

    parser.add_argument(
        "--pattern", type=str, default="*.yaml", help="File pattern to match (for directories)"
    )

    parser.add_argument(
        "--schema-type",
        type=str,
        choices=["dataset_manifest", "evalchemy_config"],
        help="Force specific schema type (auto-detected if not specified)",
    )

    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Initialize validator
    validator = SchemaValidator()

    # Validate path
    path = Path(args.path)

    if not path.exists():
        logger.error(f"Path does not exist: {path}")
        sys.exit(1)

    success = True

    if path.is_file():
        # Validate single file
        schema_type = args.schema_type or validator._determine_schema_type(path)
        if not schema_type:
            logger.error(f"Cannot determine schema type for {path}")
            sys.exit(1)

        success = validator.validate_file(path, schema_type)

    elif path.is_dir():
        # Validate directory
        success = validator.validate_directory(path, args.pattern)

    else:
        logger.error(f"Invalid path: {path}")
        sys.exit(1)

    # Print summary
    validator.print_summary()

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
AI Model Manager for PDF Metadata Extraction

Handles downloading and caching of large AI models externally.
This replaces the local 2.4GB models directory.
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class ModelManager:
    """Manages AI model downloads and local caching."""
    
    def __init__(self, cache_dir: Optional[str] = None):
        """Initialize model manager with local cache directory."""
        self.cache_dir = Path(cache_dir) if cache_dir else Path.home() / ".mathpdf_models"
        self.cache_dir.mkdir(exist_ok=True)
        
        # Model configurations
        self.model_configs = {
            "base_model": {
                "name": "pdf-metadata-extractor-base",
                "size": "1.8GB",
                "url": "https://huggingface.co/mathpdf/metadata-extractor-base",
                "description": "Base model for PDF metadata extraction (Transformers)"
            },
            "finetuned_model": {
                "name": "pdf-metadata-extractor-finetuned",
                "size": "300MB",
                "url": "https://huggingface.co/mathpdf/metadata-extractor-finetuned",
                "description": "Fine-tuned model for academic papers (Transformers/LoRA)"
            },
            # GGUF models for llama-cpp-python (grammar-constrained extraction)
            "qwen2.5-7b": {
                "name": "qwen2.5-7b-instruct-q4_k_m",
                "size": "4.7GB",
                "repo_id": "Qwen/Qwen2.5-7B-Instruct-GGUF",
                "filename": "qwen2.5-7b-instruct-q4_k_m.gguf",
                "url": "https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF",
                "description": "Qwen2.5 7B Instruct Q4_K_M — best quality (GGUF)",
                "format": "gguf",
            },
            "qwen2.5-3b": {
                "name": "qwen2.5-3b-instruct-q4_k_m",
                "size": "2.1GB",
                "repo_id": "Qwen/Qwen2.5-3B-Instruct-GGUF",
                "filename": "qwen2.5-3b-instruct-q4_k_m.gguf",
                "url": "https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF",
                "description": "Qwen2.5 3B Instruct Q4_K_M — lightweight (GGUF)",
                "format": "gguf",
            },
        }
    
    def download_model(self, model_name: str) -> Path:
        """Download model if not cached locally.

        For GGUF models, uses ``huggingface_hub.hf_hub_download`` for
        robust, resumable downloads with caching.
        """
        if model_name not in self.model_configs:
            raise ValueError(f"Unknown model: {model_name}")

        config = self.model_configs[model_name]

        # GGUF models — download the single .gguf file
        if config.get("format") == "gguf":
            return self._download_gguf_model(model_name, config)

        # Legacy Transformers models — placeholder approach
        return self._download_legacy_model(model_name, config)

    def _download_gguf_model(self, model_name: str, config: dict) -> Path:
        """Download a single GGUF file via huggingface_hub."""
        gguf_dir = self.cache_dir / "gguf"
        gguf_dir.mkdir(parents=True, exist_ok=True)

        local_path = gguf_dir / config["filename"]
        if local_path.exists():
            logger.info(f"GGUF model {model_name} already cached at {local_path}")
            return local_path

        logger.info(
            f"Downloading {config['description']} "
            f"({config['size']}) from {config['repo_id']}…"
        )

        try:
            from huggingface_hub import hf_hub_download

            downloaded = hf_hub_download(
                repo_id=config["repo_id"],
                filename=config["filename"],
                cache_dir=str(gguf_dir),
                local_dir=str(gguf_dir),
            )
            logger.info(f"Model downloaded to {downloaded}")
            return Path(downloaded)

        except ImportError:
            logger.error(
                "huggingface_hub is required for GGUF model downloads.  "
                "Install it with:  pip install huggingface_hub"
            )
            raise
        except Exception as e:
            logger.error(f"Download failed: {e}")
            raise

    def _download_legacy_model(self, model_name: str, config: dict) -> Path:
        """Download a legacy Transformers model (placeholder)."""
        model_dir = self.cache_dir / model_name
        config_file = model_dir / "config.json"

        if config_file.exists():
            logger.info(f"Model {model_name} already cached")
            return model_dir

        logger.info(f"Downloading model {model_name}...")
        model_dir.mkdir(exist_ok=True)

        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)

        readme_file = model_dir / "README.md"
        with open(readme_file, 'w') as f:
            f.write(f"# {config['name']}\n\n"
                    f"{config['description']}\n\n"
                    f"**Size**: {config['size']}\n"
                    f"**URL**: {config['url']}\n\n"
                    f"See huggingface_hub documentation for download instructions.\n")

        logger.info(f"Model config created at {model_dir}")
        logger.warning(f"Large model files not downloaded. See {readme_file} for instructions.")
        return model_dir
    
    def get_model_path(self, model_name: str) -> Path:
        """Get path to cached model."""
        return self.cache_dir / model_name
    
    def list_available_models(self) -> Dict[str, Dict[str, Any]]:
        """List available models."""
        return self.model_configs.copy()
    
    def cleanup_cache(self) -> None:
        """Remove all cached models."""
        if self.cache_dir.exists():
            import shutil
            shutil.rmtree(self.cache_dir)
            logger.info(f"Cleaned up model cache: {self.cache_dir}")


# Global instance
_model_manager: Optional[ModelManager] = None

def get_model_manager() -> ModelManager:
    """Get or create global model manager instance."""
    global _model_manager
    if _model_manager is None:
        _model_manager = ModelManager()
    return _model_manager


if __name__ == "__main__":
    # CLI interface for model management
    import sys
    
    manager = get_model_manager()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "list":
            print("Available models:")
            for name, config in manager.list_available_models().items():
                print(f"  {name}: {config['description']} ({config['size']})")
        
        elif command == "download":
            if len(sys.argv) > 2:
                model_name = sys.argv[2]
                try:
                    path = manager.download_model(model_name)
                    print(f"Model ready at: {path}")
                except ValueError as e:
                    print(f"Error: {e}")
            else:
                print("Usage: python model_manager.py download <model_name>")
        
        elif command == "cleanup":
            manager.cleanup_cache()
            print("Model cache cleaned up")
        
        else:
            print(f"Unknown command: {command}")
    else:
        print("Usage: python model_manager.py [list|download|cleanup]")
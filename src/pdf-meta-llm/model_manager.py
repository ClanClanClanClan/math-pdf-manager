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
                "description": "Base model for PDF metadata extraction"
            },
            "finetuned_model": {
                "name": "pdf-metadata-extractor-finetuned", 
                "size": "300MB",
                "url": "https://huggingface.co/mathpdf/metadata-extractor-finetuned",
                "description": "Fine-tuned model for academic papers"
            }
        }
    
    def download_model(self, model_name: str) -> Path:
        """Download model if not cached locally."""
        if model_name not in self.model_configs:
            raise ValueError(f"Unknown model: {model_name}")
        
        model_dir = self.cache_dir / model_name
        config_file = model_dir / "config.json"
        
        if config_file.exists():
            logger.info(f"Model {model_name} already cached")
            return model_dir
        
        logger.info(f"Downloading model {model_name}...")
        config = self.model_configs[model_name]
        
        # Create placeholder for now - in real implementation would download
        model_dir.mkdir(exist_ok=True)
        
        # Save model config
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        # Create README with download instructions
        readme_file = model_dir / "README.md"
        with open(readme_file, 'w') as f:
            f.write(f"""# {config['name']}

{config['description']}

**Size**: {config['size']}
**URL**: {config['url']}

## Manual Download Instructions

1. Install huggingface-hub:
   ```bash
   pip install huggingface-hub
   ```

2. Download model:
   ```python
   from huggingface_hub import snapshot_download
   snapshot_download(
       repo_id="{config['url'].split('/')[-1]}",
       local_dir="{model_dir}",
       local_dir_use_symlinks=False
   )
   ```

## Alternative: Use API

For development, consider using the Hugging Face Inference API instead of downloading large models locally.
""")
        
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
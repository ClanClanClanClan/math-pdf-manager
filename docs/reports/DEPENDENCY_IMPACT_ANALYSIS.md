
# DEPENDENCY IMPACT ANALYSIS REPORT

## CURRENT STRUCTURE METRICS
- **Root Directories**: 48
- **Root Files**: 143
- **Total Python Files**: 12434
- **Files with Imports**: 11496
- **Files with Relative Imports**: 7935

## REORGANIZATION IMPACT ASSESSMENT

### 🚨 HIGH RISK: Import Dependencies
**592 files** have imports that will break:

**metadata_fetcher.py**:
  - `utils`

**FINAL_VALIDATION_RESULTS.py**:
  - `validators`

**demo_new_system.py**:
  - `validators`

**manual_validation.py**:
  - `validators`

**main_processing.py**:
  - `utils`
  - `filename_checker`

**updater.py**:
  - `utils`

**MANIAC_TEST_EXECUTION.py**:
  - `validators`

**showcase_transformation.py**:
  - `validators`

**analyze_dependencies.py**:
  - `utils`
  - `config`
  - `api`
  - `core`

**refactor_modules.py**:
  - `validators`

**main.py**:
  - `filename_checker`

**cleanup_code.py**:
  - `utils`

**tools/deployment_validator.py**:
  - `filename_checker`
  - `validators`

**core/io.py**:
  - `utils`

**archive/parsers.py**:
  - `extractors`
  - `config`

**filename_checker/text_processing.py**:
  - `filename_checker`

**filename_checker/__init__.py**:
  - `core`

**filename_checker/batch_processing.py**:
  - `core`

**tests/test_utils.py**:
  - `utils`

**tests/test_unicode_fix.py**:
  - `filename_checker`
  - `validators`

**tests/test_main_compat.py**:
  - `utils`
  - `filename_checker`

**tests/test_main_like.py**:
  - `utils`
  - `filename_checker`
  - `validators`

**tests/test_ito_possessive.py**:
  - `filename_checker`
  - `validators`

**tests/test_filename_checker.py**:
  - `utils`
  - `filename_checker`

**tests/test_filename_checker_backup.py**:
  - `utils`
  - `filename_checker`

**utils/__init__.py**:
  - `filename_checker`
  - `validators`

**cli/commands.py**:
  - `validators`

**validators/title_normalizer.py**:
  - `utils`

**tools/analysis/comprehensive_audit.py**:
  - `utils`
  - `filename_checker`
  - `validators`

**archive/consolidated/__init__.py**:
  - `filename_checker`
  - `validators`

**archive/consolidated/validators_legacy/filename.py**:
  - `filename_checker`

**archive/consolidated/legacy_scripts/run_tests.py**:
  - `validators`

**archive/consolidated/legacy_scripts/manual_test_execution.py**:
  - `validators`

**archive/consolidated/legacy_scripts/test_main_compat.py**:
  - `utils`
  - `filename_checker`

**archive/consolidated/legacy_scripts/ultimate_test_runner.py**:
  - `validators`

**archive/consolidated/legacy_scripts/execute_tests_direct.py**:
  - `validators`

**archive/consolidated/legacy_scripts/check_test_status.py**:
  - `filename_checker`

**archive/consolidated/legacy_scripts/simple_test.py**:
  - `validators`

**archive/consolidated/legacy_scripts/execute_refactoring_tests.py**:
  - `validators`

**archive/consolidated/legacy_scripts/comprehensive_test_report.py**:
  - `validators`

**archive/consolidated/legacy_scripts/final_test_run.py**:
  - `validators`

**archive/consolidated/legacy_scripts/comprehensive_test_execution.py**:
  - `filename_checker`
  - `validators`

**archive/consolidated/debug/test_refactoring.py**:
  - `filename_checker`
  - `validators`

**archive/consolidated/debug/test_main_compat.py**:
  - `utils`
  - `filename_checker`

**archive/consolidated/debug/test_inline.py**:
  - `validators`

**archive/consolidated/debug/test_output.py**:
  - `validators`

**archive/consolidated/debug/debug_rename_issue.py**:
  - `filename_checker`

**archive/consolidated/debug/test_runner.py**:
  - `filename_checker`

**archive/consolidated/debug/debug_main_rename.py**:
  - `utils`
  - `filename_checker`

**archive/consolidated/debug/debug_test_expectations.py**:
  - `filename_checker`

**archive/consolidated/debug/test_functionality.py**:
  - `utils`
  - `validators`

**archive/consolidated/backups/backup_before_improvements/main.py**:
  - `utils`
  - `filename_checker`

**.venv/lib/python3.12/site-packages/_hypothesis_pytestplugin.py**:
  - `core`

**.venv/lib/python3.12/site-packages/packaging/requirements.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/packaging/markers.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/packaging/specifiers.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/pymupdf/__init__.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/thinc/util.py**:
  - `api`

**.venv/lib/python3.12/site-packages/thinc/__init__.py**:
  - `config`

**.venv/lib/python3.12/site-packages/thinc/optimizers.py**:
  - `config`

**.venv/lib/python3.12/site-packages/thinc/api.py**:
  - `config`

**.venv/lib/python3.12/site-packages/thinc/loss.py**:
  - `config`

**.venv/lib/python3.12/site-packages/thinc/initializers.py**:
  - `config`

**.venv/lib/python3.12/site-packages/thinc/schedules.py**:
  - `config`

**.venv/lib/python3.12/site-packages/networkx/__init__.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/huggingface_hub/_webhooks_payload.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/huggingface_hub/hub_mixin.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/huggingface_hub/_webhooks_server.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/huggingface_hub/keras_mixin.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/huggingface_hub/_commit_scheduler.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/huggingface_hub/__init__.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/huggingface_hub/_local_folder.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/huggingface_hub/lfs.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/huggingface_hub/file_download.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/huggingface_hub/community.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/huggingface_hub/_oauth.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/huggingface_hub/_login.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/huggingface_hub/inference_api.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/huggingface_hub/_inference_endpoints.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/huggingface_hub/hf_api.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/huggingface_hub/_snapshot_download.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/huggingface_hub/_upload_large_folder.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/huggingface_hub/repocard.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/huggingface_hub/repository.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/huggingface_hub/_tensorboard_logger.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/huggingface_hub/hf_file_system.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/huggingface_hub/fastai_utils.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/huggingface_hub/_commit_api.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/dotenv/__main__.py**:
  - `cli`

**.venv/lib/python3.12/site-packages/sympy/__init__.py**:
  - `core`

**.venv/lib/python3.12/site-packages/sympy/abc.py**:
  - `core`

**.venv/lib/python3.12/site-packages/typer/models.py**:
  - `core`

**.venv/lib/python3.12/site-packages/typer/completion.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/typer/rich_utils.py**:
  - `core`

**.venv/lib/python3.12/site-packages/typer/main.py**:
  - `utils`
  - `core`

**.venv/lib/python3.12/site-packages/typer/__main__.py**:
  - `cli`

**.venv/lib/python3.12/site-packages/docutils/examples.py**:
  - `core`

**.venv/lib/python3.12/site-packages/docutils/statemachine.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/pyparsing/actions.py**:
  - `core`

**.venv/lib/python3.12/site-packages/pyparsing/__init__.py**:
  - `core`

**.venv/lib/python3.12/site-packages/pyparsing/common.py**:
  - `core`

**.venv/lib/python3.12/site-packages/pyparsing/exceptions.py**:
  - `core`

**.venv/lib/python3.12/site-packages/pyparsing/testing.py**:
  - `core`

**.venv/lib/python3.12/site-packages/pyparsing/helpers.py**:
  - `core`

**.venv/lib/python3.12/site-packages/jinja2/compiler.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/jinja2/async_utils.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/jinja2/loaders.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/jinja2/__init__.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/jinja2/runtime.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/jinja2/debug.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/jinja2/lexer.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/jinja2/environment.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/jinja2/defaults.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/jinja2/nodes.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/jinja2/tests.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/jinja2/filters.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/jinja2/ext.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/cryptography/__init__.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/cryptography/fernet.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/arrow/__init__.py**:
  - `api`

**.venv/lib/python3.12/site-packages/pdfplumber/convert.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/pdfplumber/__init__.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/pdfplumber/page.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/pdfplumber/pdf.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/pdfplumber/display.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/pdfplumber/container.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/pdfplumber/structure.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/pdfplumber/table.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/fsspec/parquet.py**:
  - `utils`
  - `core`

**.venv/lib/python3.12/site-packages/fsspec/generic.py**:
  - `core`

**.venv/lib/python3.12/site-packages/fsspec/asyn.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/fsspec/__init__.py**:
  - `core`

**.venv/lib/python3.12/site-packages/fsspec/spec.py**:
  - `utils`
  - `config`
  - `core`

**.venv/lib/python3.12/site-packages/fsspec/gui.py**:
  - `core`

**.venv/lib/python3.12/site-packages/cffi/__init__.py**:
  - `api`

**.venv/lib/python3.12/site-packages/markdown_it/parser_block.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/markdown_it/renderer.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/markdown_it/ruler.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/markdown_it/parser_inline.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/markdown_it/main.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/idna/compat.py**:
  - `core`

**.venv/lib/python3.12/site-packages/idna/__init__.py**:
  - `core`

**.venv/lib/python3.12/site-packages/idna/codec.py**:
  - `core`

**.venv/lib/python3.12/site-packages/click/globals.py**:
  - `core`

**.venv/lib/python3.12/site-packages/click/__init__.py**:
  - `utils`
  - `core`

**.venv/lib/python3.12/site-packages/click/core.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/click/types.py**:
  - `utils`
  - `core`

**.venv/lib/python3.12/site-packages/click/parser.py**:
  - `core`

**.venv/lib/python3.12/site-packages/click/termui.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/click/exceptions.py**:
  - `utils`
  - `core`

**.venv/lib/python3.12/site-packages/click/shell_completion.py**:
  - `utils`
  - `core`

**.venv/lib/python3.12/site-packages/click/_termui_impl.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/click/testing.py**:
  - `utils`
  - `core`

**.venv/lib/python3.12/site-packages/click/decorators.py**:
  - `utils`
  - `core`

**.venv/lib/python3.12/site-packages/torch/__init__.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/serialization.py**:
  - `config`

**.venv/lib/python3.12/site-packages/smart_open/webhdfs.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/smart_open/hdfs.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/numpy/__init__.py**:
  - `core`

**.venv/lib/python3.12/site-packages/charset_normalizer/md.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/charset_normalizer/legacy.py**:
  - `api`

**.venv/lib/python3.12/site-packages/charset_normalizer/models.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/charset_normalizer/__init__.py**:
  - `utils`
  - `api`

**.venv/lib/python3.12/site-packages/charset_normalizer/api.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/charset_normalizer/__main__.py**:
  - `cli`

**.venv/lib/python3.12/site-packages/charset_normalizer/cd.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/requests/auth.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/requests/sessions.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/requests/models.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/requests/__init__.py**:
  - `api`

**.venv/lib/python3.12/site-packages/requests/adapters.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/pdfminer/converter.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/pdfminer/pdfdevice.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/certifi/__init__.py**:
  - `core`

**.venv/lib/python3.12/site-packages/transformers/modeling_outputs.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/transformers/configuration_utils.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/transformers/modeling_flash_attention_utils.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/transformers/image_processing_utils_fast.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/transformers/image_utils.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/transformers/tokenization_utils.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/transformers/modeling_rope_utils.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/transformers/video_utils.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/transformers/pytorch_utils.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/transformers/trainer_seq2seq.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/transformers/modeling_flax_utils.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/transformers/image_transforms.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/transformers/modeling_flax_pytorch_utils.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/transformers/feature_extraction_utils.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/transformers/tokenization_utils_base.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/transformers/testing_utils.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/transformers/activations.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/transformers/dependency_versions_check.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/transformers/trainer_utils.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/transformers/safetensors_conversion.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/transformers/processing_utils.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/transformers/image_processing_base.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/transformers/training_args_seq2seq.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/transformers/modelcard.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/transformers/optimization.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/transformers/convert_slow_tokenizers_checkpoints_to_fast.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/transformers/training_args_tf.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/transformers/__init__.py**:
  - `utils`
  - `data`

**.venv/lib/python3.12/site-packages/transformers/convert_slow_tokenizer.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/transformers/image_processing_utils.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/transformers/feature_extraction_sequence_utils.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/transformers/training_args.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/transformers/audio_utils.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/transformers/modeling_gguf_pytorch_utils.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/transformers/modeling_flax_outputs.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/transformers/cache_utils.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/transformers/modeling_tf_pytorch_utils.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/transformers/dynamic_module_utils.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/transformers/tokenization_utils_fast.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/transformers/modeling_utils.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/transformers/model_debugging_utils.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/transformers/file_utils.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/transformers/trainer.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/transformers/video_processing_utils.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/transformers/hyperparameter_search.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/transformers/convert_pytorch_checkpoint_to_tf2.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/transformers/trainer_callback.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/transformers/tf_utils.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/transformers/trainer_pt_utils.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/transformers/modeling_tf_utils.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/transformers/debug_utils.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/transformers/modeling_tf_outputs.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/tqdm/_main.py**:
  - `cli`

**.venv/lib/python3.12/site-packages/tqdm/std.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/tqdm/__init__.py**:
  - `cli`

**.venv/lib/python3.12/site-packages/tqdm/__main__.py**:
  - `cli`

**.venv/lib/python3.12/site-packages/tqdm/_utils.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/keyring/__init__.py**:
  - `core`

**.venv/lib/python3.12/site-packages/keyring/__main__.py**:
  - `cli`

**.venv/lib/python3.12/site-packages/hypothesis/provisional.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/hypothesis/stateful.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/weasel/__init__.py**:
  - `cli`

**.venv/lib/python3.12/site-packages/setuptools/dist.py**:
  - `config`

**.venv/lib/python3.12/site-packages/pydantic/fields.py**:
  - `config`

**.venv/lib/python3.12/site-packages/pydantic/__init__.py**:
  - `config`

**.venv/lib/python3.12/site-packages/pydantic/json_schema.py**:
  - `config`

**.venv/lib/python3.12/site-packages/pydantic/type_adapter.py**:
  - `config`

**.venv/lib/python3.12/site-packages/pydantic/validate_call_decorator.py**:
  - `config`

**.venv/lib/python3.12/site-packages/pydantic/dataclasses.py**:
  - `config`

**.venv/lib/python3.12/site-packages/pydantic/main.py**:
  - `config`

**.venv/lib/python3.12/site-packages/language_tool_python/server.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/language_tool_python/__init__.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/language_tool_python/__main__.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/language_tool_python/download_lt.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/selenium/webdriver/firefox/firefox_binary.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/selenium/webdriver/common/service.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/selenium/webdriver/common/action_chains.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/selenium/webdriver/remote/remote_connection.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/thinc/tests/mypy/test_mypy.py**:
  - `api`

**.venv/lib/python3.12/site-packages/networkx/algorithms/connectivity/disjoint_paths.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/networkx/algorithms/connectivity/connectivity.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/networkx/algorithms/connectivity/__init__.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/networkx/algorithms/connectivity/kcutsets.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/networkx/algorithms/connectivity/cuts.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/networkx/algorithms/flow/gomory_hu.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/networkx/algorithms/flow/maxflow.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/networkx/algorithms/flow/__init__.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/networkx/algorithms/flow/shortestaugmentingpath.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/networkx/algorithms/flow/preflowpush.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/huggingface_hub/inference/_mcp/cli.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/huggingface_hub/inference/_mcp/mcp_client.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/sympy/core/singleton.py**:
  - `core`

**.venv/lib/python3.12/site-packages/sympy/unify/usympy.py**:
  - `core`

**.venv/lib/python3.12/site-packages/sympy/strategies/tools.py**:
  - `core`

**.venv/lib/python3.12/site-packages/sympy/strategies/__init__.py**:
  - `tools`
  - `core`

**.venv/lib/python3.12/site-packages/sympy/ntheory/factor_.py**:
  - `core`

**.venv/lib/python3.12/site-packages/sympy/multipledispatch/dispatcher.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/sympy/multipledispatch/__init__.py**:
  - `core`

**.venv/lib/python3.12/site-packages/sympy/multipledispatch/conflict.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/sympy/vector/implicitregion.py**:
  - `core`

**.venv/lib/python3.12/site-packages/sympy/unify/tests/test_unify.py**:
  - `core`

**.venv/lib/python3.12/site-packages/sympy/strategies/branch/tools.py**:
  - `core`

**.venv/lib/python3.12/site-packages/sympy/strategies/branch/__init__.py**:
  - `tools`
  - `core`

**.venv/lib/python3.12/site-packages/sympy/strategies/branch/traverse.py**:
  - `core`

**.venv/lib/python3.12/site-packages/sympy/physics/optics/__init__.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/docutils/parsers/null.py**:
  - `parsers`

**.venv/lib/python3.12/site-packages/docutils/readers/__init__.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/cryptography/x509/ocsp.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/cryptography/x509/extensions.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/cryptography/x509/name.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/cryptography/x509/base.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/cryptography/x509/certificate_transparency.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/cryptography/hazmat/primitives/_serialization.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/cryptography/hazmat/primitives/_cipheralgorithm.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/cryptography/hazmat/primitives/padding.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/cryptography/hazmat/backends/openssl/backend.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/cryptography/hazmat/primitives/kdf/pbkdf2.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/cryptography/hazmat/primitives/kdf/hkdf.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/cryptography/hazmat/primitives/kdf/x963kdf.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/cryptography/hazmat/primitives/kdf/kbkdf.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/cryptography/hazmat/primitives/kdf/concatkdf.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/cryptography/hazmat/primitives/serialization/pkcs7.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/cryptography/hazmat/primitives/serialization/ssh.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/cryptography/hazmat/primitives/ciphers/algorithms.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/cryptography/hazmat/primitives/ciphers/modes.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/cryptography/hazmat/primitives/asymmetric/ec.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/cryptography/hazmat/primitives/asymmetric/rsa.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/cryptography/hazmat/primitives/asymmetric/types.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/cryptography/hazmat/primitives/asymmetric/dsa.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torch/_higher_order_ops/base_hop.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torch/_higher_order_ops/cond.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torch/_higher_order_ops/map.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torch/_functorch/partitioners.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_functorch/aot_autograd.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_export/__init__.py**:
  - `utils`
  - `config`

**.venv/lib/python3.12/site-packages/torch/onnx/__init__.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torch/fx/interpreter.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/dtype_propagation.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torch/_inductor/cudagraph_trees.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/select_algorithm.py**:
  - `utils`
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/ops_handler.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torch/_inductor/metrics.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/codecache.py**:
  - `utils`
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/mock_cache.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/optimize_indexing.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torch/_inductor/cpp_builder.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/cpu_vec_isa.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/compile_fx_ext.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/comms.py**:
  - `utils`
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/memory.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torch/_inductor/mkldnn_lowerings.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torch/_inductor/async_compile.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/pattern_matcher.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/quantized_lowerings.py**:
  - `utils`
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/triton_bundler.py**:
  - `utils`
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/graph.py**:
  - `utils`
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/lowering.py**:
  - `utils`
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/__init__.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/compile_fx.py**:
  - `utils`
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/sizevars.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torch/_inductor/ir.py**:
  - `utils`
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/analyze_preserves_zero_mask.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/index_propagation.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torch/_inductor/test_case.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/autotune_process.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/exc.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/utils.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/debug.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/comm_lowering.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/decomposition.py**:
  - `utils`
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/scheduler.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torch/_inductor/mkldnn_ir.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torch/_inductor/choices.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/remote_cache.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/comm_analysis.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torch/_inductor/bounds.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torch/_inductor/output_code.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/freezing.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/dependencies.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torch/_inductor/loop_body.py**:
  - `utils`
  - `config`

**.venv/lib/python3.12/site-packages/torch/_library/simple_registry.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torch/_library/autograd.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torch/_dynamo/cache_size.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_dynamo/guards.py**:
  - `utils`
  - `config`

**.venv/lib/python3.12/site-packages/torch/_dynamo/__init__.py**:
  - `utils`
  - `config`

**.venv/lib/python3.12/site-packages/torch/_dynamo/mutation_guard.py**:
  - `utils`
  - `config`

**.venv/lib/python3.12/site-packages/torch/_dynamo/test_case.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_dynamo/distributed.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_dynamo/resume_execution.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torch/_dynamo/output_graph.py**:
  - `utils`
  - `config`

**.venv/lib/python3.12/site-packages/torch/_dynamo/exc.py**:
  - `utils`
  - `config`

**.venv/lib/python3.12/site-packages/torch/_dynamo/utils.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_dynamo/side_effects.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torch/_dynamo/trace_rules.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torch/_dynamo/bytecode_transformation.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torch/_dynamo/convert_frame.py**:
  - `utils`
  - `config`

**.venv/lib/python3.12/site-packages/torch/_dynamo/testing.py**:
  - `utils`
  - `config`

**.venv/lib/python3.12/site-packages/torch/_dynamo/profiler.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torch/_dynamo/symbolic_convert.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torch/_dynamo/codegen.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torch/_dynamo/source.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torch/_dynamo/eval_frame.py**:
  - `utils`
  - `config`

**.venv/lib/python3.12/site-packages/torch/_dynamo/code_context.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torch/_dynamo/debug_utils.py**:
  - `utils`
  - `config`

**.venv/lib/python3.12/site-packages/torch/_dynamo/decorators.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torch/compiler/__init__.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/distributions/kl.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torch/_functorch/_aot_autograd/input_output_analysis.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torch/_functorch/_aot_autograd/runtime_wrappers.py**:
  - `utils`
  - `config`

**.venv/lib/python3.12/site-packages/torch/_functorch/_aot_autograd/dispatch_and_compile_graph.py**:
  - `utils`
  - `config`

**.venv/lib/python3.12/site-packages/torch/_functorch/_aot_autograd/autograd_cache.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_functorch/_aot_autograd/traced_function_transforms.py**:
  - `utils`
  - `config`

**.venv/lib/python3.12/site-packages/torch/_functorch/_aot_autograd/schemas.py**:
  - `utils`
  - `config`

**.venv/lib/python3.12/site-packages/torch/_functorch/_aot_autograd/jit_compile_runtime_wrappers.py**:
  - `utils`
  - `config`

**.venv/lib/python3.12/site-packages/torch/_functorch/_aot_autograd/collect_metadata_analysis.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torch/_functorch/_aot_autograd/subclass_utils.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torch/_numpy/testing/__init__.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torch/nn/modules/pooling.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torch/nn/modules/conv.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torch/nn/modules/padding.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torch/onnx/_internal/_exporter_legacy.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/onnx/_internal/exporter/_torchlib/ops/__init__.py**:
  - `core`

**.venv/lib/python3.12/site-packages/torch/distributed/checkpoint/_sharded_tensor_utils.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torch/distributed/checkpoint/state_dict_saver.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torch/distributed/checkpoint/__init__.py**:
  - `api`

**.venv/lib/python3.12/site-packages/torch/distributed/checkpoint/state_dict_loader.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torch/distributed/checkpoint/utils.py**:
  - `api`

**.venv/lib/python3.12/site-packages/torch/distributed/optim/__init__.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torch/distributed/optim/optimizer.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torch/distributed/fsdp/_common_utils.py**:
  - `api`

**.venv/lib/python3.12/site-packages/torch/distributed/_shard/__init__.py**:
  - `api`

**.venv/lib/python3.12/site-packages/torch/distributed/rpc/__init__.py**:
  - `api`

**.venv/lib/python3.12/site-packages/torch/distributed/rpc/_utils.py**:
  - `api`

**.venv/lib/python3.12/site-packages/torch/distributed/rpc/backend_registry.py**:
  - `api`

**.venv/lib/python3.12/site-packages/torch/distributed/elastic/metrics/__init__.py**:
  - `api`

**.venv/lib/python3.12/site-packages/torch/distributed/elastic/rendezvous/registry.py**:
  - `api`

**.venv/lib/python3.12/site-packages/torch/distributed/elastic/rendezvous/__init__.py**:
  - `api`

**.venv/lib/python3.12/site-packages/torch/distributed/elastic/rendezvous/etcd_rendezvous.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torch/distributed/elastic/rendezvous/c10d_rendezvous_backend.py**:
  - `utils`
  - `api`

**.venv/lib/python3.12/site-packages/torch/distributed/elastic/rendezvous/etcd_rendezvous_backend.py**:
  - `utils`
  - `api`

**.venv/lib/python3.12/site-packages/torch/distributed/elastic/rendezvous/dynamic_rendezvous.py**:
  - `utils`
  - `api`

**.venv/lib/python3.12/site-packages/torch/distributed/elastic/timer/local_timer.py**:
  - `api`

**.venv/lib/python3.12/site-packages/torch/distributed/elastic/timer/__init__.py**:
  - `api`

**.venv/lib/python3.12/site-packages/torch/distributed/elastic/utils/__init__.py**:
  - `api`

**.venv/lib/python3.12/site-packages/torch/distributed/elastic/events/__init__.py**:
  - `api`

**.venv/lib/python3.12/site-packages/torch/distributed/elastic/agent/server/__init__.py**:
  - `api`

**.venv/lib/python3.12/site-packages/torch/distributed/_shard/sharded_tensor/__init__.py**:
  - `api`

**.venv/lib/python3.12/site-packages/torch/distributed/_shard/sharded_tensor/api.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torch/distributed/_shard/sharding_plan/__init__.py**:
  - `api`

**.venv/lib/python3.12/site-packages/torch/distributed/_shard/sharding_spec/__init__.py**:
  - `api`

**.venv/lib/python3.12/site-packages/torch/distributed/_shard/sharding_spec/chunk_sharding_spec.py**:
  - `api`

**.venv/lib/python3.12/site-packages/torch/distributed/_shard/sharded_optim/__init__.py**:
  - `api`

**.venv/lib/python3.12/site-packages/torch/distributed/rpc/_testing/faulty_agent_backend_registry.py**:
  - `api`

**.venv/lib/python3.12/site-packages/torch/fx/experimental/proxy_tensor.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/fx/experimental/unification/__init__.py**:
  - `core`

**.venv/lib/python3.12/site-packages/torch/fx/experimental/unification/core.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torch/fx/experimental/unification/variable.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torch/fx/experimental/unification/more.py**:
  - `core`

**.venv/lib/python3.12/site-packages/torch/fx/experimental/unification/match.py**:
  - `utils`
  - `core`

**.venv/lib/python3.12/site-packages/torch/fx/experimental/unification/multipledispatch/dispatcher.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torch/fx/experimental/unification/multipledispatch/variadic.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torch/fx/experimental/unification/multipledispatch/__init__.py**:
  - `core`

**.venv/lib/python3.12/site-packages/torch/fx/experimental/unification/multipledispatch/conflict.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torch/masked/maskedtensor/binary.py**:
  - `core`

**.venv/lib/python3.12/site-packages/torch/masked/maskedtensor/creation.py**:
  - `core`

**.venv/lib/python3.12/site-packages/torch/masked/maskedtensor/_ops_refs.py**:
  - `core`

**.venv/lib/python3.12/site-packages/torch/masked/maskedtensor/__init__.py**:
  - `core`

**.venv/lib/python3.12/site-packages/torch/masked/maskedtensor/unary.py**:
  - `core`

**.venv/lib/python3.12/site-packages/torch/masked/maskedtensor/reductions.py**:
  - `core`

**.venv/lib/python3.12/site-packages/torch/masked/maskedtensor/passthrough.py**:
  - `core`

**.venv/lib/python3.12/site-packages/torch/_inductor/runtime/autotune_cache.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/codegen/cpp_grouped_gemm_template.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/codegen/cpp_wrapper_gpu.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/codegen/triton_utils.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/codegen/triton.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/codegen/simd.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/codegen/triton_combo_kernel.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/codegen/memory_planning.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/codegen/cpp_wrapper_cpu.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/codegen/common.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/codegen/cpp_template_kernel.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/codegen/cpp_gemm_template.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/codegen/cpp_wrapper_cpu_array_ref.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/codegen/triton_split_scan.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/codegen/halide.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/codegen/multi_kernel.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/codegen/debug_utils.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/compile_worker/subproc_pool.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/fx_passes/post_grad.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/fx_passes/replace_random.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/fx_passes/numeric_utils.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/fx_passes/decompose_mem_bound_mm.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/fx_passes/reinplace.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/fx_passes/efficient_conv_bn_eval.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/fx_passes/group_batch_fusion.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/fx_passes/pre_grad.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/fx_passes/binary_folding.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/fx_passes/micro_pipeline_tp.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/fx_passes/joint_graph.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/fx_passes/pad_mm.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torch/_inductor/fx_passes/freezing_patterns.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/kernel/mm_common.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/kernel/flex_decoding.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/kernel/mm.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/kernel/conv.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/kernel/flex_attention.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/package/package.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/codegen/cuda/cutlass_utils.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/codegen/cuda/cuda_cpp_scheduling.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/codegen/cuda/cuda_env.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/codegen/rocm/rocm_cpp_scheduling.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/codegen/rocm/compile_command.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/codegen/rocm/ck_conv_template.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/codegen/rocm/ck_universal_gemm_template.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_inductor/codegen/rocm/rocm_benchmark_request.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/utils/serialization/__init__.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/testing/_internal/logging_utils.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/testing/_internal/opinfo/core.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torch/_dynamo/backends/debugging.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_dynamo/backends/cudagraphs.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_dynamo/variables/misc.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_dynamo/variables/builder.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_dynamo/variables/tensor.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_dynamo/variables/builtin.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_dynamo/variables/torch.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_dynamo/repro/after_dynamo.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/_dynamo/repro/after_aot.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torch/ao/quantization/quantize.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torch/ao/quantization/__init__.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torch/ao/nn/quantized/modules/linear.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torch/ao/nn/quantized/modules/conv.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torch/ao/nn/quantized/modules/embedding_ops.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torch/ao/nn/quantized/reference/modules/linear.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torch/ao/nn/quantized/reference/modules/sparse.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torch/ao/nn/quantized/reference/modules/conv.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torch/ao/nn/quantized/reference/modules/rnn.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torch/ao/ns/fx/graph_passes.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torch/ao/ns/fx/weight_utils.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torch/ao/quantization/pt2e/export_utils.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torch/ao/quantization/pt2e/qat_utils.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torch/ao/quantization/fx/_equalize.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torch/ao/quantization/fx/convert.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torch/ao/quantization/fx/quantize_handler.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torch/ao/quantization/fx/_lower_to_native_backend.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torch/ao/quantization/fx/prepare.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torch/ao/pruning/sparsifier/base_sparsifier.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/numpy/ma/extras.py**:
  - `core`

**.venv/lib/python3.12/site-packages/numpy/ma/testutils.py**:
  - `core`

**.venv/lib/python3.12/site-packages/numpy/ma/__init__.py**:
  - `core`

**.venv/lib/python3.12/site-packages/numpy/lib/__init__.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/numpy/typing/tests/test_typing.py**:
  - `api`

**.venv/lib/python3.12/site-packages/pip/_vendor/packaging/specifiers.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/pip/_vendor/pyparsing/actions.py**:
  - `core`

**.venv/lib/python3.12/site-packages/pip/_vendor/pyparsing/__init__.py**:
  - `core`

**.venv/lib/python3.12/site-packages/pip/_vendor/pyparsing/common.py**:
  - `core`

**.venv/lib/python3.12/site-packages/pip/_vendor/pyparsing/exceptions.py**:
  - `core`

**.venv/lib/python3.12/site-packages/pip/_vendor/pyparsing/testing.py**:
  - `core`

**.venv/lib/python3.12/site-packages/pip/_vendor/pyparsing/helpers.py**:
  - `core`

**.venv/lib/python3.12/site-packages/pip/_vendor/idna/compat.py**:
  - `core`

**.venv/lib/python3.12/site-packages/pip/_vendor/idna/__init__.py**:
  - `core`

**.venv/lib/python3.12/site-packages/pip/_vendor/idna/codec.py**:
  - `core`

**.venv/lib/python3.12/site-packages/pip/_vendor/requests/auth.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/pip/_vendor/requests/sessions.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/pip/_vendor/requests/models.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/pip/_vendor/requests/__init__.py**:
  - `api`

**.venv/lib/python3.12/site-packages/pip/_vendor/requests/adapters.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/pip/_vendor/certifi/__init__.py**:
  - `core`

**.venv/lib/python3.12/site-packages/pip/_vendor/platformdirs/macos.py**:
  - `api`

**.venv/lib/python3.12/site-packages/pip/_vendor/platformdirs/unix.py**:
  - `api`

**.venv/lib/python3.12/site-packages/pip/_vendor/platformdirs/__init__.py**:
  - `api`

**.venv/lib/python3.12/site-packages/pip/_vendor/platformdirs/android.py**:
  - `api`

**.venv/lib/python3.12/site-packages/pip/_vendor/platformdirs/windows.py**:
  - `api`

**.venv/lib/python3.12/site-packages/pip/_vendor/colorama/tests/isatty_test.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/pip/_vendor/colorama/tests/initialise_test.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/pip/_vendor/colorama/tests/ansitowin32_test.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/transformers/onnx/config.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/transformers/onnx/convert.py**:
  - `config`

**.venv/lib/python3.12/site-packages/transformers/onnx/__init__.py**:
  - `utils`
  - `config`

**.venv/lib/python3.12/site-packages/transformers/onnx/features.py**:
  - `config`

**.venv/lib/python3.12/site-packages/transformers/onnx/__main__.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/transformers/generation/__init__.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/transformers/data/processors/xnli.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/transformers/data/processors/__init__.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/transformers/data/processors/squad.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/transformers/data/processors/glue.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/keyring/backends/macOS/__init__.py**:
  - `api`

**.venv/lib/python3.12/site-packages/hypothesis/extra/array_api.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/hypothesis/extra/numpy.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/hypothesis/strategies/_internal/strategies.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/hypothesis/strategies/_internal/featureflags.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/hypothesis/strategies/_internal/collections.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/hypothesis/extra/pandas/impl.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/torchgen/static_runtime/generator.py**:
  - `config`

**.venv/lib/python3.12/site-packages/torchgen/static_runtime/gen_static_runtime_ops.py**:
  - `config`

**.venv/lib/python3.12/site-packages/weasel/util/__init__.py**:
  - `config`

**.venv/lib/python3.12/site-packages/setuptools/_vendor/packaging/requirements.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/setuptools/_vendor/packaging/markers.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/setuptools/_vendor/packaging/specifiers.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/setuptools/_vendor/platformdirs/macos.py**:
  - `api`

**.venv/lib/python3.12/site-packages/setuptools/_vendor/platformdirs/unix.py**:
  - `api`

**.venv/lib/python3.12/site-packages/setuptools/_vendor/platformdirs/__init__.py**:
  - `api`

**.venv/lib/python3.12/site-packages/setuptools/_vendor/platformdirs/android.py**:
  - `api`

**.venv/lib/python3.12/site-packages/setuptools/_vendor/platformdirs/windows.py**:
  - `api`

**.venv/lib/python3.12/site-packages/setuptools/_vendor/wheel/vendored/packaging/requirements.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/setuptools/_vendor/wheel/vendored/packaging/markers.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/setuptools/_vendor/wheel/vendored/packaging/specifiers.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/setuptools/_distutils/tests/test_config_cmd.py**:
  - `config`

**.venv/lib/python3.12/site-packages/psutil/tests/__init__.py**:
  - `utils`

**.venv/lib/python3.12/site-packages/functorch/compile/__init__.py**:
  - `config`

**gmnap/gmnap/pipeline/__init__.py**:
  - `core`

**modules/unicode_utils_v2/unicode_utils/rate_limiter.py**:
  - `config`

**modules/unicode_utils_v2/unicode_utils/__init__.py**:
  - `cli`
  - `core`

**modules/unicode_utils_v2/unicode_utils/cli.py**:
  - `utils`
  - `core`

**modules/unicode_utils_v2/unicode_utils/utils.py**:
  - `core`

**modules/unicode_utils_v2/unicode_utils/profiles.py**:
  - `core`

**src/pdf_processing/extractors.py**:
  - `config`

**src/pdf_processing/__init__.py**:
  - `parsers`
  - `extractors`

**src/pdf_processing/parsers/base_parser.py**:
  - `config`


### ⚠️  MEDIUM RISK: Configuration Files
**86 configuration files** may need path updates:

**.pre-commit-config.yaml**:
  - `^(grobid/|tests/fixtures/)`
  - `
        
      # File Size Limit - Prevent files over 500 lines
      - id: file-size-check
        name: File Size Limit (500 lines)
        entry: python tools/file_size_check.py --max-lines 500
        language: system
        types: [python]
        fail_fast: true
        description: `
  - `
        
      # Configuration Security - Prevent insecure configuration patterns
      - id: secure-config-check
        name: Secure Configuration Check
        entry: python tools/secure_config_check.py
        language: system
        types: [python]
        description: `
  - `]
        exclude: ^(grobid/|unicode_utils/|tests/fixtures/)

  # Import sorting
  - repo: https://github.com/PyCQA/isort
    rev: 5.13.2
    hooks:
      - id: isort
        args: [`
  - `]
        exclude: ^(tests/fixtures/|\.secrets\.baseline)

  # Python dependency security check
  - repo: https://github.com/Lucas-C/pre-commit-hooks-safety
    rev: v1.3.3
    hooks:
      - id: python-safety-dependencies-check
        files: ^requirements.*\.txt$

  # Check for outdated Python syntax
  - repo: https://github.com/asottile/pyupgrade
    rev: v3.15.0
    hooks:
      - id: pyupgrade
        args: [`
  - `
        ]
        exclude: ^(grobid/|unicode_utils/|tests/fixtures/)
        additional_dependencies: [
          `
  - `
        
      # Forbidden Patterns Enhanced - Block architectural anti-patterns
      - id: forbidden-patterns-arch
        name: Forbidden Pattern Check (Architectural)
        entry: python tools/forbidden_pattern_check.py
        language: system
        types: [python]
        description: `
  - `^(tests/|debug_|test_)`
  - `^(grobid/|unicode_utils/|tests/fixtures/)`
  - `]
        exclude: ^tests/

  # Type checking (optional - can be slow)
  # - repo: https://github.com/pre-commit/mirrors-mypy
  #   rev: v1.8.0
  #   hooks:
  #     - id: mypy
  #       args: [`
  - `^(tests/|grobid/|unicode_utils/)`
  - `^(tests/fixtures/|\.secrets\.baseline)`
  - `
        
      # Multiple Responsibilities - Prevent files doing too many things
      - id: single-responsibility
        name: Single Responsibility Check
        entry: python tools/single_responsibility_check.py --max-responsibilities 1
        language: system
        types: [python]
        exclude: ^(tests/|test_|conftest\.py|__pycache__|\.venv/)
        description: `
  - `^tests/fixtures/`
  - `^(tests/|test_|conftest\.py|__pycache__|\.venv/)`
  - `
        
      # Import Dependency Rules - Enforce architectural boundaries
      - id: dependency-rules
        name: Dependency Rule Check
        entry: python tools/dependency_rule_check.py
        language: system
        pass_filenames: false
        description: `
  - `]
        exclude: ^(tests/|grobid/|unicode_utils/)

  # YAML formatting
  - repo: https://github.com/pre-commit/mirrors-prettier
    rev: v3.1.0
    hooks:
      - id: prettier
        types_or: [yaml, json]
        exclude: ^(grobid/|tests/fixtures/)

  # Check for common security issues
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: [`

**core/config/config_definitions.yaml**:
  - `https://ieeexploreapi.ieee.org/api/v1`
  - `//ieeexploreapi.ieee.org/api/v1`
  - `https://export.arxiv.org/api/query`
  - `//export.arxiv.org/api/query`

**config/grobid/grobid-evaluation.yaml**:
  - `

  # maximum concurrency allowed to GROBID server for processing parallel requests - change it according to your CPU/GPU capacities
  # for a production server running only GROBID, set the value slightly above the available number of threads of the server
  # to get best performance and security
  concurrency: 10
  # when the pool is full, for queries waiting for the availability of a Grobid engine, this is the maximum time wait to try
  # to get an engine (in seconds) - normally never change it
  poolMaxWait: 1

  delft:
    # DeLFT global parameters
    # delft installation path if Deep Learning architectures are used to implement one of the sequence labeling model,
    # embeddings are usually compiled as lmdb under delft/data (this parameter is ignored if only featured-engineered CRF are used)
    install: `

**config/grobid/grobid-full.yaml**:
  - `

  # maximum concurrency allowed to GROBID server for processing parallel requests - change it according to your CPU/GPU capacities
  # for a production server running only GROBID, set the value slightly above the available number of threads of the server
  # to get best performance and security
  concurrency: 10
  # when the pool is full, for queries waiting for the availability of a Grobid engine, this is the maximum time wait to try
  # to get an engine (in seconds) - normally never change it
  poolMaxWait: 1

  delft:
    # DeLFT global parameters
    # delft installation path if Deep Learning architectures are used to implement one of the sequence labeling model,
    # embeddings are usually compiled as lmdb under delft/data (this parameter is ignored if only featured-engineered CRF are used)
    install: `

**config/grobid/grobid.yaml**:
  - `
  
  # maximum concurrency allowed to GROBID server for processing parallel requests - change it according to your CPU/GPU capacities
  # for a production server running only GROBID, set the value slightly above the available number of threads of the server
  # to get best performance and security
  concurrency: 10
  # when the pool is full, for queries waiting for the availability of a Grobid engine, this is the maximum time wait to try 
  # to get an engine (in seconds) - normally never change it
  poolMaxWait: 1

  delft:
    # DeLFT global parameters
    # delft installation path if Deep Learning architectures are used to implement one of the sequence labeling model, 
    # embeddings are usually compiled as lmdb under delft/data (this parameter is ignored if only featured-engineered CRF are used)
    install: `

**.venv/lib/python3.12/site-packages/markdown_it/port.yaml**:
  - `t do e.g. `for {i=1;i<x;i++} {}`
    - |
      `env` is a common Python dictionary, and so does not have attribute access to keys,
      as with JavaScript dictionaries.
      `options` have attribute access only to core markdownit configuration options
    - |
      `Token.attrs` is a dictionary, instead of a list of lists.
      Upstream the list format is only used to guarantee order: https://github.com/markdown-it/markdown-it/issues/142,
      but in Python 3.7+ order of dictionaries is guaranteed.
      One should anyhow use the `attrGet`, `attrSet`, `attrPush` and `attrJoin` methods
      to manipulate `Token.attrs`, which have an identical signature to those upstream.
    - Use python version of `charCodeAt`
    - |
      Use `str` units instead of `int`s to represent Unicode codepoints.
      This provides a significant performance boost
    - |
      In markdown_it/rules_block/reference.py,
      record line range in state.env[`

**.venv/lib/python3.12/site-packages/torchgen/packaged/autograd/derivatives.yaml**:
  - `

# PackedSequence helpers
- name: _pack_padded_sequence(Tensor input, Tensor lengths, bool batch_first) -> (Tensor, Tensor)
  input: _pack_padded_sequence_backward_symint(grad, input.sym_sizes(), result1, batch_first)

# TH wrappers
- name: eq.Scalar(Tensor self, Scalar other) -> Tensor
  output_differentiability: [False]

- name: eq.Tensor(Tensor self, Tensor other) -> Tensor
  output_differentiability: [False]

- name: ge.Scalar(Tensor self, Scalar other) -> Tensor
  output_differentiability: [False]

- name: ge.Tensor(Tensor self, Tensor other) -> Tensor
  output_differentiability: [False]

- name: gt.Scalar(Tensor self, Scalar other) -> Tensor
  output_differentiability: [False]

- name: gt.Tensor(Tensor self, Tensor other) -> Tensor
  output_differentiability: [False]

- name: le.Scalar(Tensor self, Scalar other) -> Tensor
  output_differentiability: [False]

- name: le.Tensor(Tensor self, Tensor other) -> Tensor
  output_differentiability: [False]

- name: lt.Scalar(Tensor self, Scalar other) -> Tensor
  output_differentiability: [False]

- name: lt.Tensor(Tensor self, Tensor other) -> Tensor
  output_differentiability: [False]

- name: ne.Scalar(Tensor self, Scalar other) -> Tensor
  output_differentiability: [False]

- name: ne.Tensor(Tensor self, Tensor other) -> Tensor
  output_differentiability: [False]

- name: multinomial(Tensor self, int num_samples, bool replacement=False, *, Generator? generator=None) -> Tensor
  output_differentiability: [False]

- name: nonzero(Tensor self) -> Tensor
  output_differentiability: [False]

- name: segment_reduce(Tensor data, str reduce, *, Tensor? lengths=None, Tensor? indices=None, Tensor? offsets=None, int axis=0, bool unsafe=False, Scalar? initial=None) -> Tensor
  data: _segment_reduce_backward(grad, result, data, reduce, lengths, offsets, axis, initial)

- name: _pin_memory(Tensor self, Device? device=None) -> Tensor
  self: grad

- name: _new_zeros_with_same_feature_meta(Tensor self, Tensor other, *, int self_num_batch_dims=0) -> Tensor
  self: non_differentiable
  other: non_differentiable
  output_differentiability: [False]

- name: _test_warn_in_autograd(Tensor self) -> Tensor
  self: warn_backwards(grad)

- name: _test_autograd_multiple_dispatch.fullcoverage(Tensor self) -> Tensor
  dispatch:
    Default:
      self: grad.expand_symint(self.sym_sizes()) + 1
      result: auto_linear
    AutogradNestedTensor:
      self: grad.mul(grad)
    AutogradCUDA:
      self: grad.expand_symint(self.sym_sizes()) * 2

- name: _test_autograd_multiple_dispatch.ntonly(Tensor self, bool b) -> Tensor
  dispatch:
    AutogradNestedTensor:
      self: grad.mul(grad).add(grad)

- name: _test_autograd_multiple_dispatch_view(Tensor(a) self) -> Tensor(a)
  dispatch:
    Default:
      self: grad.reshape_as(self)
    AutogradCUDA:
      self: grad.reshape_as(self) + 1

- name: _efficientzerotensor(SymInt[] size, *, ScalarType? dtype=None, Layout? layout=None, Device? device=None, bool? pin_memory=None) -> Tensor
  output_differentiability: [False]

- name: scatter_reduce.two(Tensor self, int dim, Tensor index, Tensor src, str reduce, *, bool include_self=True) -> Tensor
  self, src: scatter_reduce_backward(grad, self, dim, index, src, reduce, include_self, result)
  index: non_differentiable
  result: scatter_reduce_jvp(self_p, self_t, dim, index, src_p, src_t, reduce, include_self, result)

- name: special_airy_ai(Tensor x) -> Tensor
  x: non_differentiable

- name: special_bessel_j0(Tensor self) -> Tensor
  self: non_differentiable

- name: special_bessel_j1(Tensor self) -> Tensor
  self: non_differentiable

- name: special_bessel_y0(Tensor self) -> Tensor
  self: non_differentiable

- name: special_bessel_y1(Tensor self) -> Tensor
  self: non_differentiable

- name: special_chebyshev_polynomial_t(Tensor x, Tensor n) -> Tensor
  x: non_differentiable
  n: non_differentiable

- name: special_chebyshev_polynomial_t.x_scalar(Scalar x, Tensor n) -> Tensor
  n: non_differentiable

- name: special_chebyshev_polynomial_t.n_scalar(Tensor x, Scalar n) -> Tensor
  x: non_differentiable

- name: special_chebyshev_polynomial_u(Tensor x, Tensor n) -> Tensor
  x: non_differentiable
  n: non_differentiable

- name: special_chebyshev_polynomial_u.x_scalar(Scalar x, Tensor n) -> Tensor
  n: non_differentiable

- name: special_chebyshev_polynomial_u.n_scalar(Tensor x, Scalar n) -> Tensor
  x: non_differentiable

- name: special_chebyshev_polynomial_v(Tensor x, Tensor n) -> Tensor
  x: non_differentiable
  n: non_differentiable

- name: special_chebyshev_polynomial_v.x_scalar(Scalar x, Tensor n) -> Tensor
  n: non_differentiable

- name: special_chebyshev_polynomial_v.n_scalar(Tensor x, Scalar n) -> Tensor
  x: non_differentiable

- name: special_chebyshev_polynomial_w(Tensor x, Tensor n) -> Tensor
  x: non_differentiable
  n: non_differentiable

- name: special_chebyshev_polynomial_w.x_scalar(Scalar x, Tensor n) -> Tensor
  n: non_differentiable

- name: special_chebyshev_polynomial_w.n_scalar(Tensor x, Scalar n) -> Tensor
  x: non_differentiable

- name: special_hermite_polynomial_h(Tensor x, Tensor n) -> Tensor
  x: non_differentiable
  n: non_differentiable

- name: special_hermite_polynomial_h.x_scalar(Scalar x, Tensor n) -> Tensor
  n: non_differentiable

- name: special_hermite_polynomial_h.n_scalar(Tensor x, Scalar n) -> Tensor
  x: non_differentiable

- name: special_hermite_polynomial_he(Tensor x, Tensor n) -> Tensor
  x: non_differentiable
  n: non_differentiable

- name: special_hermite_polynomial_he.x_scalar(Scalar x, Tensor n) -> Tensor
  n: non_differentiable

- name: special_hermite_polynomial_he.n_scalar(Tensor x, Scalar n) -> Tensor
  x: non_differentiable

- name: special_laguerre_polynomial_l(Tensor x, Tensor n) -> Tensor
  x: non_differentiable
  n: non_differentiable

- name: special_laguerre_polynomial_l.x_scalar(Scalar x, Tensor n) -> Tensor
  n: non_differentiable

- name: special_laguerre_polynomial_l.n_scalar(Tensor x, Scalar n) -> Tensor
  x: non_differentiable

- name: special_legendre_polynomial_p(Tensor x, Tensor n) -> Tensor
  x: non_differentiable
  n: non_differentiable

- name: special_legendre_polynomial_p.x_scalar(Scalar x, Tensor n) -> Tensor
  n: non_differentiable

- name: special_legendre_polynomial_p.n_scalar(Tensor x, Scalar n) -> Tensor
  x: non_differentiable

- name: special_modified_bessel_i0(Tensor self) -> Tensor
  self: non_differentiable

- name: special_modified_bessel_i1(Tensor self) -> Tensor
  self: non_differentiable

- name: special_modified_bessel_k0(Tensor self) -> Tensor
  self: non_differentiable

- name: special_modified_bessel_k1(Tensor self) -> Tensor
  self: non_differentiable

- name: special_scaled_modified_bessel_k0(Tensor x) -> Tensor
  x: non_differentiable

- name: special_scaled_modified_bessel_k1(Tensor x) -> Tensor
  x: non_differentiable

- name: special_shifted_chebyshev_polynomial_t(Tensor x, Tensor n) -> Tensor
  x: non_differentiable
  n: non_differentiable

- name: special_shifted_chebyshev_polynomial_t.x_scalar(Scalar x, Tensor n) -> Tensor
  n: non_differentiable

- name: special_shifted_chebyshev_polynomial_t.n_scalar(Tensor x, Scalar n) -> Tensor
  x: non_differentiable

- name: special_shifted_chebyshev_polynomial_u(Tensor x, Tensor n) -> Tensor
  x: non_differentiable
  n: non_differentiable

- name: special_shifted_chebyshev_polynomial_u.x_scalar(Scalar x, Tensor n) -> Tensor
  n: non_differentiable

- name: special_shifted_chebyshev_polynomial_u.n_scalar(Tensor x, Scalar n) -> Tensor
  x: non_differentiable

- name: special_shifted_chebyshev_polynomial_v(Tensor x, Tensor n) -> Tensor
  x: non_differentiable
  n: non_differentiable

- name: special_shifted_chebyshev_polynomial_v.x_scalar(Scalar x, Tensor n) -> Tensor
  n: non_differentiable

- name: special_shifted_chebyshev_polynomial_v.n_scalar(Tensor x, Scalar n) -> Tensor
  x: non_differentiable

- name: special_shifted_chebyshev_polynomial_w(Tensor x, Tensor n) -> Tensor
  x: non_differentiable
  n: non_differentiable

- name: special_shifted_chebyshev_polynomial_w.x_scalar(Scalar x, Tensor n) -> Tensor
  n: non_differentiable

- name: special_shifted_chebyshev_polynomial_w.n_scalar(Tensor x, Scalar n) -> Tensor
  x: non_differentiable

- name: special_spherical_bessel_j0(Tensor x) -> Tensor
  x: non_differentiable

- name: _reshape_copy(Tensor self, SymInt[] size) -> Tensor
  self: grad.reshape_symint(self.sym_sizes())
  result: auto_linear

# note(crcrpar): `torchgen/api/autograd` logic would unwantedly replace substrings of `self` and `other` of function names.
- name: _foreach_div.List(Tensor[] self, Tensor[] other) -> Tensor[]
  self: div_tensor_self_backward(grads[i], other[i], self[i].scalar_type())
  other: div_tensor_other_backward(grads[i], self[i], other[i])
  result: (self_t - other_t * result[i]) / other_p

- name: _foreach_pow.List(Tensor[] self, Tensor[] exponent) -> Tensor[]
  self: pow_backward_self(grads[i], self[i], exponent[i])
  exponent: pow_backward_exponent(grads[i], self[i], exponent[i], result[i])
  result: (pow_backward_self(self_t.conj(), self_p, exponent_p) + pow_backward_exponent(exponent_t.conj(), self_p, exponent_p, result[i])).conj()

- name: _foreach_pow.ScalarList(Tensor[] self, Scalar[] exponent) -> Tensor[]
  self: pow_backward(grads[i], self[i], exponent[i])
  result: pow_backward(self_t.conj(), self_p, exponent[i]).conj()

- name: _foreach_pow.ScalarAndTensor(Scalar self, Tensor[] exponent) -> Tensor[]
  exponent: pow_backward_exponent(grads[i], self, exponent[i], result[i])

# note(crcrpar): following definitions seem necessary because the reference native functions
# of `maximum` and `minimum` don`
  - ``torchgen/api/autograd``
  - `) -> Tensor
  grad_output: gelu_backward(grad, self, approximate)
  self: gelu_double_backward(grad, grad_output, self, approximate)
  result: gelu_backward(grad_output_t, self_p, approximate) + gelu_double_backward(self_t, grad_output_p, self_p, approximate)

- name: glu(Tensor self, int dim=-1) -> Tensor
  # TODO: glu_backward can benefit from forward result,
  # and forward ad/forward over reverse ad for that matter
  self: glu_backward(grad, self, dim)
  result: glu_jvp(result, self_p, self_t, dim)

- name: hardshrink(Tensor self, Scalar lambd=0.5) -> Tensor
  self: hardshrink_backward(grad, self, lambd)
  result: auto_element_wise

- name: hardshrink_backward(Tensor grad_out, Tensor self, Scalar lambd) -> Tensor
  grad_out: hardshrink_backward(grad, self, lambd)
  self: zeros_like(grad)
  result: at::where((self_p > lambd).logical_or(self_p < -lambd), grad_out_t, at::zeros({}, result.options()).expand_as(result))

- name: hardtanh(Tensor self, Scalar min_val=-1, Scalar max_val=1) -> Tensor
  self: hardtanh_backward(grad, self, min_val, max_val)
  result: auto_element_wise

- name: leaky_relu(Tensor self, Scalar negative_slope=0.01) -> Tensor
  self: leaky_relu_backward(grad, self, negative_slope, false)
  result: auto_element_wise

- name: leaky_relu_(Tensor(a!) self, Scalar negative_slope=0.01) -> Tensor(a!)
  self: leaky_relu_backward(grad, result, negative_slope, true)
  result: self_t.copy_(leaky_relu_backward(original_self_t.conj(), result, negative_slope, true).conj())

- name: log_sigmoid_forward(Tensor self) -> (Tensor output, Tensor buffer)
  self: log_sigmoid_backward(grad, self, buffer)
  output: log_sigmoid_backward(self_t.conj(), self_p, buffer).conj()
  output_differentiability: [True, False]

- name: _log_softmax(Tensor self, int dim, bool half_to_float) -> Tensor
  self: _log_softmax_backward_data(grad, result, dim, self.scalar_type())
  result: self_t - logsumexp_jvp(self_p, self_t, {dim}, true)

- name: _sparse_log_softmax(Tensor self, int dim, bool half_to_float) -> Tensor
  self: _sparse_log_softmax_backward_data(grad, result, dim, self)

- name: _masked_softmax(Tensor self, Tensor mask, int? dim=None, int? mask_type=None) -> Tensor
  self: _masked_softmax_backward(grad, result, mask, dim)
  mask: non_differentiable

- name: _prelu_kernel(Tensor self, Tensor weight) -> Tensor
  self, weight: `
  - `
  result0: at::where(self_p >= 0, grad_output_t, grad_output_t * weight_p + grad_output_p * weight_t)
  result1: at::where(self_p >= 0, at::zeros({}, self_p.options()), grad_output_p * self_t + grad_output_t * self_p)

- name: rrelu_with_noise(Tensor self, Tensor(b!) noise, Scalar lower=0.125, Scalar upper=0.3333333333333333, bool training=False, Generator? generator=None) -> Tensor
  self: rrelu_with_noise_backward(grad, self, noise, lower, upper, training, false)
  result: auto_element_wise

- name: rrelu_with_noise_(Tensor(a!) self, Tensor(b!) noise, Scalar lower=0.125, Scalar upper=0.3333333333333333, bool training=False, Generator? generator=None) -> Tensor(a!)
  self: rrelu_with_noise_backward(grad, result, noise, lower, upper, training, true)

- name: rrelu_with_noise_functional(Tensor self, Tensor noise, Scalar lower=0.125, Scalar upper=0.3333333333333333, bool training=False, Generator? generator=None) -> (Tensor, Tensor noise_out)
  noise: non_differentiable
  self: rrelu_with_noise_backward(grad, self, noise, lower, upper, training, false)

- name: _softmax(Tensor self, int dim, bool half_to_float) -> Tensor
  self: _softmax_backward_data(grad, result, dim, self.scalar_type())
  result: result * (self_t - logsumexp_jvp(self_p, self_t, {dim}, true))

- name: _sparse_softmax(Tensor self, int dim, bool half_to_float) -> Tensor
  self: _sparse_softmax_backward_data(grad, result, dim, self)

- name: _sparse_sparse_matmul(Tensor self, Tensor other) -> Tensor
  self: sparse_sparse_matmul_backward(grad, self, other, 0)
  other: sparse_sparse_matmul_backward(grad, self, other, 1)

- name: softplus(Tensor self, Scalar beta=1, Scalar threshold=20) -> Tensor
  self: softplus_backward(grad, self, beta, threshold)
  result: auto_element_wise

- name: softshrink(Tensor self, Scalar lambd=0.5) -> Tensor
  self: softshrink_backward(grad, self, lambd)
  result: auto_element_wise

- name: threshold(Tensor self, Scalar threshold, Scalar value) -> Tensor
  self: threshold_backward(grad, self, threshold)
  result: auto_element_wise

- name: threshold_(Tensor(a!) self, Scalar threshold, Scalar value) -> Tensor(a!)
  self: threshold_backward(grad, self, threshold)
  result: self_t.copy_(threshold_backward(self_t.conj(), original_self_p, threshold).conj())

- name: reflection_pad1d(Tensor self, SymInt[2] padding) -> Tensor
  self: reflection_pad1d_backward_symint(grad, self, padding)
  result: auto_linear

- name: reflection_pad2d(Tensor self, SymInt[4] padding) -> Tensor
  self: reflection_pad2d_backward_symint(grad, self, padding)
  result: auto_linear

- name: reflection_pad3d(Tensor self, SymInt[6] padding) -> Tensor
  self: reflection_pad3d_backward_symint(grad, self, padding)
  result: auto_linear

- name: replication_pad1d(Tensor self, SymInt[2] padding) -> Tensor
  self: replication_pad1d_backward_symint(grad, self, padding)
  result: auto_linear

- name: replication_pad2d(Tensor self, SymInt[4] padding) -> Tensor
  self: replication_pad2d_backward_symint(grad, self, padding)
  result: auto_linear

- name: replication_pad3d(Tensor self, SymInt[6] padding) -> Tensor
  self: replication_pad3d_backward_symint(grad, self, padding)
  result: auto_linear

- name: upsample_linear1d(Tensor self, SymInt[1] output_size, bool align_corners, float? scales=None) -> Tensor
  self: upsample_linear1d_backward_symint(grad, output_size, self.sym_sizes(), align_corners, scales)
  result: auto_linear

- name: upsample_bilinear2d(Tensor self, SymInt[2] output_size, bool align_corners, float? scales_h=None, float? scales_w=None) -> Tensor
  self: upsample_bilinear2d_backward_symint(grad, output_size, self.sym_sizes(), align_corners, scales_h, scales_w)
  result: auto_linear

- name: _upsample_bilinear2d_aa(Tensor self, SymInt[2] output_size, bool align_corners, float? scales_h=None, float? scales_w=None) -> Tensor
  self: _upsample_bilinear2d_aa_backward_symint(grad, output_size, self.sym_sizes(), align_corners, scales_h, scales_w)
  result: auto_linear

- name: upsample_bicubic2d(Tensor self, SymInt[2] output_size, bool align_corners, float? scales_h=None, float? scales_w=None) -> Tensor
  self: upsample_bicubic2d_backward_symint(grad, output_size, self.sym_sizes(), align_corners, scales_h, scales_w)
  result: auto_linear

- name: _upsample_bicubic2d_aa(Tensor self, SymInt[2] output_size, bool align_corners, float? scales_h=None, float? scales_w=None) -> Tensor
  self: _upsample_bicubic2d_aa_backward_symint(grad, output_size, self.sym_sizes(), align_corners, scales_h, scales_w)
  result: auto_linear

- name: upsample_trilinear3d(Tensor self, SymInt[3] output_size, bool align_corners, float? scales_d=None, float? scales_h=None, float? scales_w=None) -> Tensor
  self: upsample_trilinear3d_backward_symint(grad, output_size, self.sym_sizes(), align_corners, scales_d, scales_h, scales_w)
  result: auto_linear

- name: upsample_nearest1d(Tensor self, SymInt[1] output_size, float? scales=None) -> Tensor
  self: upsample_nearest1d_backward_symint(grad, output_size, self.sym_sizes(), scales)
  result: auto_linear

- name: _upsample_nearest_exact1d(Tensor self, SymInt[1] output_size, float? scales=None) -> Tensor
  self: _upsample_nearest_exact1d_backward_symint(grad, output_size, self.sym_sizes(), scales)
  result: auto_linear

- name: upsample_nearest2d(Tensor self, SymInt[2] output_size, float? scales_h=None, float? scales_w=None) -> Tensor
  self: upsample_nearest2d_backward_symint(grad, output_size, self.sym_sizes(), scales_h, scales_w)
  result: auto_linear

- name: _upsample_nearest_exact2d(Tensor self, SymInt[2] output_size, float? scales_h=None, float? scales_w=None) -> Tensor
  self: _upsample_nearest_exact2d_backward_symint(grad, output_size, self.sym_sizes(), scales_h, scales_w)
  result: auto_linear

- name: upsample_nearest3d(Tensor self, SymInt[3] output_size, float? scales_d=None, float? scales_h=None, float? scales_w=None) -> Tensor
  self: upsample_nearest3d_backward_symint(grad, output_size, self.sym_sizes(), scales_d, scales_h, scales_w)
  result: auto_linear

- name: _upsample_nearest_exact3d(Tensor self, SymInt[3] output_size, float? scales_d=None, float? scales_h=None, float? scales_w=None) -> Tensor
  self: _upsample_nearest_exact3d_backward_symint(grad, output_size, self.sym_sizes(), scales_d, scales_h, scales_w)
  result: auto_linear

- name: pixel_shuffle(Tensor self, int upscale_factor) -> Tensor
  self: pixel_unshuffle(grad, upscale_factor)
  result: auto_linear

- name: pixel_unshuffle(Tensor self, int downscale_factor) -> Tensor
  self: pixel_shuffle(grad, downscale_factor)
  result: auto_linear

- name: channel_shuffle(Tensor self, SymInt groups) -> Tensor
  self: channel_shuffle_symint(grad, grad.sym_size(1) / groups)
  result: auto_linear

- name: _adaptive_avg_pool2d(Tensor self, SymInt[2] output_size) -> Tensor
  self: _adaptive_avg_pool2d_backward(grad, self)
  result: auto_linear

- name: _adaptive_avg_pool3d(Tensor self, SymInt[3] output_size) -> Tensor
  self: _adaptive_avg_pool3d_backward(grad, self)
  result: auto_linear

- name: adaptive_max_pool2d(Tensor self, int[2] output_size) -> (Tensor, Tensor)
  self: adaptive_max_pool2d_backward(grad, self, result1)
  result0: gather(self_t.flatten(-2), -1, result1.flatten(-2)).view_as(result1)
  output_differentiability: [True, False]

- name: adaptive_max_pool3d(Tensor self, int[3] output_size) -> (Tensor, Tensor)
  self: adaptive_max_pool3d_backward(grad, self, result1)
  result0: gather(self_t.flatten(-3), -1, result1.flatten(-3)).view_as(result1)
  output_differentiability: [True, False]

- name: avg_pool2d(Tensor self, int[2] kernel_size, int[2] stride=[], int[2] padding=0, bool ceil_mode=False, bool count_include_pad=True, int? divisor_override=None) -> Tensor
  self: avg_pool2d_backward(grad, self, kernel_size, stride, padding, ceil_mode, count_include_pad, divisor_override)
  result: auto_linear

- name: avg_pool3d(Tensor self, int[3] kernel_size, int[3] stride=[], int[3] padding=0, bool ceil_mode=False, bool count_include_pad=True, int? divisor_override=None) -> Tensor
  self: avg_pool3d_backward(grad, self, kernel_size, stride, padding, ceil_mode, count_include_pad, divisor_override)
  result: auto_linear

- name: fractional_max_pool2d(Tensor self, int[2] kernel_size, int[2] output_size, Tensor random_samples) -> (Tensor, Tensor)
  self: fractional_max_pool2d_backward(grad, self, kernel_size, output_size, result1)
  result0: gather(self_t.flatten(-2), -1, result1.flatten(-2)).view_as(result1)
  output_differentiability: [True, False]

- name: fractional_max_pool3d(Tensor self, int[3] kernel_size, int[3] output_size, Tensor random_samples) -> (Tensor, Tensor)
  self: fractional_max_pool3d_backward(grad, self, kernel_size, output_size, result1)
  result0: gather(self_t.flatten(-3), -1, result1.flatten(-3)).view_as(result1)
  output_differentiability: [True, False]

- name: linear(Tensor input, Tensor weight, Tensor? bias=None) -> Tensor
  input, weight, bias: `

**.venv/lib/python3.12/site-packages/torchgen/packaged/ATen/native/native_functions.yaml**:
  - ` underscore and be bound to the desired Python name in
#   torch/fft/__init__.py, and the desired C++ name in torch/csrc/api/include/torch/fft.h.
#   The `
  - ` to split args

- func: rot90(Tensor self, int k=1, int[] dims=[0,1]) -> Tensor
  variants: function, method
  dispatch:
    CompositeExplicitAutograd: rot90
  autogen: rot90.out

- func: trapezoid.x(Tensor y, Tensor x, *, int dim=-1) -> Tensor

- func: trapezoid.dx(Tensor y, *, Scalar dx=1, int dim=-1) -> Tensor

- func: trapz.x(Tensor y, Tensor x, *, int dim=-1) -> Tensor

- func: trapz.dx(Tensor y, *, float dx=1, int dim=-1) -> Tensor

# Fused implementation detail for transformers. Adds in-projection bias to QKV and divides Q by sqrt(D/num_heads).
- func: _transform_bias_rescale_qkv(Tensor qkv, Tensor qkv_bias, int num_heads) -> (Tensor, Tensor, Tensor)
  dispatch:
    CPU, NestedTensorCPU: transform_bias_rescale_qkv_cpu
    CUDA, NestedTensorCUDA: transform_bias_rescale_qkv_cuda
  autogen: _transform_bias_rescale_qkv.out

- func: _nested_tensor_from_mask(Tensor t, Tensor mask, bool mask_check=True) -> Tensor
  dispatch:
    CPU, CUDA: NestedTensor_nested_tensor_from_mask
  autogen: _nested_tensor_from_mask.out

- func: _nested_tensor_from_mask_left_aligned(Tensor t, Tensor mask) -> bool
  dispatch:
    CPU, CUDA: NestedTensor_nested_tensor_from_mask_left_aligned

- func: _nested_from_padded(Tensor padded, Tensor cpu_nested_shape_example, bool fuse_transform_0213=False) -> Tensor
  device_check: NoCheck # cpu_nested_shape_example will always be on CPU
  dispatch:
    CPU: nested_from_padded_generic
    CUDA: nested_from_padded_cuda
  autogen: _nested_from_padded.out

# These private functions are temporary. They will be updated/deleted when nested tensors switch to using SymInts for their metadata representation
- func: _nested_tensor_size(Tensor self) -> Tensor
  variants: method
  dispatch:
    NestedTensorCPU, NestedTensorCUDA: _nested_tensor_size
  autogen: _nested_tensor_size.out

- func: _nested_tensor_strides(Tensor self) -> Tensor
  variants: method
  dispatch:
    NestedTensorCPU, NestedTensorCUDA: _nested_tensor_strides
  autogen: _nested_tensor_strides.out

- func: _nested_tensor_storage_offsets(Tensor self) -> Tensor
  variants: method
  dispatch:
    NestedTensorCPU, NestedTensorCUDA, NestedTensorMeta: _nested_tensor_storage_offsets
  autogen: _nested_tensor_storage_offsets.out

# _nested_from_padded is not usable from Python, so
# _nested_from_padded_and_nested_example is available for testing.
- func: _nested_from_padded_and_nested_example(Tensor padded, Tensor nt_example) -> Tensor
  dispatch:
    NestedTensorCPU, NestedTensorCUDA: NestedTensor_from_padded_and_nested_example
  autogen: _nested_from_padded_and_nested_example.out

# The input arguments`
  - `t do any check but only directly sets the flag. So it can be
# a bit unsafe. Similar to _indices and _values, this is useful for implementing
# custom sparse operations in Python/C++ extension.
- func: _coalesced_(Tensor(a!) self, bool coalesced) -> Tensor(a!)
  variants: method
  dispatch:
    SparseCPU, SparseCUDA, SparseMeta: _coalesced_sparse_
  device_check: NoCheck
  device_guard: False
  autogen: _coalesced, _coalesced.out

- func: indices(Tensor(a) self) -> Tensor(a)
  variants: method
  dispatch:
    SparseCPU, SparseCUDA, SparseMeta: indices_sparse
    CompositeExplicitAutograd: indices_default
  device_check: NoCheck
  device_guard: False

- func: values(Tensor(a) self) -> Tensor(a)
  variants: method
  dispatch:
    SparseCPU, SparseCUDA, SparseMeta: values_sparse
    SparseCsrCPU, SparseCsrCUDA, SparseCsrMeta: values_sparse_csr
    NestedTensorCPU, NestedTensorCUDA: values_nested
    CompositeExplicitAutograd: values_default
  device_check: NoCheck
  device_guard: False

- func: crow_indices(Tensor(a) self) -> Tensor(a)
  variants: method
  dispatch:
    SparseCsrCPU, SparseCsrCUDA, SparseCsrMeta: crow_indices_sparse_csr
    CompositeExplicitAutograd: crow_indices_default
  device_check: NoCheck
  device_guard: False

- func: col_indices(Tensor(a) self) -> Tensor(a)
  variants: method
  dispatch:
    SparseCsrCPU, SparseCsrCUDA, SparseCsrMeta: col_indices_sparse_csr
    CompositeExplicitAutograd: col_indices_default
  device_check: NoCheck
  device_guard: False

- func: ccol_indices(Tensor(a) self) -> Tensor(a)
  variants: method
  dispatch:
    SparseCsrCPU, SparseCsrCUDA, SparseCsrMeta: ccol_indices_sparse_csr
    CompositeExplicitAutograd: ccol_indices_default
  device_check: NoCheck
  device_guard: False

- func: row_indices(Tensor(a) self) -> Tensor(a)
  variants: method
  dispatch:
    SparseCsrCPU, SparseCsrCUDA, SparseCsrMeta: row_indices_sparse_csr
    CompositeExplicitAutograd: row_indices_default
  device_check: NoCheck
  device_guard: False

- func: hspmm.out(Tensor mat1, Tensor mat2, *, Tensor(a!) out) -> Tensor(a!)
  dispatch:
    SparseCPU: hspmm_out_sparse_cpu
    SparseCUDA: hspmm_out_sparse_cuda

- func: hspmm(Tensor mat1, Tensor mat2) -> Tensor
  dispatch:
    SparseCPU: hspmm_sparse_cpu
    SparseCUDA: hspmm_sparse_cuda

- func: copy_sparse_to_sparse_(Tensor(a!) self, Tensor src, bool non_blocking=False) -> Tensor(a!)
  device_check: NoCheck  # Allows copy into different device
  variants: function
  dispatch:
    SparseCPU, SparseCUDA, SparseMeta: copy_sparse_
  autogen: copy_sparse_to_sparse, copy_sparse_to_sparse.out

# By adding the AutogradNestedTensor this makes this function CompositeImplicit-like for nested tensors
- func: unbind.int(Tensor(a -> *) self, int dim=0) -> Tensor(a)[]
  variants: function, method
  dispatch:
    CompositeExplicitAutograd: unbind
    NestedTensorCPU, NestedTensorCUDA: NestedTensor_unbind

- func: unbind.Dimname(Tensor(a -> *) self, Dimname dim) -> Tensor(a)[]
  variants: function, method

- func: to_sparse.sparse_dim(Tensor self, int sparse_dim) -> Tensor
  variants: method

# Special case of to_sparse.sparse_dim with custom derivative
- func: _to_sparse.sparse_dim(Tensor self, int sparse_dim) -> Tensor
  variants: method
  dispatch:
    CPU, CUDA: dense_to_sparse
    SparseCPU, SparseCUDA: sparse_coo_to_sparse
    SparseCsrCPU, SparseCsrCUDA, SparseCsrMeta: sparse_compressed_to_sparse
  autogen: _to_sparse.sparse_dim_out

- func: to_sparse(Tensor self, *, Layout? layout=None, int[2]? blocksize=None, int? dense_dim=None) -> Tensor
  variants: method

# Special case of to_sparse with custom derivative
- func: _to_sparse(Tensor self, *, Layout? layout=None, int[2]? blocksize=None, int? dense_dim=None) -> Tensor
  variants: method
  dispatch:
    CPU, CUDA: dense_to_sparse
    SparseCPU, SparseCUDA: sparse_coo_to_sparse
    SparseCsrCPU, SparseCsrCUDA, SparseCsrMeta: sparse_compressed_to_sparse
  autogen: _to_sparse.out

- func: to_sparse_csr(Tensor self, int? dense_dim=None) -> Tensor
  variants: method

# Special case of to_sparse_csr with custom derivative
- func: _to_sparse_csr(Tensor self, int? dense_dim=None) -> Tensor
  variants: method
  dispatch:
    CPU, CUDA: dense_to_sparse_csr
    SparseCPU, SparseCUDA: coo_to_sparse_csr
    SparseCsrCPU, SparseCsrCUDA, SparseCsrMeta: sparse_compressed_to_sparse_csr
  autogen: _to_sparse_csr.out

- func: to_sparse_csc(Tensor self, int? dense_dim=None) -> Tensor
  variants: method

# Special case of to_sparse_csc with custom derivative
- func: _to_sparse_csc(Tensor self, int? dense_dim=None) -> Tensor
  variants: method
  dispatch:
    CPU, CUDA: dense_to_sparse_csc
    SparseCPU, SparseCUDA: coo_to_sparse_csc
    SparseCsrCPU, SparseCsrCUDA, SparseCsrMeta: sparse_compressed_to_sparse_csc
  autogen: _to_sparse_csc.out

- func: to_sparse_bsr(Tensor self, int[2] blocksize, int? dense_dim=None) -> Tensor
  variants: method

# Special case of to_sparse_bsr with custom derivative
- func: _to_sparse_bsr(Tensor self, int[2] blocksize, int? dense_dim=None) -> Tensor
  variants: method
  dispatch:
    CPU, CUDA: dense_to_sparse_bsr
    SparseCPU, SparseCUDA: coo_to_sparse_bsr
    SparseCsrCPU, SparseCsrCUDA, SparseCsrMeta: sparse_compressed_to_sparse_bsr
  autogen: _to_sparse_bsr.out

- func: to_sparse_bsc(Tensor self, int[2] blocksize, int? dense_dim=None) -> Tensor
  variants: method

# Special case of to_sparse_bsc with custom derivative
- func: _to_sparse_bsc(Tensor self, int[2] blocksize, int? dense_dim=None) -> Tensor
  variants: method
  dispatch:
    CPU, CUDA: dense_to_sparse_bsc
    SparseCPU, SparseCUDA: coo_to_sparse_bsc
    SparseCsrCPU, SparseCsrCUDA, SparseCsrMeta: sparse_compressed_to_sparse_bsc
  autogen: _to_sparse_bsc.out

- func: _to_sparse_semi_structured(Tensor dense) -> (Tensor, Tensor)
  variants: function
  dispatch:
    CUDA: _to_sparse_semi_structured

- func: to_mkldnn(Tensor self, ScalarType? dtype=None) -> Tensor
  variants: method
  dispatch:
    CPU: dense_to_mkldnn
  autogen: to_mkldnn.out

- func: mkldnn_reorder_conv2d_weight(Tensor self, SymInt[2] padding=0, SymInt[2] stride=1, SymInt[2] dilation=1, SymInt groups=1, SymInt[]? input_size=None) -> Tensor
  variants: function
  python_module: nn
  dispatch:
    MkldnnCPU: mkldnn_reorder_conv2d_weight
  autogen: mkldnn_reorder_conv2d_weight.out

- func: mkldnn_reorder_conv3d_weight(Tensor self, SymInt[3] padding=0, SymInt[3] stride=1, SymInt[3] dilation=1, SymInt groups=1, SymInt[]? input_size=None) -> Tensor
  variants: function
  python_module: nn
  dispatch:
    MkldnnCPU: mkldnn_reorder_conv3d_weight
  autogen: mkldnn_reorder_conv3d_weight.out

- func: to_mkldnn_backward(Tensor grad, Tensor input) -> Tensor

- func: quantize_per_tensor_dynamic(Tensor self, ScalarType dtype, bool reduce_range) -> Tensor
  variants: function
  dispatch:
    CPU, CUDA: quantize_per_tensor_dynamic
  autogen: quantize_per_tensor_dynamic.out

- func: quantize_per_tensor(Tensor self, float scale, int zero_point, ScalarType dtype) -> Tensor
  variants: function
  dispatch:
    CPU, CUDA: quantize_per_tensor
  autogen: quantize_per_tensor.out

- func: quantize_per_tensor.tensor_qparams(Tensor self, Tensor scale, Tensor zero_point, ScalarType dtype) -> Tensor
  variants: function
  dispatch:
    CPU, CUDA: quantize_per_tensor_tensor_qparams
  autogen: quantize_per_tensor.tensor_qparams_out

- func: quantize_per_tensor.tensors(Tensor[] tensors, Tensor scales, Tensor zero_points, ScalarType dtype) -> Tensor[]
  variants: function
  dispatch:
    CPU: quantize_per_tensor_list_cpu
  autogen: quantize_per_tensor.tensors_out

- func: quantize_per_channel(Tensor self, Tensor scales, Tensor zero_points, int axis, ScalarType dtype) -> Tensor
  variants: function
  dispatch:
    CPU, CUDA: quantize_per_channel
  autogen: quantize_per_channel.out

- func: dequantize.self(Tensor self) -> Tensor
  variants: function, method
  dispatch:
    CPU, CUDA: dequantize_cpu_or_cuda
    QuantizedCPU, QuantizedCUDA: dequantize_quantized
  autogen: dequantize.self_out

- func: dequantize.tensors(Tensor[] tensors) -> Tensor[]
  variants: function
  dispatch:
    QuantizedCPU: dequantize_tensors_quantized_cpu
  autogen: dequantize.tensors_out

- func: q_scale(Tensor self) -> float
  variants: function, method
  dispatch:
    QuantizedCPU, QuantizedCUDA: q_scale_quant

- func: q_zero_point(Tensor self) -> int
  variants: function, method
  dispatch:
    QuantizedCPU, QuantizedCUDA: q_zero_point_quant

- func: q_per_channel_scales(Tensor self) -> Tensor
  variants: function, method
  dispatch:
    QuantizedCPU, QuantizedCUDA: q_per_channel_scales
  autogen: q_per_channel_scales.out

- func: q_per_channel_zero_points(Tensor self) -> Tensor
  variants: function, method
  dispatch:
    QuantizedCPU, QuantizedCUDA: q_per_channel_zero_points
  autogen: q_per_channel_zero_points.out

- func: q_per_channel_axis(Tensor self) -> int
  variants: function, method
  dispatch:
    QuantizedCPU, QuantizedCUDA: q_per_channel_axis

- func: int_repr(Tensor self) -> Tensor
  device_check: NoCheck   # TensorIterator
  variants: function, method
  dispatch:
    QuantizedCPU: int_repr_quantized_cpu
    QuantizedCUDA: int_repr_quantized_cuda
  autogen: int_repr.out

- func: _make_per_tensor_quantized_tensor(Tensor self, float scale, int zero_point) -> Tensor
  dispatch:
    CPU: make_per_tensor_quantized_tensor_cpu
    CUDA: make_per_tensor_quantized_tensor_cuda
  autogen: _make_per_tensor_quantized_tensor.out

- func: _make_per_channel_quantized_tensor(Tensor self, Tensor scale, Tensor zero_point, int axis) -> Tensor
  dispatch:
    CPU: make_per_channel_quantized_tensor_cpu
    CUDA: make_per_channel_quantized_tensor_cuda
  autogen: _make_per_channel_quantized_tensor.out

- func: qscheme(Tensor self) -> QScheme
  variants: method
  dispatch:
    QuantizedCPU, QuantizedCUDA: qscheme_quant

- func: fake_quantize_per_tensor_affine(Tensor self, float scale, int zero_point, int quant_min, int quant_max) -> Tensor
  device_check: NoCheck   # TensorIterator
  variants: function

- func: fake_quantize_per_tensor_affine.tensor_qparams(Tensor self, Tensor scale, Tensor zero_point, int quant_min, int quant_max) -> Tensor
  device_check: NoCheck   # TensorIterator
  variants: function

- func: fake_quantize_per_tensor_affine_cachemask(Tensor self, float scale, int zero_point, int quant_min, int quant_max) -> (Tensor output, Tensor mask)
  variants: function
  dispatch:
    CPU, CUDA: fake_quantize_per_tensor_affine_cachemask
  autogen: fake_quantize_per_tensor_affine_cachemask.out

- func: _fake_quantize_per_tensor_affine_cachemask_tensor_qparams(Tensor self, Tensor scale, Tensor zero_point, Tensor fake_quant_enabled, int quant_min, int quant_max) -> (Tensor output, Tensor mask)
  variants: function
  dispatch:
    CPU, CUDA: _fake_quantize_per_tensor_affine_cachemask_tensor_qparams
  autogen: _fake_quantize_per_tensor_affine_cachemask_tensor_qparams.out

- func: fake_quantize_per_tensor_affine_cachemask_backward(Tensor grad, Tensor mask) -> Tensor
  variants: function

- func: _fake_quantize_learnable_per_tensor_affine(Tensor self, Tensor scale, Tensor zero_point, int quant_min, int quant_max, float grad_factor=1.0) -> Tensor
  variants: function
  dispatch:
    CPU, CUDA: _fake_quantize_learnable_per_tensor_affine
  autogen: _fake_quantize_learnable_per_tensor_affine.out

- func: _fake_quantize_learnable_per_tensor_affine_backward(Tensor grad, Tensor self, Tensor scale, Tensor zero_point, int quant_min, int quant_max, float grad_factor=1.0) -> (Tensor, Tensor, Tensor)
  variants: function
  dispatch:
    CPU, CUDA: _fake_quantize_learnable_per_tensor_affine_backward

- func: fake_quantize_per_channel_affine(Tensor self, Tensor scale, Tensor zero_point, int axis, int quant_min, int quant_max) -> Tensor
  device_check: NoCheck   # TensorIterator
  variants: function

- func: fake_quantize_per_channel_affine_cachemask(Tensor self, Tensor scale, Tensor zero_point, int axis, int quant_min, int quant_max) -> (Tensor output, Tensor mask)
  variants: function
  dispatch:
    CPU, CUDA: fake_quantize_per_channel_affine_cachemask
  autogen: fake_quantize_per_channel_affine_cachemask.out

- func: fake_quantize_per_channel_affine_cachemask_backward(Tensor grad, Tensor mask) -> Tensor
  variants: function

- func: _fake_quantize_learnable_per_channel_affine(Tensor self, Tensor scale, Tensor zero_point, int axis, int quant_min, int quant_max, float grad_factor=1.0) -> Tensor
  variants: function
  dispatch:
    CPU, CUDA: _fake_quantize_learnable_per_channel_affine
  autogen: _fake_quantize_learnable_per_channel_affine.out

- func: _fake_quantize_learnable_per_channel_affine_backward(Tensor grad, Tensor self, Tensor scale, Tensor zero_point, int axis, int quant_min, int quant_max, float grad_factor=1.0) -> (Tensor, Tensor, Tensor)
  variants: function
  dispatch:
    CPU, CUDA: _fake_quantize_learnable_per_channel_affine_backward

- func: fused_moving_avg_obs_fake_quant(Tensor self, Tensor observer_on, Tensor fake_quant_on, Tensor(a!) running_min, Tensor(b!) running_max, Tensor(c!) scale, Tensor(d!) zero_point, float averaging_const, int quant_min, int quant_max, int ch_axis, bool per_row_fake_quant=False, bool symmetric_quant=False) -> Tensor
  variants: function

- func: _fused_moving_avg_obs_fq_helper(Tensor self, Tensor observer_on, Tensor fake_quant_on, Tensor(a!) running_min, Tensor(b!) running_max, Tensor(c!) scale, Tensor(d!) zero_point, float averaging_const, int quant_min, int quant_max, int ch_axis, bool per_row_fake_quant=False, bool symmetric_quant=False) -> (Tensor output, Tensor mask)
  dispatch:
    CPU: fused_moving_avg_obs_fake_quant_cpu
    CUDA: fused_moving_avg_obs_fake_quant_cuda
  autogen: _fused_moving_avg_obs_fq_helper_functional, _fused_moving_avg_obs_fq_helper.out

- func: _choose_qparams_per_tensor(Tensor self, bool reduce_range=False) -> (float, int)
  variants: function

- func: _saturate_weight_to_fp16(Tensor weight) -> Tensor
  variants: function

- func: choose_qparams_optimized(Tensor input, int numel, int n_bins, float ratio, int bit_width) -> (Tensor, Tensor)
  variants: function

- func: _autocast_to_reduced_precision(Tensor(a) self, bool cuda_enabled, bool cpu_enabled, ScalarType cuda_dtype, ScalarType cpu_dtype) -> Tensor(a)
  variants: method
  device_guard: False

- func: _autocast_to_full_precision(Tensor(a) self, bool cuda_enabled, bool cpu_enabled) -> Tensor(a)
  variants: method
  device_guard: False

- func: _to_copy(Tensor self, *, ScalarType? dtype=None, Layout? layout=None, Device? device=None, bool? pin_memory=None, bool non_blocking=False, MemoryFormat? memory_format=None) -> Tensor
  device_check: NoCheck
  device_guard: False
  dispatch:
    CompositeExplicitAutograd: _to_copy
    NestedTensorCPU, NestedTensorCUDA: _to_copy_nested
  autogen: _to_copy.out
  tags: core

# to(Device) must not exist because all constructors of Device also works for
# TensorOptions. Otherwise, an ambiguity error is thrown.
# See NOTE [ TensorOptions Constructors ].
- func: to.dtype_layout(Tensor(a) self, *, ScalarType? dtype=None, Layout? layout=None, Device? device=None, bool? pin_memory=None, bool non_blocking=False, bool copy=False, MemoryFormat? memory_format=None) -> Tensor(a)
  variants: method
  device_check: NoCheck
  device_guard: False

- func: to.device(Tensor(a) self, Device device, ScalarType dtype, bool non_blocking=False, bool copy=False, MemoryFormat? memory_format=None) -> Tensor(a)
  variants: method
  device_check: NoCheck
  device_guard: False

- func: to.dtype(Tensor(a) self, ScalarType dtype, bool non_blocking=False, bool copy=False, MemoryFormat? memory_format=None) -> Tensor(a)
  variants: method
  device_check: NoCheck
  device_guard: False

- func: to.other(Tensor(a) self, Tensor other, bool non_blocking=False, bool copy=False, MemoryFormat? memory_format=None) -> Tensor(a)
  variants: method
  device_check: NoCheck
  device_guard: False

- func: meshgrid(Tensor[] tensors) -> Tensor[]

# TODO: Two weeks after this lands, combine these two overloads,
#       making `
  - `t be a method
- func: lift(Tensor self) -> Tensor
  dispatch:
    CompositeExplicitAutograd: lift
  autogen: lift.out

# lift_fresh is called with an argument that is guaranteed to be
# fresh (i.e., newly allocated).  This is ONLY called from a
# torch.tensor call; if you FX trace a lift_fresh, you are obligated
# to convert this into a lift_fresh_copy (because FX will violate the
# freshness invariant when tracing).
- func: lift_fresh(Tensor(a) self) -> Tensor(a)
  dispatch:
    CompositeExplicitAutograd: lift_fresh

# Like lift, but it clones the input.
- func: lift_fresh_copy(Tensor self) -> Tensor
  tags: view_copy
  dispatch:
    CompositeExplicitAutogradNonFunctional: lift_fresh_copy
  autogen: lift_fresh_copy.out

- func: is_set_to(Tensor self, Tensor tensor) -> bool
  variants: method
  device_check: NoCheck
  device_guard: False
  dispatch:
    CPU, CUDA, MPS: is_set_to

- func: masked_fill_.Scalar(Tensor(a!) self, Tensor mask, Scalar value) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  variants: method
  dispatch:
    CPU: masked_fill__cpu
    CUDA: masked_fill__cuda
    QuantizedCPU: masked_fill__quantized_cpu
    QuantizedCUDA: masked_fill__quantized_cuda
    MPS: masked_fill__mps
  autogen: masked_fill.Scalar_out

- func: masked_fill.Scalar(Tensor self, Tensor mask, Scalar value) -> Tensor
  device_check: NoCheck   # TensorIterator
  variants: function, method
  dispatch:
    CompositeExplicitAutograd: masked_fill
    NestedTensorCPU, NestedTensorCUDA: NestedTensor_masked_fill
  tags: pointwise

- func: masked_fill_.Tensor(Tensor(a!) self, Tensor mask, Tensor value) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  variants: method
  dispatch:
    CPU: masked_fill__cpu
    CUDA: masked_fill__cuda
    QuantizedCPU: masked_fill__quantized_cpu
    QuantizedCUDA: masked_fill__quantized_cuda
    MPS: masked_fill__mps
  autogen: masked_fill.Tensor_out

- func: masked_fill.Tensor(Tensor self, Tensor mask, Tensor value) -> Tensor
  device_check: NoCheck   # TensorIterator
  variants: function, method
  dispatch:
    CompositeExplicitAutograd: masked_fill

- func: masked_scatter_(Tensor(a!) self, Tensor mask, Tensor source) -> Tensor(a!)
  variants: method
  dispatch:
    CPU: masked_scatter__cpu
    CUDA: masked_scatter__cuda
    MPS: masked_scatter__mps
  autogen: masked_scatter.out

- func: masked_scatter(Tensor self, Tensor mask, Tensor source) -> Tensor
  variants: function, method
  dispatch:
    CompositeExplicitAutograd: masked_scatter
  tags: core

- func: masked_scatter_backward(Tensor grad_output, Tensor mask, SymInt[] sizes) -> Tensor
  dispatch:
    CompositeExplicitAutograd: masked_scatter_backward_symint

- func: _masked_softmax(Tensor self, Tensor mask, int? dim=None, int? mask_type=None) -> Tensor
  dispatch:
    CUDA: masked_softmax_cuda
    CPU: masked_softmax_cpu
  autogen: _masked_softmax.out

- func: _masked_softmax_backward(Tensor grad_output, Tensor output, Tensor mask, int? dim=None) -> Tensor
  dispatch:
    CUDA: masked_softmax_backward_cuda
    CPU: masked_softmax_backward_cpu
  autogen: _masked_softmax_backward.out

- func: view(Tensor(a) self, SymInt[] size) -> Tensor(a)
  variants: method
  device_check: NoCheck
  device_guard: False
  dispatch:
    ZeroTensor, Meta, CPU, CUDA, QuantizedCPU, QuantizedCUDA, MPS: view
    MkldnnCPU: mkldnn_view
    NestedTensorCPU, NestedTensorCUDA: view_nested
  tags: core

# Warning: If you want to change the name or overload name of this
# operator, you might also want to change the `isBlockListedSchema`
# function in `torch/csrc/jit/frontend/schema_catching.cpp`.
# The name and overload name of this operator is hardcoded in that
# function in order to workaround a bug:
# https://github.com/pytorch/pytorch/issues/47964
- func: view.dtype(Tensor(a) self, ScalarType dtype) -> Tensor(a)
  variants: method
  device_check: NoCheck
  device_guard: False
  dispatch:
    CompositeExplicitAutograd: view_dtype

- func: put_(Tensor(a!) self, Tensor index, Tensor source, bool accumulate=False) -> Tensor(a!)
  variants: method
  dispatch:
    CPU, CUDA: put_
  autogen: put.out

- func: put(Tensor self, Tensor index, Tensor source, bool accumulate=False) -> Tensor
  variants: function, method
  dispatch:
    CompositeExplicitAutograd: put

- func: index_add.out(Tensor self, int dim, Tensor index, Tensor source, *, Scalar alpha=1, Tensor(a!) out) -> Tensor(a!)
  structured: True
  variants: function
  precomputed:
  - dim -> int dim
  dispatch:
    CPU: index_add_cpu_out
    CUDA: index_add_cuda_out
    MPS: index_add_mps_out

- func: index_add_(Tensor(a!) self, int dim, Tensor index, Tensor source, *, Scalar alpha=1) -> Tensor(a!)
  structured_delegate: index_add.out
  variants: method

- func: index_add(Tensor self, int dim, Tensor index, Tensor source, *, Scalar alpha=1) -> Tensor
  structured_delegate: index_add.out
  variants: function, method

- func: index_add.dimname(Tensor self, Dimname dim, Tensor index, Tensor source, *, Scalar alpha=1) -> Tensor
  variants: function, method

- func: index_reduce.out(Tensor self, int dim, Tensor index, Tensor source, str reduce, *, bool include_self=True, Tensor(a!) out) -> Tensor(a!)
  structured: True
  variants: function
  precomputed:
  - dim -> int dim
  dispatch:
    CPU: index_reduce_cpu_out
    CUDA: index_reduce_cuda_out

- func: index_reduce_(Tensor(a!) self, int dim, Tensor index, Tensor source, str reduce, *, bool include_self=True) -> Tensor(a!)
  structured_delegate: index_reduce.out
  variants: method

- func: index_reduce(Tensor self, int dim, Tensor index, Tensor source, str reduce, *, bool include_self=True) -> Tensor
  structured_delegate: index_reduce.out
  variants: function, method

- func: index_fill_.int_Scalar(Tensor(a!) self, int dim, Tensor index, Scalar value) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  variants: method
  dispatch:
    CPU: index_fill_
    CUDA: index_fill_
    MPS: index_fill_mps_
  autogen: index_fill.int_Scalar_out

- func: index_fill.int_Scalar(Tensor self, int dim, Tensor index, Scalar value) -> Tensor
  device_check: NoCheck   # TensorIterator
  variants: function, method
  dispatch:
    CompositeExplicitAutograd: index_fill

- func: index_fill_.int_Tensor(Tensor(a!) self, int dim, Tensor index, Tensor value) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  variants: method
  dispatch:
    CPU, CUDA: index_fill_
    MPS: index_fill_mps_
  autogen: index_fill.int_Tensor_out

- func: index_fill.int_Tensor(Tensor self, int dim, Tensor index, Tensor value) -> Tensor
  device_check: NoCheck   # TensorIterator
  variants: function, method
  dispatch:
    CompositeExplicitAutograd: index_fill

- func: index_fill_.Dimname_Scalar(Tensor(a!) self, Dimname dim, Tensor index, Scalar value) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  variants: method

- func: index_fill_.Dimname_Tensor(Tensor(a!) self, Dimname dim, Tensor index, Tensor value) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  variants: method

- func: index_fill.Dimname_Scalar(Tensor self, Dimname dim, Tensor index, Scalar value) -> Tensor
  device_check: NoCheck   # TensorIterator
  variants: function, method

- func: index_fill.Dimname_Tensor(Tensor self, Dimname dim, Tensor index, Tensor value) -> Tensor
  device_check: NoCheck   # TensorIterator
  variants: function, method

- func: scatter.src(Tensor self, int dim, Tensor index, Tensor src) -> Tensor
  structured_delegate: scatter.src_out
  variants: function, method
  tags: core

- func: scatter_.src(Tensor(a!) self, int dim, Tensor index, Tensor src) -> Tensor(a!)
  structured_delegate: scatter.src_out
  variants: method

- func: scatter.src_out(Tensor self, int dim, Tensor index, Tensor src, *, Tensor(a!) out) -> Tensor(a!)
  structured: True
  variants: function
  dispatch:
    CPU, CUDA: scatter_src_out
    MPS: scatter_src_out_mps

- func: scatter.value(Tensor self, int dim, Tensor index, Scalar value) -> Tensor
  structured_delegate: scatter.value_out
  variants: function, method
  tags: core

- func: scatter_.value(Tensor(a!) self, int dim, Tensor index, Scalar value) -> Tensor(a!)
  structured_delegate: scatter.value_out
  variants: method

- func: scatter.value_out(Tensor self, int dim, Tensor index, Scalar value, *, Tensor(a!) out) -> Tensor(a!)
  structured: True
  variants: function
  dispatch:
    CPU, CUDA: scatter_value_out
    MPS: scatter_value_out_mps

- func: scatter.reduce(Tensor self, int dim, Tensor index, Tensor src, *, str reduce) -> Tensor
  structured_delegate: scatter.reduce_out
  variants: function, method

- func: scatter_.reduce(Tensor(a!) self, int dim, Tensor index, Tensor src, *, str reduce) -> Tensor(a!)
  structured_delegate: scatter.reduce_out
  variants: method

- func: scatter.reduce_out(Tensor self, int dim, Tensor index, Tensor src, *, str reduce, Tensor(a!) out) -> Tensor(a!)
  structured: True
  variants: function
  dispatch:
    CPU, CUDA: scatter_reduce_out
    MPS: scatter_reduce_out_mps

- func: scatter.value_reduce(Tensor self, int dim, Tensor index, Scalar value, *, str reduce) -> Tensor
  structured_delegate: scatter.value_reduce_out
  variants: function, method

- func: scatter_.value_reduce(Tensor(a!) self, int dim, Tensor index, Scalar value, *, str reduce) -> Tensor(a!)
  structured_delegate: scatter.value_reduce_out
  variants: method

- func: scatter.value_reduce_out(Tensor self, int dim, Tensor index, Scalar value, *, str reduce, Tensor(a!) out) -> Tensor(a!)
  structured: True
  variants: function
  dispatch:
    CPU, CUDA: scatter_value_reduce_out
    MPS: scatter_value_reduce_out_mps

- func: scatter.dimname_src(Tensor self, Dimname dim, Tensor index, Tensor src) -> Tensor
  variants: function, method

- func: scatter.dimname_value(Tensor self, Dimname dim, Tensor index, Scalar value) -> Tensor
  variants: function, method

- func: scatter_add(Tensor self, int dim, Tensor index, Tensor src) -> Tensor
  structured_delegate: scatter_add.out
  variants: function, method
  tags: core

- func: scatter_add_(Tensor(a!) self, int dim, Tensor index, Tensor src) -> Tensor(a!)
  structured_delegate: scatter_add.out
  variants: method

- func: scatter_add.out(Tensor self, int dim, Tensor index, Tensor src, *, Tensor(a!) out) -> Tensor(a!)
  structured: True
  variants: function
  dispatch:
    CPU, CUDA: scatter_add
    MPS: scatter_add_mps_out

- func: scatter_add.dimname(Tensor self, Dimname dim, Tensor index, Tensor src) -> Tensor
  variants: function, method

- func: scatter_reduce.two(Tensor self, int dim, Tensor index, Tensor src, str reduce, *, bool include_self=True) -> Tensor
  structured_delegate: scatter_reduce.two_out
  variants: function, method
  tags: core

- func: scatter_reduce_.two(Tensor(a!) self, int dim, Tensor index, Tensor src, str reduce, *, bool include_self=True) -> Tensor(a!)
  structured_delegate: scatter_reduce.two_out
  variants: method

- func: scatter_reduce.two_out(Tensor self, int dim, Tensor index, Tensor src, str reduce, *, bool include_self=True, Tensor(a!) out) -> Tensor(a!)
  structured: True
  variants: function
  dispatch:
    CPU, CUDA, MPS: scatter_reduce_two

- func: eq_.Scalar(Tensor(a!) self, Scalar other) -> Tensor(a!)
  structured_delegate: eq.Scalar_out
  device_check: NoCheck   # TensorIterator
  variants: method

- func: eq_.Tensor(Tensor(a!) self, Tensor other) -> Tensor(a!)
  structured_delegate: eq.Tensor_out
  device_check: NoCheck   # TensorIterator
  variants: method

- func: bitwise_and.Tensor_out(Tensor self, Tensor other, *, Tensor(a!) out) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  structured: True
  structured_inherits: TensorIteratorBase
  variants: function
  dispatch:
    CPU, CUDA: bitwise_and_out
    MPS: bitwise_and_out_mps
  tags: pointwise

- func: bitwise_and.Scalar_out(Tensor self, Scalar other, *, Tensor(a!) out) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  variants: function
  dispatch:
    CompositeExplicitAutograd: bitwise_and_out
  tags: pointwise

- func: bitwise_and.Scalar(Tensor self, Scalar other) -> Tensor
  device_check: NoCheck   # TensorIterator
  variants: method, function
  dispatch:
    CompositeExplicitAutograd: bitwise_and
  tags: [core, pointwise]

- func: bitwise_and.Scalar_Tensor(Scalar self, Tensor other) -> Tensor
  device_check: NoCheck   # TensorIterator
  variants: function
  dispatch:
    CompositeExplicitAutograd: bitwise_and
  autogen: bitwise_and.Scalar_Tensor_out
  tags: pointwise

- func: bitwise_and.Tensor(Tensor self, Tensor other) -> Tensor
  device_check: NoCheck   # TensorIterator
  variants: method, function
  structured_delegate: bitwise_and.Tensor_out
  tags: [core, pointwise]

- func: bitwise_and_.Scalar(Tensor(a!) self, Scalar other) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  variants: method
  dispatch:
    CompositeExplicitAutograd: bitwise_and_
  tags: pointwise

- func: bitwise_and_.Tensor(Tensor(a!) self, Tensor other) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  variants: method
  structured_delegate: bitwise_and.Tensor_out
  tags: pointwise

- func: __and__.Scalar(Tensor self, Scalar other) -> Tensor
  device_check: NoCheck   # TensorIterator
  variants: method, function

- func: __and__.Tensor(Tensor self, Tensor other) -> Tensor
  device_check: NoCheck   # TensorIterator
  variants: method, function

- func: __iand__.Scalar(Tensor(a!) self, Scalar other) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  variants: method

- func: __iand__.Tensor(Tensor(a!) self, Tensor other) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  variants: method

- func: bitwise_or.Tensor_out(Tensor self, Tensor other, *, Tensor(a!) out) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  structured: True
  structured_inherits: TensorIteratorBase
  variants: function
  dispatch:
    CPU, CUDA: bitwise_or_out
    MPS: bitwise_or_out_mps
  tags: pointwise

- func: bitwise_or.Scalar_out(Tensor self, Scalar other, *, Tensor(a!) out) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  variants: function
  dispatch:
    CompositeExplicitAutograd: bitwise_or_out
  tags: pointwise

- func: bitwise_or.Scalar(Tensor self, Scalar other) -> Tensor
  device_check: NoCheck   # TensorIterator
  variants: method, function
  dispatch:
    CompositeExplicitAutograd: bitwise_or
  tags: [core, pointwise]

- func: bitwise_or.Scalar_Tensor(Scalar self, Tensor other) -> Tensor
  device_check: NoCheck   # TensorIterator
  variants: function
  dispatch:
    CompositeExplicitAutograd: bitwise_or
  autogen: bitwise_or.Scalar_Tensor_out
  tags: pointwise

- func: bitwise_or.Tensor(Tensor self, Tensor other) -> Tensor
  device_check: NoCheck   # TensorIterator
  variants: method, function
  structured_delegate: bitwise_or.Tensor_out
  tags: [core, pointwise]

- func: bitwise_or_.Scalar(Tensor(a!) self, Scalar other) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  variants: method
  dispatch:
    CompositeExplicitAutograd: bitwise_or_
  tags: pointwise

- func: bitwise_or_.Tensor(Tensor(a!) self, Tensor other) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  variants: method
  structured_delegate: bitwise_or.Tensor_out
  tags: pointwise

- func: __or__.Scalar(Tensor self, Scalar other) -> Tensor
  device_check: NoCheck   # TensorIterator
  variants: method, function

- func: __or__.Tensor(Tensor self, Tensor other) -> Tensor
  device_check: NoCheck   # TensorIterator
  variants: method, function

- func: __ior__.Scalar(Tensor(a!) self, Scalar other) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  variants: method

- func: __ior__.Tensor(Tensor(a!) self, Tensor other) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  variants: method

- func: bitwise_xor.Tensor_out(Tensor self, Tensor other, *, Tensor(a!) out) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  structured: True
  structured_inherits: TensorIteratorBase
  variants: function
  dispatch:
    CPU, CUDA: bitwise_xor_out
    MPS: bitwise_xor_out_mps
  tags: pointwise

- func: bitwise_xor.Scalar_out(Tensor self, Scalar other, *, Tensor(a!) out) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  variants: function
  dispatch:
    CompositeExplicitAutograd: bitwise_xor_out
  tags: pointwise

- func: bitwise_xor.Scalar(Tensor self, Scalar other) -> Tensor
  device_check: NoCheck   # TensorIterator
  variants: method, function
  dispatch:
    CompositeExplicitAutograd: bitwise_xor
  tags: [core, pointwise]

- func: bitwise_xor.Scalar_Tensor(Scalar self, Tensor other) -> Tensor
  device_check: NoCheck   # TensorIterator
  variants: function
  dispatch:
    CompositeExplicitAutograd: bitwise_xor
  autogen: bitwise_xor.Scalar_Tensor_out
  tags: pointwise

- func: bitwise_xor.Tensor(Tensor self, Tensor other) -> Tensor
  device_check: NoCheck   # TensorIterator
  variants: method, function
  structured_delegate: bitwise_xor.Tensor_out
  tags: [core, pointwise]

- func: bitwise_xor_.Scalar(Tensor(a!) self, Scalar other) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  variants: method
  dispatch:
    CompositeExplicitAutograd: bitwise_xor_
  tags: pointwise

- func: bitwise_xor_.Tensor(Tensor(a!) self, Tensor other) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  variants: method
  structured_delegate: bitwise_xor.Tensor_out
  tags: pointwise

- func: __xor__.Scalar(Tensor self, Scalar other) -> Tensor
  device_check: NoCheck   # TensorIterator
  variants: method, function
  tags: pointwise

- func: __xor__.Tensor(Tensor self, Tensor other) -> Tensor
  device_check: NoCheck   # TensorIterator
  variants: method, function
  tags: pointwise

- func: __ixor__.Scalar(Tensor(a!) self, Scalar other) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  variants: method
  tags: pointwise

- func: __ixor__.Tensor(Tensor(a!) self, Tensor other) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  variants: method
  tags: pointwise

- func: __lshift__.Scalar(Tensor self, Scalar other) -> Tensor
  device_check: NoCheck   # TensorIterator
  variants: method, function
  dispatch:
    CPU, CUDA, MPS: __lshift__
  tags: pointwise

- func: __lshift__.Tensor(Tensor self, Tensor other) -> Tensor
  device_check: NoCheck   # TensorIterator
  variants: method, function
  dispatch:
    CPU, CUDA, MPS: __lshift__
  tags: pointwise

- func: __ilshift__.Scalar(Tensor(a!) self, Scalar other) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  variants: method
  dispatch:
    CPU, CUDA, MPS: __ilshift__
  autogen: __lshift__.Scalar_out
  tags: pointwise

- func: __ilshift__.Tensor(Tensor(a!) self, Tensor other) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  variants: method
  dispatch:
    CPU, CUDA, MPS: __ilshift__
  autogen: __lshift__.Tensor_out
  tags: pointwise

- func: bitwise_left_shift.Tensor(Tensor self, Tensor other) -> Tensor
  device_check: NoCheck   # TensorIterator
  variants: function, method
  structured_delegate: bitwise_left_shift.Tensor_out
  tags: pointwise

- func: bitwise_left_shift_.Tensor(Tensor(a!) self, Tensor other) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  variants: method
  structured_delegate: bitwise_left_shift.Tensor_out
  tags: pointwise

- func: bitwise_left_shift.Tensor_out(Tensor self, Tensor other, *, Tensor(a!) out) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  structured: True
  structured_inherits: TensorIteratorBase
  dispatch:
    CPU, CUDA, MPS: bitwise_left_shift_out
  tags: pointwise

- func: bitwise_left_shift.Tensor_Scalar(Tensor self, Scalar other) -> Tensor
  device_check: NoCheck   # TensorIterator
  variants: method, function
  dispatch:
    CompositeExplicitAutograd: bitwise_left_shift
  tags: pointwise

- func: bitwise_left_shift_.Tensor_Scalar(Tensor(a!) self, Scalar other) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  variants: method
  dispatch:
    CompositeExplicitAutograd: bitwise_left_shift_
  tags: pointwise

- func: bitwise_left_shift.Tensor_Scalar_out(Tensor self, Scalar other, *, Tensor(a!) out) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  variants: function
  dispatch:
    CompositeExplicitAutograd: bitwise_left_shift_out
  tags: pointwise

- func: bitwise_left_shift.Scalar_Tensor(Scalar self, Tensor other) -> Tensor
  device_check: NoCheck   # TensorIterator
  variants: function
  dispatch:
    CompositeExplicitAutograd: bitwise_left_shift
  autogen: bitwise_left_shift.Scalar_Tensor_out
  tags: pointwise

- func: __rshift__.Scalar(Tensor self, Scalar other) -> Tensor
  device_check: NoCheck   # TensorIterator
  variants: method, function
  dispatch:
    CPU, CUDA, MPS: __rshift__
  tags: pointwise

- func: __rshift__.Tensor(Tensor self, Tensor other) -> Tensor
  device_check: NoCheck   # TensorIterator
  variants: method, function
  dispatch:
    CPU, CUDA, MPS: __rshift__
  tags: pointwise

- func: __irshift__.Scalar(Tensor(a!) self, Scalar other) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  variants: method
  dispatch:
    CPU, CUDA, MPS: __irshift__
  autogen: __rshift__.Scalar_out

- func: __irshift__.Tensor(Tensor(a!) self, Tensor other) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  variants: method
  dispatch:
    CPU, CUDA, MPS: __irshift__
  autogen: __rshift__.Tensor_out

- func: bitwise_right_shift.Tensor(Tensor self, Tensor other) -> Tensor
  device_check: NoCheck   # TensorIterator
  variants: function, method
  structured_delegate: bitwise_right_shift.Tensor_out
  tags: pointwise

- func: bitwise_right_shift_.Tensor(Tensor(a!) self, Tensor other) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  variants: method
  structured_delegate: bitwise_right_shift.Tensor_out
  tags: pointwise

- func: bitwise_right_shift.Tensor_out(Tensor self, Tensor other, *, Tensor(a!) out) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  structured: True
  structured_inherits: TensorIteratorBase
  dispatch:
    CPU, CUDA, MPS: bitwise_right_shift_out
  tags: pointwise

- func: bitwise_right_shift.Tensor_Scalar(Tensor self, Scalar other) -> Tensor
  device_check: NoCheck   # TensorIterator
  variants: method, function
  dispatch:
    CompositeExplicitAutograd: bitwise_right_shift
  tags: pointwise

- func: bitwise_right_shift_.Tensor_Scalar(Tensor(a!) self, Scalar other) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  variants: method
  dispatch:
    CompositeExplicitAutograd: bitwise_right_shift_
  tags: pointwise

- func: bitwise_right_shift.Tensor_Scalar_out(Tensor self, Scalar other, *, Tensor(a!) out) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  variants: function
  dispatch:
    CompositeExplicitAutograd: bitwise_right_shift_out
  tags: pointwise

- func: bitwise_right_shift.Scalar_Tensor(Scalar self, Tensor other) -> Tensor
  device_check: NoCheck   # TensorIterator
  variants: function
  dispatch:
    CompositeExplicitAutograd: bitwise_right_shift
  autogen: bitwise_right_shift.Scalar_Tensor_out
  tags: pointwise

- func: tril_(Tensor(a!) self, int diagonal=0) -> Tensor(a!)
  structured_delegate: tril.out
  variants: method

- func: triu_(Tensor(a!) self, int diagonal=0) -> Tensor(a!)
  structured_delegate: triu.out
  variants: method

- func: digamma_(Tensor(a!) self) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  structured_delegate: digamma.out
  variants: method
  tags: pointwise

- func: lerp_.Scalar(Tensor(a!) self, Tensor end, Scalar weight) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  variants: method
  structured_delegate: lerp.Scalar_out
  tags: pointwise

- func: lerp_.Tensor(Tensor(a!) self, Tensor end, Tensor weight) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  variants: method
  structured_delegate: lerp.Tensor_out
  tags: pointwise

- func: addbmm_(Tensor(a!) self, Tensor batch1, Tensor batch2, *, Scalar beta=1, Scalar alpha=1) -> Tensor(a!)
  variants: method
  dispatch:
    CPU, CUDA, XPU: addbmm_
    MPS: addbmm_mps_

- func: addbmm.out(Tensor self, Tensor batch1, Tensor batch2, *, Scalar beta=1, Scalar alpha=1, Tensor(a!) out) -> Tensor(a!)
  dispatch:
    CPU, CUDA, XPU: addbmm_out
    MPS: addbmm_out_mps

- func: addbmm(Tensor self, Tensor batch1, Tensor batch2, *, Scalar beta=1, Scalar alpha=1) -> Tensor
  variants: method, function
  dispatch:
    CPU, CUDA, XPU: addbmm
    MPS: addbmm_mps

- func: random_.from(Tensor(a!) self, int from, int? to, *, Generator? generator=None) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  variants: method
  tags: nondeterministic_seeded
  dispatch:
    CPU, CUDA: random_
    Meta: random_meta_
    MPS: random_mps_
  autogen: random.from, random.from_out

- func: random_.to(Tensor(a!) self, int to, *, Generator? generator=None) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  tags: nondeterministic_seeded
  variants: method
  dispatch:
    CPU, CUDA: random_
    Meta: random_meta_
    MPS: random_mps_
  autogen: random.to, random.to_out

- func: random_(Tensor(a!) self, *, Generator? generator=None) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  tags: nondeterministic_seeded
  variants: method
  dispatch:
    CPU, CUDA: random_
    MPS: random_mps_
    Meta: random_meta_
  autogen: random, random.out

- func: uniform_(Tensor(a!) self, float from=0, float to=1, *, Generator? generator=None) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  tags: nondeterministic_seeded
  variants: method
  dispatch:
    CPU, CUDA: uniform_
    MPS: uniform_mps_
    Meta: uniform_meta_
  autogen: uniform, uniform.out

- func: cauchy_(Tensor(a!) self, float median=0, float sigma=1, *, Generator? generator=None) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  variants: method
  tags: nondeterministic_seeded
  dispatch:
    CPU, CUDA: cauchy_
  autogen: cauchy, cauchy.out

- func: log_normal_(Tensor(a!) self, float mean=1, float std=2, *, Generator? generator=None) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  tags: nondeterministic_seeded
  variants: method
  dispatch:
    CPU, CUDA: log_normal_
  autogen: log_normal, log_normal.out

- func: exponential_(Tensor(a!) self, float lambd=1, *, Generator? generator=None) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  tags: nondeterministic_seeded
  variants: method
  dispatch:
    CPU, CUDA: exponential_
    MPS: exponential_mps_
  autogen: exponential, exponential.out

- func: geometric_(Tensor(a!) self, float p, *, Generator? generator=None) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  tags: nondeterministic_seeded
  variants: method
  dispatch:
    CPU, CUDA: geometric_

  # wrappers for TH functions
  autogen: geometric, geometric.out

- func: diag.out(Tensor self, int diagonal=0, *, Tensor(a!) out) -> Tensor(a!)

- func: diag(Tensor self, int diagonal=0) -> Tensor
  variants: method, function

- func: cross.out(Tensor self, Tensor other, int? dim=None, *, Tensor(a!) out) -> Tensor(a!)

- func: cross(Tensor self, Tensor other, int? dim=None) -> Tensor
  variants: method, function

- func: triu.out(Tensor self, int diagonal=0, *, Tensor(a!) out) -> Tensor(a!)
  structured: True
  dispatch:
    CPU: triu_cpu
    CUDA: triu_cuda
    MPS: triu_mps_out

- func: triu(Tensor self, int diagonal=0) -> Tensor
  structured_delegate: triu.out
  variants: method, function

- func: tril.out(Tensor self, int diagonal=0, *, Tensor(a!) out) -> Tensor(a!)
  structured: True
  dispatch:
    CPU: tril_cpu
    CUDA: tril_cuda
    MPS: tril_mps_out

- func: tril(Tensor self, int diagonal=0) -> Tensor
  structured_delegate: tril.out
  variants: method, function

- func: tril_indices(int row, int col, int offset=0, *, ScalarType? dtype=long, Layout? layout=None, Device? device=None, bool? pin_memory=None) -> Tensor
  dispatch:
    CPU: tril_indices_cpu
    CUDA: tril_indices_cuda
    MPS: tril_indices_mps
  autogen: tril_indices.out

- func: triu_indices(int row, int col, int offset=0, *, ScalarType? dtype=long, Layout? layout=None, Device? device=None, bool? pin_memory=None) -> Tensor
  dispatch:
    CPU: triu_indices_cpu
    CUDA: triu_indices_cuda
    MPS: triu_indices_mps
  autogen: triu_indices.out

- func: trace(Tensor self) -> Tensor
  variants: method, function
  dispatch:
    CPU: trace_cpu
    CUDA: trace_cuda
    MPS: trace_mps
  autogen: trace.out

- func: trace_backward(Tensor grad, SymInt[] sizes) -> Tensor
  variants: function
  device_check: NoCheck
  device_guard: False
  dispatch:
    CompositeImplicitAutograd: trace_backward_symint

- func: ne.Scalar_out(Tensor self, Scalar other, *, Tensor(a!) out) -> Tensor(a!)
  structured: True
  structured_inherits: TensorIteratorBase
  device_check: NoCheck   # TensorIterator
  dispatch:
    CPU, CUDA: ne_Scalar_out
    MPS: ne_scalar_out_mps
    QuantizedCPU: ne_out_quantized_cpu
  tags: pointwise

- func: ne.Scalar(Tensor self, Scalar other) -> Tensor
  structured_delegate: ne.Scalar_out
  device_check: NoCheck   # TensorIterator
  variants: method, function
  dispatch:
    QuantizedCPU: ne_quantized_cpu
  tags: [core, pointwise]

- func: ne.Tensor_out(Tensor self, Tensor other, *, Tensor(a!) out) -> Tensor(a!)
  structured: True
  structured_inherits: TensorIteratorBase
  device_check: NoCheck   # TensorIterator
  dispatch:
    CPU, CUDA: ne_Tensor_out
    MPS: ne_tensor_out_mps
    QuantizedCPU: ne_out_quantized_cpu
  tags: pointwise

- func: ne.Tensor(Tensor self, Tensor other) -> Tensor
  structured_delegate: ne.Tensor_out
  device_check: NoCheck   # TensorIterator
  variants: method, function
  dispatch:
    QuantizedCPU: ne_quantized_cpu
  tags: [core, pointwise]

- func: ne_.Scalar(Tensor(a!) self, Scalar other) -> Tensor(a!)
  structured_delegate: ne.Scalar_out
  device_check: NoCheck   # TensorIterator
  variants: method

- func: ne_.Tensor(Tensor(a!) self, Tensor other) -> Tensor(a!)
  structured_delegate: ne.Tensor_out
  device_check: NoCheck   # TensorIterator
  variants: method

# not_equal, alias for torch.ne
- func: not_equal.Scalar_out(Tensor self, Scalar other, *, Tensor(a!) out) -> Tensor(a!)

- func: not_equal.Scalar(Tensor self, Scalar other) -> Tensor
  variants: method, function

- func: not_equal.Tensor_out(Tensor self, Tensor other, *, Tensor(a!) out) -> Tensor(a!)

- func: not_equal.Tensor(Tensor self, Tensor other) -> Tensor
  variants: method, function

- func: not_equal_.Scalar(Tensor(a!) self, Scalar other) -> Tensor(a!)
  variants: method

- func: not_equal_.Tensor(Tensor(a!) self, Tensor other) -> Tensor(a!)
  variants: method

- func: eq.Scalar_out(Tensor self, Scalar other, *, Tensor(a!) out) -> Tensor(a!)
  structured: True
  structured_inherits: TensorIteratorBase
  device_check: NoCheck   # TensorIterator
  dispatch:
    CPU, CUDA: eq_Scalar_out
    MPS: eq_scalar_out_mps
    QuantizedCPU: eq_out_quantized_cpu
  tags: pointwise

- func: eq.Scalar(Tensor self, Scalar other) -> Tensor
  structured_delegate: eq.Scalar_out
  device_check: NoCheck   # TensorIterator
  variants: method, function
  dispatch:
    QuantizedCPU: eq_quantized_cpu
    NestedTensorCPU, NestedTensorCUDA: eq_scalar_nested
  tags: [core, pointwise]

- func: eq.Tensor_out(Tensor self, Tensor other, *, Tensor(a!) out) -> Tensor(a!)
  structured: True
  structured_inherits: TensorIteratorBase
  device_check: NoCheck   # TensorIterator
  dispatch:
    CPU, CUDA: eq_Tensor_out
    MPS: eq_tensor_out_mps
    QuantizedCPU: eq_out_quantized_cpu
  tags: pointwise

- func: eq.Tensor(Tensor self, Tensor other) -> Tensor
  structured_delegate: eq.Tensor_out
  device_check: NoCheck   # TensorIterator
  variants: method, function
  dispatch:
    QuantizedCPU: eq_quantized_cpu
    NestedTensorCPU, NestedTensorCUDA: eq_tensor_nested
  tags: [core, pointwise]

- func: ge.Scalar_out(Tensor self, Scalar other, *, Tensor(a!) out) -> Tensor(a!)
  structured: True
  structured_inherits: TensorIteratorBase
  device_check: NoCheck   # TensorIterator
  dispatch:
    CPU, CUDA: ge_Scalar_out
    MPS: ge_scalar_out_mps
    QuantizedCPU: ge_out_quantized_cpu
  tags: pointwise

- func: ge.Scalar(Tensor self, Scalar other) -> Tensor
  structured_delegate: ge.Scalar_out
  device_check: NoCheck   # TensorIterator
  variants: method, function
  dispatch:
    QuantizedCPU: ge_quantized_cpu
    NestedTensorCPU, NestedTensorCUDA: ge_scalar_nested
  tags: [core, pointwise]

- func: ge.Tensor_out(Tensor self, Tensor other, *, Tensor(a!) out) -> Tensor(a!)
  structured: True
  structured_inherits: TensorIteratorBase
  device_check: NoCheck   # TensorIterator
  dispatch:
    CPU, CUDA: ge_Tensor_out
    MPS: ge_tensor_out_mps
    QuantizedCPU: ge_out_quantized_cpu
  tags: pointwise

- func: ge.Tensor(Tensor self, Tensor other) -> Tensor
  structured_delegate: ge.Tensor_out
  device_check: NoCheck   # TensorIterator
  variants: method, function
  dispatch:
    QuantizedCPU: ge_quantized_cpu
  tags: [core, pointwise]

- func: ge_.Scalar(Tensor(a!) self, Scalar other) -> Tensor(a!)
  structured_delegate: ge.Scalar_out
  device_check: NoCheck   # TensorIterator
  variants: method

- func: ge_.Tensor(Tensor(a!) self, Tensor other) -> Tensor(a!)
  structured_delegate: ge.Tensor_out
  device_check: NoCheck   # TensorIterator
  variants: method

# greater_equal, alias for torch.ge
- func: greater_equal.Scalar_out(Tensor self, Scalar other, *, Tensor(a!) out) -> Tensor(a!)

- func: greater_equal.Scalar(Tensor self, Scalar other) -> Tensor
  variants: method, function

- func: greater_equal.Tensor_out(Tensor self, Tensor other, *, Tensor(a!) out) -> Tensor(a!)

- func: greater_equal.Tensor(Tensor self, Tensor other) -> Tensor
  variants: method, function

- func: greater_equal_.Scalar(Tensor(a!) self, Scalar other) -> Tensor(a!)
  variants: method

- func: greater_equal_.Tensor(Tensor(a!) self, Tensor other) -> Tensor(a!)
  variants: method

- func: le.Scalar_out(Tensor self, Scalar other, *, Tensor(a!) out) -> Tensor(a!)
  structured: True
  structured_inherits: TensorIteratorBase
  device_check: NoCheck   # TensorIterator
  dispatch:
    CPU, CUDA: le_Scalar_out
    MPS: le_scalar_out_mps
    QuantizedCPU: le_out_quantized_cpu
  tags: pointwise

- func: le.Scalar(Tensor self, Scalar other) -> Tensor
  structured_delegate: le.Scalar_out
  device_check: NoCheck   # TensorIterator
  variants: method, function
  dispatch:
    QuantizedCPU: le_quantized_cpu
  tags: [core, pointwise]

- func: le.Tensor_out(Tensor self, Tensor other, *, Tensor(a!) out) -> Tensor(a!)
  structured: True
  structured_inherits: TensorIteratorBase
  device_check: NoCheck   # TensorIterator
  dispatch:
    CPU, CUDA: le_Tensor_out
    MPS: le_tensor_out_mps
    QuantizedCPU: le_out_quantized_cpu
  tags: pointwise

- func: le.Tensor(Tensor self, Tensor other) -> Tensor
  structured_delegate: le.Tensor_out
  device_check: NoCheck   # TensorIterator
  variants: method, function
  dispatch:
    QuantizedCPU: le_quantized_cpu
  tags: [core, pointwise]

- func: le_.Scalar(Tensor(a!) self, Scalar other) -> Tensor(a!)
  structured_delegate: le.Scalar_out
  device_check: NoCheck   # TensorIterator
  variants: method

- func: le_.Tensor(Tensor(a!) self, Tensor other) -> Tensor(a!)
  structured_delegate: le.Tensor_out
  device_check: NoCheck   # TensorIterator
  variants: method

# less_equal, alias for torch.le
- func: less_equal.Scalar_out(Tensor self, Scalar other, *, Tensor(a!) out) -> Tensor(a!)

- func: less_equal.Scalar(Tensor self, Scalar other) -> Tensor
  variants: method, function

- func: less_equal.Tensor_out(Tensor self, Tensor other, *, Tensor(a!) out) -> Tensor(a!)

- func: less_equal.Tensor(Tensor self, Tensor other) -> Tensor
  variants: method, function

- func: less_equal_.Scalar(Tensor(a!) self, Scalar other) -> Tensor(a!)
  variants: method

- func: less_equal_.Tensor(Tensor(a!) self, Tensor other) -> Tensor(a!)
  variants: method

- func: gt.Scalar_out(Tensor self, Scalar other, *, Tensor(a!) out) -> Tensor(a!)
  structured: True
  structured_inherits: TensorIteratorBase
  device_check: NoCheck   # TensorIterator
  dispatch:
    CPU, CUDA: gt_Scalar_out
    MPS: gt_scalar_out_mps
    QuantizedCPU: gt_out_quantized_cpu
  tags: pointwise

- func: gt.Scalar(Tensor self, Scalar other) -> Tensor
  structured_delegate: gt.Scalar_out
  device_check: NoCheck   # TensorIterator
  variants: method, function
  dispatch:
    QuantizedCPU: gt_quantized_cpu
    NestedTensorCPU, NestedTensorCUDA: gt_scalar_nested
  tags: [core, pointwise]

- func: gt.Tensor_out(Tensor self, Tensor other, *, Tensor(a!) out) -> Tensor(a!)
  structured: True
  structured_inherits: TensorIteratorBase
  device_check: NoCheck   # TensorIterator
  dispatch:
    CPU, CUDA: gt_Tensor_out
    MPS: gt_tensor_out_mps
    QuantizedCPU: gt_out_quantized_cpu
  tags: pointwise

- func: gt.Tensor(Tensor self, Tensor other) -> Tensor
  structured_delegate: gt.Tensor_out
  device_check: NoCheck   # TensorIterator
  variants: method, function
  dispatch:
    QuantizedCPU: gt_quantized_cpu
  tags: [core, pointwise]

- func: gt_.Scalar(Tensor(a!) self, Scalar other) -> Tensor(a!)
  structured_delegate: gt.Scalar_out
  device_check: NoCheck   # TensorIterator
  variants: method

- func: gt_.Tensor(Tensor(a!) self, Tensor other) -> Tensor(a!)
  structured_delegate: gt.Tensor_out
  device_check: NoCheck   # TensorIterator
  variants: method

#  greater, alias for torch.gt
- func: greater.Scalar_out(Tensor self, Scalar other, *, Tensor(a!) out) -> Tensor(a!)

- func: greater.Scalar(Tensor self, Scalar other) -> Tensor
  variants: method, function

- func: greater.Tensor_out(Tensor self, Tensor other, *, Tensor(a!) out) -> Tensor(a!)

- func: greater.Tensor(Tensor self, Tensor other) -> Tensor
  variants: method, function

- func: greater_.Scalar(Tensor(a!) self, Scalar other) -> Tensor(a!)
  variants: method

- func: greater_.Tensor(Tensor(a!) self, Tensor other) -> Tensor(a!)
  variants: method

- func: lt.Scalar_out(Tensor self, Scalar other, *, Tensor(a!) out) -> Tensor(a!)
  structured: True
  structured_inherits: TensorIteratorBase
  device_check: NoCheck   # TensorIterator
  dispatch:
    CPU, CUDA: lt_Scalar_out
    MPS: lt_scalar_out_mps
    QuantizedCPU: lt_out_quantized_cpu
  tags: pointwise

- func: lt.Scalar(Tensor self, Scalar other) -> Tensor
  structured_delegate: lt.Scalar_out
  device_check: NoCheck   # TensorIterator
  variants: method, function
  dispatch:
    QuantizedCPU: lt_quantized_cpu
  tags: [core, pointwise]

- func: lt.Tensor_out(Tensor self, Tensor other, *, Tensor(a!) out) -> Tensor(a!)
  structured: True
  structured_inherits: TensorIteratorBase
  device_check: NoCheck   # TensorIterator
  dispatch:
    CPU, CUDA: lt_Tensor_out
    MPS: lt_tensor_out_mps
    QuantizedCPU: lt_out_quantized_cpu
  tags: pointwise

- func: lt.Tensor(Tensor self, Tensor other) -> Tensor
  structured_delegate: lt.Tensor_out
  device_check: NoCheck   # TensorIterator
  variants: method, function
  dispatch:
    QuantizedCPU: lt_quantized_cpu
  tags: [core, pointwise]

- func: lt_.Scalar(Tensor(a!) self, Scalar other) -> Tensor(a!)
  structured_delegate: lt.Scalar_out
  device_check: NoCheck   # TensorIterator
  variants: method

- func: lt_.Tensor(Tensor(a!) self, Tensor other) -> Tensor(a!)
  structured_delegate: lt.Tensor_out
  device_check: NoCheck   # TensorIterator
  variants: method

#  less, alias for torch.lt
- func: less.Scalar_out(Tensor self, Scalar other, *, Tensor(a!) out) -> Tensor(a!)

- func: less.Scalar(Tensor self, Scalar other) -> Tensor
  variants: method, function

- func: less.Tensor_out(Tensor self, Tensor other, *, Tensor(a!) out) -> Tensor(a!)

- func: less.Tensor(Tensor self, Tensor other) -> Tensor
  variants: method, function

- func: less_.Scalar(Tensor(a!) self, Scalar other) -> Tensor(a!)
  variants: method

- func: less_.Tensor(Tensor(a!) self, Tensor other) -> Tensor(a!)
  variants: method

- func: take.out(Tensor self, Tensor index, *, Tensor(a!) out) -> Tensor(a!)
  dispatch:
    CPU, CUDA: take_out

- func: take(Tensor self, Tensor index) -> Tensor
  variants: method, function
  dispatch:
    CPU, CUDA: take

- func: take_along_dim.out(Tensor self, Tensor indices, int? dim=None, *, Tensor(a!) out) -> Tensor(a!)

- func: take_along_dim(Tensor self, Tensor indices, int? dim=None) -> Tensor
  variants: method, function

- func: index_select.out(Tensor self, int dim, Tensor index, *, Tensor(a!) out) -> Tensor(a!)
  dispatch:
    CPU, QuantizedCPU: index_select_out_cpu_
    CUDA, QuantizedCUDA: index_select_out_cuda
    MPS: index_select_out_mps

- func: index_select(Tensor self, int dim, Tensor index) -> Tensor
  variants: method, function
  dispatch:
    CPU: index_select_cpu_
    QuantizedCPU: index_select_quantized_cpu_
    CUDA: index_select_cuda
    QuantizedCUDA: index_select_quantized_cuda
    SparseCPU: index_select_sparse_cpu
    SparseCUDA: index_select_sparse_cuda
    MPS: index_select_mps
  tags: core

- func: index_select.dimname_out(Tensor self, Dimname dim, Tensor index, *, Tensor(a!) out) -> Tensor(a!)

- func: index_select.dimname(Tensor self, Dimname dim, Tensor index) -> Tensor
  variants: method, function

- func: index_select_backward(Tensor grad, SymInt[] self_sizes, int dim, Tensor index) -> Tensor
  variants: function
  device_check: NoCheck
  device_guard: False
  dispatch:
    CompositeImplicitAutograd: index_select_backward_symint

- func: masked_select.out(Tensor self, Tensor mask, *, Tensor(a!) out) -> Tensor(a!)
  dispatch:
    CPU: masked_select_out_cpu
    CUDA: masked_select_out_cuda
    MPS: masked_select_out_mps
  tags: dynamic_output_shape

- func: masked_select(Tensor self, Tensor mask) -> Tensor
  variants: method, function
  dispatch:
    CPU: masked_select_cpu
    CUDA: masked_select_cuda
    MPS: masked_select_mps
  tags: dynamic_output_shape

- func: masked_select_backward(Tensor grad, Tensor input, Tensor mask) -> Tensor
  variants: function
  device_check: NoCheck
  device_guard: False

- func: nonzero.out(Tensor self, *, Tensor(a!) out) -> Tensor(a!)
  dispatch:
    CPU: nonzero_out_cpu
    CUDA: nonzero_out_cuda
    MPS: nonzero_out_mps
  tags: dynamic_output_shape

- func: nonzero(Tensor self) -> Tensor
  variants: method, function
  dispatch:
    CPU: nonzero_cpu
    CUDA: nonzero_cuda
    MPS: nonzero_mps
  tags: [dynamic_output_shape, core]

- func: nonzero_static.out(Tensor self, *, SymInt size, int fill_value=-1, Tensor(a!) out) -> Tensor(a!)
  dispatch:
    CPU: nonzero_static_out_cpu
    CUDA: nonzero_static_out_cuda

- func: nonzero_static(Tensor self, *, SymInt size, int fill_value=-1) -> Tensor
  variants: method, function
  dispatch:
    CPU: nonzero_static_cpu
    CUDA: nonzero_static_cuda

- func: nonzero_numpy(Tensor self) -> Tensor[]
  variants: method, function

- func: argwhere(Tensor self) -> Tensor
  variants: method, function
  tags: dynamic_output_shape

- func: gather.out(Tensor self, int dim, Tensor index, *, bool sparse_grad=False, Tensor(a!) out) -> Tensor(a!)
  structured: True
  dispatch:
    CPU, CUDA: gather_out
    MPS: gather_out_mps

- func: gather(Tensor self, int dim, Tensor index, *, bool sparse_grad=False) -> Tensor
  variants: method, function
  structured_delegate: gather.out
  tags: core

- func: gather_backward(Tensor grad, Tensor self, int dim, Tensor index, bool sparse_grad) -> Tensor
  variants: function
  device_check: NoCheck
  device_guard: False

- func: gather.dimname_out(Tensor self, Dimname dim, Tensor index, *, bool sparse_grad=False, Tensor(a!) out) -> Tensor(a!)

- func: gather.dimname(Tensor self, Dimname dim, Tensor index, *, bool sparse_grad=False) -> Tensor
  variants: method, function

- func: _gather_sparse_backward(Tensor self, int dim, Tensor index, Tensor grad) -> Tensor

- func: addcmul.out(Tensor self, Tensor tensor1, Tensor tensor2, *, Scalar value=1, Tensor(a!) out) -> Tensor(a!)
  structured: True
  structured_inherits: TensorIteratorBase
  device_check: NoCheck   # TensorIterator
  dispatch:
    CPU, CUDA: addcmul_out
    MPS: addcmul_out_mps
  tags: pointwise

- func: addcmul(Tensor self, Tensor tensor1, Tensor tensor2, *, Scalar value=1) -> Tensor
  structured_delegate: addcmul.out
  device_check: NoCheck   # TensorIterator
  variants: method, function
  tags: pointwise

- func: addcmul_(Tensor(a!) self, Tensor tensor1, Tensor tensor2, *, Scalar value=1) -> Tensor(a!)
  structured_delegate: addcmul.out
  device_check: NoCheck   # TensorIterator
  variants: method
  tags: pointwise

- func: addcdiv.out(Tensor self, Tensor tensor1, Tensor tensor2, *, Scalar value=1, Tensor(a!) out) -> Tensor(a!)
  structured: True
  structured_inherits: TensorIteratorBase
  device_check: NoCheck   # TensorIterator
  dispatch:
    CPU, CUDA: addcdiv_out
    MPS: addcdiv_out_mps
  tags: pointwise

- func: addcdiv(Tensor self, Tensor tensor1, Tensor tensor2, *, Scalar value=1) -> Tensor
  structured_delegate: addcdiv.out
  device_check: NoCheck   # TensorIterator
  variants: method, function
  tags: pointwise

- func: addcdiv_(Tensor(a!) self, Tensor tensor1, Tensor tensor2, *, Scalar value=1) -> Tensor(a!)
  structured_delegate: addcdiv.out
  device_check: NoCheck   # TensorIterator
  variants: method
  tags: pointwise

- func: cross_entropy_loss(Tensor self, Tensor target, Tensor? weight=None, int reduction=Mean, SymInt ignore_index=-100, float label_smoothing=0.0) -> Tensor
  python_module: nn
  dispatch:
    CompositeImplicitAutograd: cross_entropy_loss_symint

- func: triangular_solve.X(Tensor self, Tensor A, bool upper=True, bool transpose=False, bool unitriangular=False, *, Tensor(a!) X, Tensor(b!) M) -> (Tensor(a!) solution, Tensor(b!) cloned_coefficient)
  structured: True
  dispatch:
    CPU, CUDA: triangular_solve_out
    MPS: triangular_solve_mps_out
    SparseCsrCPU: triangular_solve_out_sparse_csr_cpu
    SparseCsrCUDA: triangular_solve_out_sparse_csr_cuda

- func: triangular_solve(Tensor self, Tensor A, bool upper=True, bool transpose=False, bool unitriangular=False) -> (Tensor solution, Tensor cloned_coefficient)
  structured_delegate: triangular_solve.X
  variants: method, function

- func: _linalg_check_errors(Tensor info, str api_name, *, bool is_matrix) -> ()
  dispatch:
    CompositeExplicitAutograd: _linalg_check_errors

- func: linalg_solve_triangular.out(Tensor self, Tensor B, *, bool upper, bool left=True, bool unitriangular=False, Tensor(a!) out) -> Tensor(a!)
  python_module: linalg
  dispatch:
    CPU, CUDA: linalg_solve_triangular_out
    MPS: linalg_solve_triangular_mps_out

- func: linalg_solve_triangular(Tensor self, Tensor B, *, bool upper, bool left=True, bool unitriangular=False) -> Tensor
  python_module: linalg
  variants: function
  dispatch:
    CPU, CUDA: linalg_solve_triangular
    MPS: linalg_solve_triangular_mps

- func: linalg_vander(Tensor x, *, SymInt? N=None) -> Tensor
  python_module: linalg
  dispatch:
    CompositeImplicitAutograd: linalg_vander_symint

- func: svd.U(Tensor self, bool some=True, bool compute_uv=True, *, Tensor(a!) U, Tensor(b!) S, Tensor(c!) V) -> (Tensor(a!) U, Tensor(b!) S, Tensor(c!) V)

- func: svd(Tensor self, bool some=True, bool compute_uv=True) -> (Tensor U, Tensor S, Tensor V)
  variants: method, function

# swapaxes, alias for transpose
- func: swapaxes(Tensor(a) self, int axis0, int axis1) -> Tensor(a)
  variants: function, method
  device_check: NoCheck
  device_guard: False

- func: swapaxes_(Tensor(a!) self, int axis0, int axis1) -> Tensor(a!)
  variants: method
  device_check: NoCheck
  device_guard: False
  tags: inplace_view

# swapdims, alias for transpose
- func: swapdims(Tensor(a) self, int dim0, int dim1) -> Tensor(a)
  variants: function, method
  device_check: NoCheck
  device_guard: False

- func: swapdims_(Tensor(a!) self, int dim0, int dim1) -> Tensor(a!)
  variants: method
  device_check: NoCheck
  device_guard: False
  tags: inplace_view

- func: cholesky.out(Tensor self, bool upper=False, *, Tensor(a!) out) -> Tensor(a!)
  dispatch:
    CPU, CUDA: cholesky_out
    MPS: cholesky_mps_out

- func: cholesky(Tensor self, bool upper=False) -> Tensor
  variants: method, function
  dispatch:
    CPU, CUDA: cholesky
    MPS: cholesky_mps

- func: cholesky_solve.out(Tensor self, Tensor input2, bool upper=False, *, Tensor(a!) out) -> Tensor(a!)
  dispatch:
    CompositeExplicitAutograd: cholesky_solve_out

- func: cholesky_solve(Tensor self, Tensor input2, bool upper=False) -> Tensor
  variants: method, function
  dispatch:
    CompositeExplicitAutograd: cholesky_solve

- func: _cholesky_solve_helper(Tensor self, Tensor A, bool upper) -> Tensor
  variants: function
  dispatch:
    CPU: _cholesky_solve_helper_cpu
    CUDA: _cholesky_solve_helper_cuda
  autogen: _cholesky_solve_helper.out

- func: cholesky_inverse(Tensor self, bool upper=False) -> Tensor
  variants: method, function
  dispatch:
    CPU, CUDA: cholesky_inverse

- func: cholesky_inverse.out(Tensor self, bool upper=False, *, Tensor(a!) out) -> Tensor(a!)
  dispatch:
    CPU, CUDA: cholesky_inverse_out

- func: qr.Q(Tensor self, bool some=True, *, Tensor(a!) Q, Tensor(b!) R) -> (Tensor(a!) Q, Tensor(b!) R)

- func: qr(Tensor self, bool some=True) -> (Tensor Q, Tensor R)
  variants: method, function

- func: geqrf.a(Tensor self, *, Tensor(a!) a, Tensor(b!) tau) -> (Tensor(a!) a, Tensor(b!) tau)
  dispatch:
    CPU, CUDA: geqrf_out

- func: geqrf(Tensor self) -> (Tensor a, Tensor tau)
  variants: method, function
  dispatch:
    CPU, CUDA: geqrf

# orgqr, alias for linalg_householder_product
- func: orgqr(Tensor self, Tensor input2) -> Tensor
  variants: method, function

- func: orgqr.out(Tensor self, Tensor input2, *, Tensor(a!) out) -> Tensor(a!)

- func: ormqr.out(Tensor self, Tensor input2, Tensor input3, bool left=True, bool transpose=False, *, Tensor(a!) out) -> Tensor(a!)
  dispatch:
    CPU, CUDA: ormqr_out

- func: ormqr(Tensor self, Tensor input2, Tensor input3, bool left=True, bool transpose=False) -> Tensor
  variants: method, function
  dispatch:
    CPU, CUDA: ormqr

- func: _lu_with_info(Tensor self, bool pivot=True, bool check_errors=True) -> (Tensor LU, Tensor pivots, Tensor info)
  variants: function

- func: lu_solve.out(Tensor self, Tensor LU_data, Tensor LU_pivots, *, Tensor(a!) out) -> Tensor(a!)

- func: lu_solve(Tensor self, Tensor LU_data, Tensor LU_pivots) -> Tensor
  variants: method, function

# lu_unpack
- func: lu_unpack(Tensor LU_data, Tensor LU_pivots, bool unpack_data=True, bool unpack_pivots=True) -> (Tensor P, Tensor L, Tensor U)
  structured_delegate: lu_unpack.out
  variants: function

- func: lu_unpack.out(Tensor LU_data, Tensor LU_pivots, bool unpack_data=True, bool unpack_pivots=True, *, Tensor(a!) P, Tensor(b!) L, Tensor(c!) U) -> (Tensor(a!) P, Tensor(b!) L, Tensor(c!) U)
  variants: function
  structured: True
  dispatch:
    CPU, CUDA: lu_unpack_out
    MPS: lu_unpack_out_mps

# TODO: remove dispatch section when porting TH CUDA to ATen
- func: multinomial.out(Tensor self, int num_samples, bool replacement=False, *, Generator? generator=None, Tensor(a!) out) -> Tensor(a!)
  tags: nondeterministic_seeded
  dispatch:
    CPU, CUDA: multinomial_out
    MPS: multinomial_out_mps

- func: multinomial(Tensor self, int num_samples, bool replacement=False, *, Generator? generator=None) -> Tensor
  variants: method, function
  dispatch:
    CPU, CUDA: multinomial
    MPS: multinomial_mps
  tags: nondeterministic_seeded

- func: lgamma.out(Tensor self, *, Tensor(a!) out) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  structured: True
  structured_inherits: TensorIteratorBase
  dispatch:
    CPU, CUDA: lgamma_out
    MPS: lgamma_out_mps
  tags: pointwise

- func: lgamma_(Tensor(a!) self) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  structured_delegate: lgamma.out
  variants: method
  tags: pointwise

- func: lgamma(Tensor self) -> Tensor
  device_check: NoCheck   # TensorIterator
  structured_delegate: lgamma.out
  variants: method, function
  tags: pointwise

- func: digamma.out(Tensor self, *, Tensor(a!) out) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  structured: True
  structured_inherits: TensorIteratorBase
  dispatch:
    CPU, CUDA: digamma_out
    MPS: digamma_out_mps
  tags: pointwise

- func: digamma(Tensor self) -> Tensor
  device_check: NoCheck   # TensorIterator
  structured_delegate: digamma.out
  variants: method, function
  tags: pointwise

- func: polygamma.out(int n, Tensor self, *, Tensor(a!) out) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  structured: True
  structured_inherits: TensorIteratorBase
  dispatch:
    CPU, CUDA: polygamma_out
    MPS: polygamma_out_mps
  tags: pointwise

- func: polygamma(int n, Tensor self) -> Tensor
  device_check: NoCheck   # TensorIterator
  structured_delegate: polygamma.out
  variants: method, function
  tags: pointwise

- func: polygamma_(Tensor(a!) self, int n) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  variants: method
  dispatch:
    CompositeExplicitAutograd: polygamma_
  tags: pointwise

- func: erfinv(Tensor self) -> Tensor
  device_check: NoCheck   # TensorIterator
  structured_delegate: erfinv.out
  variants: method, function
  dispatch:
    SparseCPU, SparseCUDA: erfinv_sparse
    SparseCsrCPU, SparseCsrCUDA, SparseCsrMeta: erfinv_sparse_csr
  tags: pointwise

- func: erfinv_(Tensor(a!) self) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  structured_delegate: erfinv.out
  variants: method
  dispatch:
    SparseCPU, SparseCUDA: erfinv_sparse_
    SparseCsrCPU, SparseCsrCUDA, SparseCsrMeta: erfinv_sparse_csr_
  tags: pointwise

- func: erfinv.out(Tensor self, *, Tensor(a!) out) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  structured: True
  structured_inherits: TensorIteratorBase
  dispatch:
    CPU, CUDA, MPS: erfinv_out
    SparseCPU, SparseCUDA: erfinv_sparse_out
    SparseCsrCPU, SparseCsrCUDA, SparseCsrMeta: erfinv_sparse_csr_out
  tags: pointwise

- func: i0(Tensor self) -> Tensor
  structured_delegate: i0.out
  variants: function, method
  tags: pointwise

- func: i0_(Tensor(a!) self) -> Tensor(a!)
  structured_delegate: i0.out
  variants: function, method
  tags: pointwise

- func: i0.out(Tensor self, *, Tensor(a!) out) -> Tensor(a!)
  structured: True
  structured_inherits: TensorIteratorBase
  dispatch:
    CPU, CUDA, MPS: i0_out
  tags: pointwise

- func: sign(Tensor self) -> Tensor
  device_check: NoCheck   # TensorIterator
  structured_delegate: sign.out
  variants: function, method
  dispatch:
    SparseCPU, SparseCUDA: sign_sparse
    SparseCsrCPU, SparseCsrCUDA, SparseCsrMeta: sign_sparse_csr
  tags: [core, pointwise]

- func: sign_(Tensor(a!) self) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  structured_delegate: sign.out
  variants: method
  dispatch:
    SparseCPU, SparseCUDA: sign_sparse_
    SparseCsrCPU, SparseCsrCUDA, SparseCsrMeta: sign_sparse_csr_
  tags: pointwise

- func: sign.out(Tensor self, *, Tensor(a!) out) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  structured: True
  structured_inherits: TensorIteratorBase
  dispatch:
    CPU, CUDA: sign_out
    MPS: sign_out_mps
    SparseCPU, SparseCUDA: sign_sparse_out
    SparseCsrCPU, SparseCsrCUDA, SparseCsrMeta: sign_sparse_csr_out
  tags: pointwise

- func: signbit(Tensor self) -> Tensor
  variants: function, method
  structured_delegate: signbit.out
  dispatch:
    SparseCPU, SparseCUDA: signbit_sparse
    SparseCsrCPU, SparseCsrCUDA, SparseCsrMeta: signbit_sparse_csr
  tags: pointwise

- func: signbit.out(Tensor self, *, Tensor(a!) out) -> Tensor(a!)
  structured: True
  structured_inherits: TensorIteratorBase
  dispatch:
    CPU: signbit_out
    CUDA: signbit_out
    MPS: signbit_out_mps
    SparseCPU, SparseCUDA: signbit_sparse_out
    SparseCsrCPU, SparseCsrCUDA, SparseCsrMeta: signbit_sparse_csr_out
  tags: pointwise

- func: dist(Tensor self, Tensor other, Scalar p=2) -> Tensor
  device_check: NoCheck   # TensorIterator
  variants: method, function
  dispatch:
    CompositeExplicitAutograd: dist
  autogen: dist.out

- func: atan2.out(Tensor self, Tensor other, *, Tensor(a!) out) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  structured: True
  structured_inherits: TensorIteratorBase
  dispatch:
    CPU, CUDA: atan2_out
    MPS: atan2_out_mps
  tags: [core, pointwise]

- func: atan2_(Tensor(a!) self, Tensor other) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  structured_delegate: atan2.out
  variants: method
  tags: pointwise

- func: atan2(Tensor self, Tensor other) -> Tensor
  device_check: NoCheck   # TensorIterator
  structured_delegate: atan2.out
  variants: method, function
  tags: [core, pointwise]
# arctan2, alias of atan2

- func: arctan2(Tensor self, Tensor other) -> Tensor
  variants: method, function

- func: arctan2.out(Tensor self, Tensor other, *, Tensor(a!) out) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator

- func: arctan2_(Tensor(a!) self, Tensor other) -> Tensor(a!)
  variants: method

- func: lerp.Scalar_out(Tensor self, Tensor end, Scalar weight, *, Tensor(a!) out) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  structured: True
  structured_inherits: TensorIteratorBase
  dispatch:
    CPU, CUDA: lerp_Scalar
    MPS: lerp_Scalar_mps
  tags: pointwise

- func: lerp.Tensor_out(Tensor self, Tensor end, Tensor weight, *, Tensor(a!) out) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  structured: True
  structured_inherits: TensorIteratorBase
  dispatch:
    CPU, CUDA: lerp_Tensor
    MPS: lerp_Tensor_mps
  tags: pointwise

- func: lerp.Scalar(Tensor self, Tensor end, Scalar weight) -> Tensor
  device_check: NoCheck   # TensorIterator
  variants: method, function
  structured_delegate: lerp.Scalar_out
  tags: pointwise

- func: lerp.Tensor(Tensor self, Tensor end, Tensor weight) -> Tensor
  device_check: NoCheck   # TensorIterator
  variants: method, function
  structured_delegate: lerp.Tensor_out
  tags: pointwise

- func: histc.out(Tensor self, int bins=100, Scalar min=0, Scalar max=0, *, Tensor(a!) out) -> Tensor(a!)
  dispatch:
    CPU, MPS: histogram_histc_out
    CUDA: _histc_out_cuda

- func: histc(Tensor self, int bins=100, Scalar min=0, Scalar max=0) -> Tensor
  variants: method, function
  dispatch:
    CPU, MPS: histogram_histc
    CUDA: _histc_cuda

- func: histogram.bins_tensor_out(Tensor self, Tensor bins, *, Tensor? weight=None, bool density=False, Tensor(a!) hist, Tensor(b!) bin_edges) -> (Tensor(a!) hist, Tensor(b!) bin_edges)
  dispatch:
    CPU, MPS: histogram_out

- func: histogram.bins_tensor(Tensor self, Tensor bins, *, Tensor? weight=None, bool density=False) -> (Tensor hist, Tensor bin_edges)
  variants: method, function
  dispatch:
    CPU, MPS: histogram

- func: histogram.bin_ct_out(Tensor self, int bins=100, *, float[]? range=None, Tensor? weight=None, bool density=False, Tensor(a!) hist, Tensor(b!) bin_edges) -> (Tensor(a!) hist, Tensor(b!) bin_edges)
  dispatch:
    CPU, MPS: histogram_out

- func: histogram.bin_ct(Tensor self, int bins=100, *, float[]? range=None, Tensor? weight=None, bool density=False) -> (Tensor hist, Tensor bin_edges)
  variants: method, function
  dispatch:
    CPU, MPS: histogram

- func: _histogramdd_bin_edges(Tensor self, int[] bins, *, float[]? range=None, Tensor? weight=None, bool density=False) -> Tensor[]
  dispatch:
    CPU, MPS: histogramdd_bin_edges
  autogen: _histogramdd_bin_edges.out

- func: _histogramdd_from_bin_cts(Tensor self, int[] bins, *, float[]? range=None, Tensor? weight=None, bool density=False) -> Tensor
  dispatch:
    CPU, MPS: _histogramdd
  autogen: _histogramdd_from_bin_cts.out

- func: _histogramdd_from_bin_tensors(Tensor self, Tensor[] bins, *, Tensor? weight=None, bool density=False) -> Tensor
  dispatch:
    CPU, MPS: _histogramdd
  autogen: _histogramdd_from_bin_tensors.out

- func: histogramdd(Tensor self, int[] bins, float[]? range=None, Tensor? weight=None, bool density=False) -> (Tensor hist, Tensor[] bin_edges)

- func: histogramdd.int_bins(Tensor self, int bins, float[]? range=None, Tensor? weight=None, bool density=False) -> (Tensor hist, Tensor[] bin_edges)

- func: histogramdd.TensorList_bins(Tensor self, Tensor[] bins, float[]? range=None, Tensor? weight=None, bool density=False) -> (Tensor hist, Tensor[] bin_edges)

- func: fmod.Scalar_out(Tensor self, Scalar other, *, Tensor(a!) out) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  dispatch:
    CompositeExplicitAutograd: fmod_out
  tags: pointwise

- func: fmod.Scalar(Tensor self, Scalar other) -> Tensor
  device_check: NoCheck   # TensorIterator
  variants: method, function
  dispatch:
    CompositeExplicitAutograd: fmod
  tags: [core, pointwise]

- func: fmod_.Scalar(Tensor(a!) self, Scalar other) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  variants: method
  dispatch:
    CompositeExplicitAutograd: fmod_
  tags: pointwise

- func: fmod.Tensor_out(Tensor self, Tensor other, *, Tensor(a!) out) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  structured: True
  structured_inherits: TensorIteratorBase
  dispatch:
    CPU, CUDA: fmod_out
    MPS: fmod_mps_out
  tags: pointwise

- func: fmod.Tensor(Tensor self, Tensor other) -> Tensor
  device_check: NoCheck   # TensorIterator
  structured_delegate: fmod.Tensor_out
  variants: method, function
  tags: [core, pointwise]

- func: fmod_.Tensor(Tensor(a!) self, Tensor other) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  variants: method
  structured_delegate: fmod.Tensor_out
  tags: pointwise

- func: hypot.out(Tensor self, Tensor other, *, Tensor(a!) out) -> Tensor(a!)
  structured: True
  structured_inherits: TensorIteratorBase
  dispatch:
    CPU, CUDA: hypot_out
    MPS: hypot_out_mps
  tags: pointwise

- func: hypot(Tensor self, Tensor other) -> Tensor
  structured_delegate: hypot.out
  variants: method, function
  tags: pointwise

- func: hypot_(Tensor(a!) self, Tensor other) -> Tensor(a!)
  structured_delegate: hypot.out
  variants: method
  tags: pointwise

- func: igamma.out(Tensor self, Tensor other, *, Tensor(a!) out) -> Tensor(a!)
  structured: True
  structured_inherits: TensorIteratorBase
  dispatch:
    CPU, CUDA: igamma_out
  tags: pointwise

- func: igamma(Tensor self, Tensor other) -> Tensor
  structured_delegate: igamma.out
  variants: method, function
  tags: pointwise

- func: igamma_(Tensor(a!) self, Tensor other) -> Tensor(a!)
  structured_delegate: igamma.out
  variants: method
  tags: pointwise

- func: igammac.out(Tensor self, Tensor other, *, Tensor(a!) out) -> Tensor(a!)
  structured: True
  structured_inherits: TensorIteratorBase
  dispatch:
    CPU, CUDA: igammac_out
  tags: pointwise

- func: igammac(Tensor self, Tensor other) -> Tensor
  structured_delegate: igammac.out
  variants: method, function
  tags: pointwise

- func: igammac_(Tensor(a!) self, Tensor other) -> Tensor(a!)
  structured_delegate: igammac.out
  variants: method
  tags: pointwise

- func: nextafter.out(Tensor self, Tensor other, *, Tensor(a!) out) -> Tensor(a!)
  structured: True
  structured_inherits: TensorIteratorBase
  dispatch:
    CPU, CUDA, MPS: nextafter_out
  tags: pointwise

- func: nextafter(Tensor self, Tensor other) -> Tensor
  structured_delegate: nextafter.out
  variants: method, function
  tags: pointwise

- func: nextafter_(Tensor(a!) self, Tensor other) -> Tensor(a!)
  structured_delegate: nextafter.out
  variants: method
  tags: pointwise

- func: remainder.Scalar_out(Tensor self, Scalar other, *, Tensor(a!) out) -> Tensor(a!)
  dispatch:
    CompositeExplicitAutograd: remainder_out
  tags: pointwise

- func: remainder.Scalar(Tensor self, Scalar other) -> Tensor
  variants: method, function
  dispatch:
    CompositeExplicitAutograd: remainder
  tags: [core, pointwise]

- func: remainder_.Scalar(Tensor(a!) self, Scalar other) -> Tensor(a!)
  variants: method
  dispatch:
    CompositeExplicitAutograd: remainder_
  tags: pointwise

- func: remainder.Tensor_out(Tensor self, Tensor other, *, Tensor(a!) out) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  structured: True
  structured_inherits: TensorIteratorBase
  dispatch:
    CPU, CUDA: remainder_out
    MPS: remainder_out_mps
  tags: pointwise

- func: remainder.Tensor(Tensor self, Tensor other) -> Tensor
  device_check: NoCheck   # TensorIterator
  structured_delegate: remainder.Tensor_out
  variants: method, function
  tags: [core, pointwise]

- func: remainder_.Tensor(Tensor(a!) self, Tensor other) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  structured_delegate: remainder.Tensor_out
  variants: method
  tags: pointwise

- func: remainder.Scalar_Tensor(Scalar self, Tensor other) -> Tensor
  device_check: NoCheck   # TensorIterator
  variants: function
  dispatch:
    CPU, CUDA, MPS: remainder
  autogen: remainder.Scalar_Tensor_out
  tags: pointwise

- func: min(Tensor self) -> Tensor
  device_check: NoCheck   # TensorIterator
  variants: method, function
  dispatch:
    CPU, CUDA: min
    MPS: min_mps
    QuantizedCPU: min_quantized_cpu

- func: min.unary_out(Tensor self, *, Tensor(a!) out) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  dispatch:
    CPU, CUDA: min_unary_out
    QuantizedCPU: min_quantized_unary_out

- func: fmin(Tensor self, Tensor other) -> Tensor
  structured_delegate: fmin.out
  device_check: NoCheck   # TensorIterator
  variants: method, function
  tags: pointwise

- func: fmin.out(Tensor self, Tensor other, *, Tensor(a!) out) -> Tensor(a!)
  structured: True
  structured_inherits: TensorIteratorBase
  device_check: NoCheck   # TensorIterator
  dispatch:
    CPU, CUDA, MPS: fmin_out
  tags: pointwise

- func: max(Tensor self) -> Tensor
  device_check: NoCheck   # TensorIterator
  variants: method, function
  dispatch:
    CPU, CUDA: max
    MPS: max_mps
    QuantizedCPU: max_quantized_cpu

- func: fmax(Tensor self, Tensor other) -> Tensor
  structured_delegate: fmax.out
  device_check: NoCheck   # TensorIterator
  variants: method, function
  tags: pointwise

- func: fmax.out(Tensor self, Tensor other, *, Tensor(a!) out) -> Tensor(a!)
  structured: True
  structured_inherits: TensorIteratorBase
  device_check: NoCheck   # TensorIterator
  dispatch:
    CPU, CUDA, MPS: fmax_out
  tags: pointwise

- func: maximum(Tensor self, Tensor other) -> Tensor
  structured_delegate: maximum.out
  device_check: NoCheck   # TensorIterator
  variants: method, function
  tags: [core, pointwise]

- func: maximum.out(Tensor self, Tensor other, *, Tensor(a!) out) -> Tensor(a!)
  structured: True
  structured_inherits: TensorIteratorBase
  device_check: NoCheck   # TensorIterator
  dispatch:
    CPU, CUDA: maximum_out
    MPS: maximum_out_mps
  tags: pointwise

# binary max, alias of maximum
# NOTE: max is not an alias for maximum, since there is also unary max
- func: max.other(Tensor self, Tensor other) -> Tensor
  device_check: NoCheck   # TensorIterator
  variants: method, function
  tags: pointwise

- func: max.out(Tensor self, Tensor other, *, Tensor(a!) out) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  tags: pointwise

- func: max.unary_out(Tensor self, *, Tensor(a!) out) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  dispatch:
    CPU, CUDA: max_unary_out
    QuantizedCPU: max_quantized_unary_out

- func: minimum(Tensor self, Tensor other) -> Tensor
  structured_delegate: minimum.out
  device_check: NoCheck   # TensorIterator
  variants: method, function
  tags: [core, pointwise]

- func: minimum.out(Tensor self, Tensor other, *, Tensor(a!) out) -> Tensor(a!)
  structured: True
  structured_inherits: TensorIteratorBase
  device_check: NoCheck   # TensorIterator
  dispatch:
    CPU, CUDA: minimum_out
    MPS: minimum_out_mps
  tags: pointwise

# binary min, alias for minimum
# NOTE: min is not an alias for minimum, since there is also unary min
- func: min.out(Tensor self, Tensor other, *, Tensor(a!) out) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  tags: pointwise

- func: min.other(Tensor self, Tensor other) -> Tensor
  device_check: NoCheck   # TensorIterator
  variants: method, function
  tags: pointwise

- func: quantile(Tensor self, Tensor q, int? dim=None, bool keepdim=False, *, str interpolation=`
  - `t due to overload ambiguity with normal.Tensor_float.
- func: normal_functional(Tensor self, float mean=0, float std=1, *, Generator? generator=None) -> Tensor
  device_check: NoCheck   # TensorIterator
  tags: nondeterministic_seeded
  dispatch:
    CompositeExplicitAutograd: normal_functional

- func: normal.Tensor_float_out(Tensor mean, float std=1, *, Generator? generator=None, Tensor(a!) out) -> Tensor(a!)
  tags: nondeterministic_seeded
  dispatch:
    CPU, CUDA: normal_out
    MPS: normal_mps_out
    Meta: normal_out_meta

- func: normal.Tensor_float(Tensor mean, float std=1, *, Generator? generator=None) -> Tensor
  dispatch:
    CPU, CUDA: normal
    MPS: normal_mps
    Meta: normal_meta
  tags: nondeterministic_seeded

- func: normal.float_Tensor_out(float mean, Tensor std, *, Generator? generator=None, Tensor(a!) out) -> Tensor(a!)
  dispatch:
    CPU, CUDA: normal_out
    Meta: normal_out_meta
    MPS: normal_mps_out
  tags: nondeterministic_seeded

- func: normal.float_Tensor(float mean, Tensor std, *, Generator? generator=None) -> Tensor
  dispatch:
    CPU, CUDA: normal
    MPS: normal_mps
    Meta: normal_meta
  tags: nondeterministic_seeded

- func: normal.Tensor_Tensor_out(Tensor mean, Tensor std, *, Generator? generator=None, Tensor(a!) out) -> Tensor(a!)
  dispatch:
    CPU, CUDA: normal_out
    Meta: normal_out_meta
    MPS: normal_mps_out
  tags: nondeterministic_seeded

- func: normal.Tensor_Tensor(Tensor mean, Tensor std, *, Generator? generator=None) -> Tensor
  dispatch:
    CPU, CUDA: normal
    MPS: normal_mps
    Meta: normal_meta
  tags: nondeterministic_seeded

- func: normal.float_float(float mean, float std, SymInt[] size, *, Generator? generator=None, ScalarType? dtype=None, Layout? layout=None, Device? device=None, bool? pin_memory=None) -> Tensor
  dispatch:
    CompositeExplicitAutograd: normal
  tags: nondeterministic_seeded

- func: normal.float_float_out(float mean, float std, SymInt[] size, *, Generator? generator=None, Tensor(a!) out) -> Tensor(a!)
  dispatch:
    CompositeExplicitAutograd: normal_out
  tags: nondeterministic_seeded

- func: alias(Tensor(a) self) -> Tensor(a)
  variants: method, function
  dispatch:
    CompositeExplicitAutograd: alias
    NestedTensorCPU, NestedTensorCUDA: alias_nested
  tags: core

- func: _amp_foreach_non_finite_check_and_unscale_(Tensor(a!)[] self, Tensor(b!) found_inf, Tensor inv_scale) -> ()
  variants: function
  dispatch:
    CUDA: _amp_foreach_non_finite_check_and_unscale_cuda_
    CPU: _amp_foreach_non_finite_check_and_unscale_cpu_
  autogen: _amp_foreach_non_finite_check_and_unscale, _amp_foreach_non_finite_check_and_unscale.out

- func: _amp_update_scale_(Tensor(a!) self, Tensor(b!) growth_tracker, Tensor found_inf, float scale_growth_factor, float scale_backoff_factor, int growth_interval) -> Tensor(a!)
  variants: function
  dispatch:
    CUDA: _amp_update_scale_cuda_
    CPU: _amp_update_scale_cpu_
  autogen: _amp_update_scale, _amp_update_scale.out

    #- func: _cat(Tensor[] tensors, int dim=0) -> Tensor
    #dispatch:
    #CPU: _cat_cpu
    #CUDA: cat_cuda
    #MPS: cat_mps
    #QuantizedCPU: cat_quantized_cpu

    #- func: _cat.out(Tensor[] tensors, int dim=0, *, Tensor(a!) out) -> Tensor(a!)
    #dispatch:
    #CPU: _cat_out_cpu
  #CUDA: cat_out_cuda
  #QuantizedCPU: cat_out_quantized_cpu

- func: _foreach_add.Scalar(Tensor[] self, Scalar scalar) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_add_scalar_kernel_slow
    CUDA: foreach_tensor_add_scalar_kernel_cuda

- func: _foreach_add_.Scalar(Tensor(a!)[] self, Scalar scalar) -> ()
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_add_scalar_kernel_slow_
    CUDA: foreach_tensor_add_scalar_kernel_cuda_
  autogen: _foreach_add.Scalar_out

- func: _foreach_add.List(Tensor[] self, Tensor[] other, *, Scalar alpha=1) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_add_list_kernel_slow
    CUDA: foreach_tensor_add_list_kernel_cuda

- func: _foreach_add_.List(Tensor(a!)[] self, Tensor[] other, *, Scalar alpha=1) -> ()
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_add_list_kernel_slow_
    CUDA: foreach_tensor_add_list_kernel_cuda_
  autogen: _foreach_add.List_out

- func: _foreach_add.ScalarList(Tensor[] self, Scalar[] scalars) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_add_scalarlist_kernel_slow
    CUDA: foreach_tensor_add_scalarlist_kernel_cuda

- func: _foreach_add_.ScalarList(Tensor(a!)[] self, Scalar[] scalars) -> ()
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_add_scalarlist_kernel_slow_
    CUDA: foreach_tensor_add_scalarlist_kernel_cuda_
  autogen: _foreach_add.ScalarList_out

- func: _foreach_add.Tensor(Tensor[] self, Tensor other, *, Scalar alpha=1) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_add_tensor_kernel_slow
    CUDA: foreach_tensor_add_tensor_kernel_cuda

- func: _foreach_add_.Tensor(Tensor(a!)[] self, Tensor other, *, Scalar alpha=1) -> ()
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_add_tensor_kernel_slow_
    CUDA: foreach_tensor_add_tensor_kernel_cuda_
  autogen: _foreach_add.Tensor_out

- func: _foreach_sub.Scalar(Tensor[] self, Scalar scalar) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_sub_scalar_kernel_slow
    CUDA: foreach_tensor_sub_scalar_kernel_cuda

- func: _foreach_sub_.Scalar(Tensor(a!)[] self, Scalar scalar) -> ()
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_sub_scalar_kernel_slow_
    CUDA: foreach_tensor_sub_scalar_kernel_cuda_
  autogen: _foreach_sub.Scalar_out

- func: _foreach_sub.List(Tensor[] self, Tensor[] other, *, Scalar alpha=1) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_sub_list_kernel_slow
    CUDA: foreach_tensor_sub_list_kernel_cuda

- func: _foreach_sub_.List(Tensor(a!)[] self, Tensor[] other, *, Scalar alpha=1) -> ()
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_sub_list_kernel_slow_
    CUDA: foreach_tensor_sub_list_kernel_cuda_
  autogen: _foreach_sub.List_out

- func: _foreach_sub.ScalarList(Tensor[] self, Scalar[] scalars) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_sub_scalarlist_kernel_slow
    CUDA: foreach_tensor_sub_scalarlist_kernel_cuda

- func: _foreach_sub_.ScalarList(Tensor(a!)[] self, Scalar[] scalars) -> ()
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_sub_scalarlist_kernel_slow_
    CUDA: foreach_tensor_sub_scalarlist_kernel_cuda_
  autogen: _foreach_sub.ScalarList_out

- func: _foreach_mul.Scalar(Tensor[] self, Scalar scalar) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_mul_scalar_kernel_slow
    CUDA: foreach_tensor_mul_scalar_kernel_cuda

- func: _foreach_mul_.Scalar(Tensor(a!)[] self, Scalar scalar) -> ()
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_mul_scalar_kernel_slow_
    CUDA: foreach_tensor_mul_scalar_kernel_cuda_
  autogen: _foreach_mul.Scalar_out

- func: _foreach_mul.List(Tensor[] self, Tensor[] other) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_mul_list_kernel_slow
    CUDA: foreach_tensor_mul_list_kernel_cuda

- func: _foreach_mul_.List(Tensor(a!)[] self, Tensor[] other) -> ()
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_mul_list_kernel_slow_
    CUDA: foreach_tensor_mul_list_kernel_cuda_
  autogen: _foreach_mul.List_out

- func: _foreach_mul.ScalarList(Tensor[] self, Scalar[] scalars) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_mul_scalarlist_kernel_slow
    CUDA: foreach_tensor_mul_scalarlist_kernel_cuda

- func: _foreach_mul_.ScalarList(Tensor(a!)[] self, Scalar[] scalars) -> ()
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_mul_scalarlist_kernel_slow_
    CUDA: foreach_tensor_mul_scalarlist_kernel_cuda_
  autogen: _foreach_mul.ScalarList_out

- func: _foreach_mul.Tensor(Tensor[] self, Tensor other) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_mul_tensor_kernel_slow
    CUDA: foreach_tensor_mul_tensor_kernel_cuda

- func: _foreach_mul_.Tensor(Tensor(a!)[] self, Tensor other) -> ()
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_mul_tensor_kernel_slow_
    CUDA: foreach_tensor_mul_tensor_kernel_cuda_
  autogen: _foreach_mul.Tensor_out

- func: _foreach_div.Scalar(Tensor[] self, Scalar scalar) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_div_scalar_kernel_slow
    CUDA: foreach_tensor_div_scalar_kernel_cuda

- func: _foreach_div_.Scalar(Tensor(a!)[] self, Scalar scalar) -> ()
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_div_scalar_kernel_slow_
    CUDA: foreach_tensor_div_scalar_kernel_cuda_
  autogen: _foreach_div.Scalar_out

- func: _foreach_div.List(Tensor[] self, Tensor[] other) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_div_list_kernel_slow
    CUDA: foreach_tensor_div_list_kernel_cuda

- func: _foreach_div_.List(Tensor(a!)[] self, Tensor[] other) -> ()
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_div_list_kernel_slow_
    CUDA: foreach_tensor_div_list_kernel_cuda_
  autogen: _foreach_div.List_out

- func: _foreach_div.ScalarList(Tensor[] self, Scalar[] scalars) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_div_scalarlist_kernel_slow
    CUDA: foreach_tensor_div_scalarlist_kernel_cuda

- func: _foreach_div_.ScalarList(Tensor(a!)[] self, Scalar[] scalars) -> ()
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_div_scalarlist_kernel_slow_
    CUDA: foreach_tensor_div_scalarlist_kernel_cuda_
  autogen: _foreach_div.ScalarList_out

- func: _foreach_div.Tensor(Tensor[] self, Tensor other) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_div_tensor_kernel_slow
    CUDA: foreach_tensor_div_tensor_kernel_cuda

- func: _foreach_div_.Tensor(Tensor(a!)[] self, Tensor other) -> ()
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_div_tensor_kernel_slow_
    CUDA: foreach_tensor_div_tensor_kernel_cuda_
  autogen: _foreach_div.Tensor_out

- func: _foreach_clamp_max.Scalar(Tensor[] self, Scalar scalar) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_clamp_max_scalar_kernel_slow
    CUDA: foreach_tensor_clamp_max_scalar_kernel_cuda

- func: _foreach_clamp_max_.Scalar(Tensor(a!)[] self, Scalar scalar) -> ()
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_clamp_max_scalar_kernel_slow_
    CUDA: foreach_tensor_clamp_max_scalar_kernel_cuda_
  autogen: _foreach_clamp_max.Scalar_out

- func: _foreach_clamp_max.List(Tensor[] self, Tensor[] other) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_clamp_max_list_kernel_slow
    CUDA: foreach_tensor_clamp_max_list_kernel_cuda

- func: _foreach_clamp_max_.List(Tensor(a!)[] self, Tensor[] other) -> ()
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_clamp_max_list_kernel_slow_
    CUDA: foreach_tensor_clamp_max_list_kernel_cuda_
  autogen: _foreach_clamp_max.List_out

- func: _foreach_clamp_max.ScalarList(Tensor[] self, Scalar[] scalars) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_clamp_max_scalarlist_kernel_slow
    CUDA: foreach_tensor_clamp_max_scalarlist_kernel_cuda

- func: _foreach_clamp_max_.ScalarList(Tensor(a!)[] self, Scalar[] scalars) -> ()
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_clamp_max_scalarlist_kernel_slow_
    CUDA: foreach_tensor_clamp_max_scalarlist_kernel_cuda_
  autogen: _foreach_clamp_max.ScalarList_out

- func: _foreach_clamp_min.Scalar(Tensor[] self, Scalar scalar) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_clamp_min_scalar_kernel_slow
    CUDA: foreach_tensor_clamp_min_scalar_kernel_cuda

- func: _foreach_clamp_min_.Scalar(Tensor(a!)[] self, Scalar scalar) -> ()
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_clamp_min_scalar_kernel_slow_
    CUDA: foreach_tensor_clamp_min_scalar_kernel_cuda_
  autogen: _foreach_clamp_min.Scalar_out

- func: _foreach_clamp_min.List(Tensor[] self, Tensor[] other) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_clamp_min_list_kernel_slow
    CUDA: foreach_tensor_clamp_min_list_kernel_cuda

- func: _foreach_clamp_min_.List(Tensor(a!)[] self, Tensor[] other) -> ()
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_clamp_min_list_kernel_slow_
    CUDA: foreach_tensor_clamp_min_list_kernel_cuda_
  autogen: _foreach_clamp_min.List_out

- func: _foreach_clamp_min.ScalarList(Tensor[] self, Scalar[] scalars) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_clamp_min_scalarlist_kernel_slow
    CUDA: foreach_tensor_clamp_min_scalarlist_kernel_cuda

- func: _foreach_clamp_min_.ScalarList(Tensor(a!)[] self, Scalar[] scalars) -> ()
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_clamp_min_scalarlist_kernel_slow_
    CUDA: foreach_tensor_clamp_min_scalarlist_kernel_cuda_
  autogen: _foreach_clamp_min.ScalarList_out

# foreach_minimum/maximum dispatches to clamp_max/min
- func: _foreach_maximum.Scalar(Tensor[] self, Scalar scalar) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_clamp_min_scalar_kernel_slow
    CUDA: foreach_tensor_clamp_min_scalar_kernel_cuda

- func: _foreach_maximum_.Scalar(Tensor(a!)[] self, Scalar scalar) -> ()
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_clamp_min_scalar_kernel_slow_
    CUDA: foreach_tensor_clamp_min_scalar_kernel_cuda_
  autogen: _foreach_maximum.Scalar_out

# foreach_minimum/maximum dispatches to clamp_max/min
- func: _foreach_maximum.List(Tensor[] self, Tensor[] other) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_clamp_min_list_kernel_slow
    CUDA: foreach_tensor_clamp_min_list_kernel_cuda

- func: _foreach_maximum_.List(Tensor(a!)[] self, Tensor[] other) -> ()
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_clamp_min_list_kernel_slow_
    CUDA: foreach_tensor_clamp_min_list_kernel_cuda_
  autogen: _foreach_maximum.List_out

# foreach_minimum/maximum dispatches to clamp_max/min
- func: _foreach_maximum.ScalarList(Tensor[] self, Scalar[] scalars) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_clamp_min_scalarlist_kernel_slow
    CUDA: foreach_tensor_clamp_min_scalarlist_kernel_cuda

- func: _foreach_maximum_.ScalarList(Tensor(a!)[] self, Scalar[] scalars) -> ()
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_clamp_min_scalarlist_kernel_slow_
    CUDA: foreach_tensor_clamp_min_scalarlist_kernel_cuda_
  autogen: _foreach_maximum.ScalarList_out

- func: _foreach_minimum.Scalar(Tensor[] self, Scalar scalar) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_clamp_max_scalar_kernel_slow
    CUDA: foreach_tensor_clamp_max_scalar_kernel_cuda

- func: _foreach_minimum_.Scalar(Tensor(a!)[] self, Scalar scalar) -> ()
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_clamp_max_scalar_kernel_slow_
    CUDA: foreach_tensor_clamp_max_scalar_kernel_cuda_
  autogen: _foreach_minimum.Scalar_out

- func: _foreach_minimum.List(Tensor[] self, Tensor[] other) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_clamp_max_list_kernel_slow
    CUDA: foreach_tensor_clamp_max_list_kernel_cuda

- func: _foreach_minimum_.List(Tensor(a!)[] self, Tensor[] other) -> ()
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_clamp_max_list_kernel_slow_
    CUDA: foreach_tensor_clamp_max_list_kernel_cuda_
  autogen: _foreach_minimum.List_out

- func: _foreach_minimum.ScalarList(Tensor[] self, Scalar[] scalars) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_clamp_max_scalarlist_kernel_slow
    CUDA: foreach_tensor_clamp_max_scalarlist_kernel_cuda

- func: _foreach_minimum_.ScalarList(Tensor(a!)[] self, Scalar[] scalars) -> ()
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_clamp_max_scalarlist_kernel_slow_
    CUDA: foreach_tensor_clamp_max_scalarlist_kernel_cuda_
  autogen: _foreach_minimum.ScalarList_out

- func: _foreach_addcdiv.Scalar(Tensor[] self, Tensor[] tensor1, Tensor[] tensor2, Scalar value=1) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_addcdiv_scalar_slow
    CUDA: foreach_tensor_addcdiv_scalar_cuda

- func: _foreach_addcdiv.ScalarList(Tensor[] self, Tensor[] tensor1, Tensor[] tensor2, Scalar[] scalars) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_addcdiv_scalarlist_slow
    CUDA: foreach_tensor_addcdiv_scalarlist_cuda

- func: _foreach_addcdiv.Tensor(Tensor[] self, Tensor[] tensor1, Tensor[] tensor2, Tensor scalars) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_addcdiv_tensor_slow
    CUDA: foreach_tensor_addcdiv_tensor_cuda

- func: _foreach_addcdiv_.Scalar(Tensor(a!)[] self, Tensor[] tensor1, Tensor[] tensor2, Scalar value=1) -> ()
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_addcdiv_scalar_slow_
    CUDA: foreach_tensor_addcdiv_scalar_cuda_
  autogen: _foreach_addcdiv.Scalar_out

- func: _foreach_addcdiv_.ScalarList(Tensor(a!)[] self, Tensor[] tensor1, Tensor[] tensor2, Scalar[] scalars) -> ()
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_addcdiv_scalarlist_slow_
    CUDA: foreach_tensor_addcdiv_scalarlist_cuda_
  autogen: _foreach_addcdiv.ScalarList_out

- func: _foreach_addcdiv_.Tensor(Tensor(a!)[] self, Tensor[] tensor1, Tensor[] tensor2, Tensor scalars) -> ()
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_addcdiv_tensor_slow_
    CUDA: foreach_tensor_addcdiv_tensor_cuda_
  autogen: _foreach_addcdiv.Tensor_out

- func: _foreach_addcmul.Scalar(Tensor[] self, Tensor[] tensor1, Tensor[] tensor2, Scalar value=1) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_addcmul_scalar_slow
    CUDA: foreach_tensor_addcmul_scalar_cuda

- func: _foreach_addcmul.ScalarList(Tensor[] self, Tensor[] tensor1, Tensor[] tensor2, Scalar[] scalars) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_addcmul_scalarlist_slow
    CUDA: foreach_tensor_addcmul_scalarlist_cuda

- func: _foreach_addcmul.Tensor(Tensor[] self, Tensor[] tensor1, Tensor[] tensor2, Tensor scalars) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_addcmul_tensor_slow
    CUDA: foreach_tensor_addcmul_tensor_cuda

- func: _foreach_addcmul_.Scalar(Tensor(a!)[] self, Tensor[] tensor1, Tensor[] tensor2, Scalar value=1) -> ()
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_addcmul_scalar_slow_
    CUDA: foreach_tensor_addcmul_scalar_cuda_
  autogen: _foreach_addcmul.Scalar_out

- func: _foreach_addcmul_.ScalarList(Tensor(a!)[] self, Tensor[] tensor1, Tensor[] tensor2, Scalar[] scalars) -> ()
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_addcmul_scalarlist_slow_
    CUDA: foreach_tensor_addcmul_scalarlist_cuda_
  autogen: _foreach_addcmul.ScalarList_out

- func: _foreach_addcmul_.Tensor(Tensor(a!)[] self, Tensor[] tensor1, Tensor[] tensor2, Tensor scalars) -> ()
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_addcmul_tensor_slow_
    CUDA: foreach_tensor_addcmul_tensor_cuda_
  autogen: _foreach_addcmul.Tensor_out

- func: _foreach_abs(Tensor[] self) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_abs_slow
    CUDA: foreach_tensor_abs_cuda

- func: _foreach_abs_(Tensor(a!)[] self) -> ()
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_abs_slow_
    CUDA: foreach_tensor_abs_cuda_
  autogen: _foreach_abs.out

- func: _foreach_acos(Tensor[] self) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_acos_slow
    CUDA: foreach_tensor_acos_cuda

- func: _foreach_acos_(Tensor(a!)[] self) -> ()
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_acos_slow_
    CUDA: foreach_tensor_acos_cuda_
  autogen: _foreach_acos.out

- func: _foreach_asin(Tensor[] self) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_asin_slow
    CUDA: foreach_tensor_asin_cuda

- func: _foreach_asin_(Tensor(a!)[] self) -> ()
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_asin_slow_
    CUDA: foreach_tensor_asin_cuda_
  autogen: _foreach_asin.out

- func: _foreach_atan(Tensor[] self) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_atan_slow
    CUDA: foreach_tensor_atan_cuda

- func: _foreach_atan_(Tensor(a!)[] self) -> ()
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_atan_slow_
    CUDA: foreach_tensor_atan_cuda_
  autogen: _foreach_atan.out

- func: _foreach_ceil(Tensor[] self) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_ceil_slow
    CUDA: foreach_tensor_ceil_cuda

- func: _foreach_ceil_(Tensor(a!)[] self) -> ()
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_ceil_slow_
    CUDA: foreach_tensor_ceil_cuda_
  autogen: _foreach_ceil.out

- func: _foreach_cos(Tensor[] self) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_cos_slow
    CUDA: foreach_tensor_cos_cuda

- func: _foreach_cos_(Tensor(a!)[] self) -> ()
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_cos_slow_
    CUDA: foreach_tensor_cos_cuda_
  autogen: _foreach_cos.out

- func: _foreach_cosh(Tensor[] self) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_cosh_slow
    CUDA: foreach_tensor_cosh_cuda

- func: _foreach_cosh_(Tensor(a!)[] self) -> ()
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_cosh_slow_
    CUDA: foreach_tensor_cosh_cuda_
  autogen: _foreach_cosh.out

- func: _foreach_erf(Tensor[] self) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_erf_slow
    CUDA: foreach_tensor_erf_cuda

- func: _foreach_erf_(Tensor(a!)[] self) -> ()
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_erf_slow_
    CUDA: foreach_tensor_erf_cuda_
  autogen: _foreach_erf.out

- func: _foreach_erfc(Tensor[] self) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_erfc_slow
    CUDA: foreach_tensor_erfc_cuda

- func: _foreach_erfc_(Tensor(a!)[] self) -> ()
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_erfc_slow_
    CUDA: foreach_tensor_erfc_cuda_
  autogen: _foreach_erfc.out

- func: _foreach_exp(Tensor[] self) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_exp_slow
    CUDA: foreach_tensor_exp_cuda

- func: _foreach_exp_(Tensor(a!)[] self) -> ()
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_exp_slow_
    CUDA: foreach_tensor_exp_cuda_
  autogen: _foreach_exp.out

- func: _foreach_expm1(Tensor[] self) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_expm1_slow
    CUDA: foreach_tensor_expm1_cuda

- func: _foreach_expm1_(Tensor(a!)[] self) -> ()
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_expm1_slow_
    CUDA: foreach_tensor_expm1_cuda_
  autogen: _foreach_expm1.out

- func: _foreach_floor(Tensor[] self) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_floor_slow
    CUDA: foreach_tensor_floor_cuda

- func: _foreach_floor_(Tensor(a!)[] self) -> ()
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_floor_slow_
    CUDA: foreach_tensor_floor_cuda_
  autogen: _foreach_floor.out

- func: _foreach_frac(Tensor[] self) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_frac_slow
    CUDA: foreach_tensor_frac_cuda

- func: _foreach_frac_(Tensor(a!)[] self) -> ()
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_frac_slow_
    CUDA: foreach_tensor_frac_cuda_
  autogen: _foreach_frac.out

- func: _foreach_lerp.List(Tensor[] self, Tensor[] tensors1, Tensor[] weights) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensors are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_ternary_lerp_slow
    CUDA: foreach_tensor_lerp_ternary_cuda
  autogen: _foreach_lerp.List_out

- func: _foreach_lerp_.List(Tensor(a!)[] self, Tensor[] tensors1, Tensor[] weights) -> ()
  device_check: NoCheck   # foreach kernels fall back to slow path when tensors are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_ternary_lerp_slow_
    CUDA: foreach_tensor_lerp_ternary_cuda_
  autogen: _foreach_lerp.List_out

- func: _foreach_lerp.Scalar(Tensor[] self, Tensor[] tensors1, Scalar weight) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensors are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_lerp_list_kernel_slow
    CUDA: foreach_tensor_lerp_list_cuda
  autogen: _foreach_lerp.Scalar_out

- func: _foreach_lerp_.Scalar(Tensor(a!)[] self, Tensor[] tensors1, Scalar weight) -> ()
  device_check: NoCheck   # foreach kernels fall back to slow path when tensors are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_lerp_list_kernel_slow_
    CUDA: foreach_tensor_lerp_list_cuda_
  autogen: _foreach_lerp.Scalar_out

- func: _foreach_lerp.ScalarList(Tensor[] self, Tensor[] tensors1, Scalar[] weight) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensors are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_lerp_scalarlist_kernel_slow
    CUDA: foreach_tensor_lerp_scalarlist_cuda
  autogen: _foreach_lerp.ScalarList_out

- func: _foreach_lerp_.ScalarList(Tensor(a!)[] self, Tensor[] tensors1, Scalar[] weight) -> ()
  device_check: NoCheck   # foreach kernels fall back to slow path when tensors are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_lerp_scalarlist_kernel_slow_
    CUDA: foreach_tensor_lerp_scalarlist_cuda_
  autogen: _foreach_lerp.ScalarList_out

- func: _foreach_lgamma(Tensor[] self) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_lgamma_slow
    CUDA: foreach_tensor_lgamma_cuda

- func: _foreach_lgamma_(Tensor(a!)[] self) -> ()
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_lgamma_slow_
    CUDA: foreach_tensor_lgamma_cuda_
  autogen: _foreach_lgamma.out

- func: _foreach_log(Tensor[] self) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_log_slow
    CUDA: foreach_tensor_log_cuda

- func: _foreach_log_(Tensor(a!)[] self) -> ()
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_log_slow_
    CUDA: foreach_tensor_log_cuda_
  autogen: _foreach_log.out

- func: _foreach_log10(Tensor[] self) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_log10_slow
    CUDA: foreach_tensor_log10_cuda

- func: _foreach_log10_(Tensor(a!)[] self) -> ()
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_log10_slow_
    CUDA: foreach_tensor_log10_cuda_
  autogen: _foreach_log10.out

- func: _foreach_log1p(Tensor[] self) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_log1p_slow
    CUDA: foreach_tensor_log1p_cuda

- func: _foreach_log1p_(Tensor(a!)[] self) -> ()
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_log1p_slow_
    CUDA: foreach_tensor_log1p_cuda_
  autogen: _foreach_log1p.out

- func: _foreach_log2(Tensor[] self) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_log2_slow
    CUDA: foreach_tensor_log2_cuda

- func: _foreach_log2_(Tensor(a!)[] self) -> ()
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_log2_slow_
    CUDA: foreach_tensor_log2_cuda_
  autogen: _foreach_log2.out

- func: _foreach_max(Tensor[] self) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_max_slow
    CUDA: foreach_tensor_max_cuda
  autogen: _foreach_max.out

- func: _foreach_neg(Tensor[] self) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_neg_slow
    CUDA: foreach_tensor_neg_cuda

- func: _foreach_neg_(Tensor(a!)[] self) -> ()
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_neg_slow_
    CUDA: foreach_tensor_neg_cuda_
  autogen: _foreach_neg.out

- func: _foreach_norm.Scalar(Tensor[] self, Scalar ord=2, ScalarType? dtype=None) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_norm_slow
    CUDA: foreach_tensor_norm_cuda
  autogen: _foreach_norm.Scalar_out

- func: _foreach_pow.List(Tensor[] self, Tensor[] exponent) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_pow_list_kernel_slow
    CUDA: foreach_tensor_pow_list_kernel_cuda

- func: _foreach_pow.Scalar(Tensor[] self, Scalar exponent) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_pow_scalar_kernel_slow
    CUDA: foreach_tensor_pow_scalar_kernel_cuda

- func: _foreach_pow.ScalarList(Tensor[] self, Scalar[] exponent) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_pow_scalarlist_kernel_slow
    CUDA: foreach_tensor_pow_scalarlist_kernel_cuda

- func: _foreach_pow.ScalarAndTensor(Scalar self, Tensor[] exponent) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_scalar_pow_list_kernel_slow
    CUDA: foreach_scalar_pow_list_kernel_cuda

- func: _foreach_pow_.List(Tensor(a!)[] self, Tensor[] exponent) -> ()
  device_check: NoCheck
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_pow_list_kernel_slow_
    CUDA: foreach_tensor_pow_list_kernel_cuda_
  autogen: _foreach_pow.List_out

- func: _foreach_pow_.Scalar(Tensor(a!)[] self, Scalar exponent) -> ()
  device_check: NoCheck
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_pow_scalar_kernel_slow_
    CUDA: foreach_tensor_pow_scalar_kernel_cuda_
  autogen: _foreach_pow.Scalar_out

- func: _foreach_pow_.ScalarList(Tensor(a!)[] self, Scalar[] exponent) -> ()
  device_check: NoCheck
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_pow_scalarlist_kernel_slow_
    CUDA: foreach_tensor_pow_scalarlist_kernel_cuda_
  autogen: _foreach_pow.ScalarList_out

- func: _foreach_reciprocal(Tensor[] self) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_reciprocal_slow
    CUDA: foreach_tensor_reciprocal_cuda

- func: _foreach_reciprocal_(Tensor(a!)[] self) -> ()
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_reciprocal_slow_
    CUDA: foreach_tensor_reciprocal_cuda_
  autogen: _foreach_reciprocal.out

- func: _foreach_round(Tensor[] self) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_round_slow
    CUDA: foreach_tensor_round_cuda

- func: _foreach_round_(Tensor(a!)[] self) -> ()
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_round_slow_
    CUDA: foreach_tensor_round_cuda_
  autogen: _foreach_round.out

- func: _foreach_rsqrt(Tensor[] self) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_rsqrt_slow
    CUDA: foreach_tensor_rsqrt_cuda

- func: _foreach_rsqrt_(Tensor(a!)[] self) -> ()
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_rsqrt_slow_
    CUDA: foreach_tensor_rsqrt_cuda_
  autogen: _foreach_rsqrt.out

- func: _foreach_sigmoid(Tensor[] self) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_sigmoid_slow
    CUDA: foreach_tensor_sigmoid_cuda

- func: _foreach_sigmoid_(Tensor(a!)[] self) -> ()
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_sigmoid_slow_
    CUDA: foreach_tensor_sigmoid_cuda_
  autogen: _foreach_sigmoid.out

- func: _foreach_sign(Tensor[] self) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_sign_slow
    CUDA: foreach_tensor_sign_cuda

- func: _foreach_sign_(Tensor(a!)[] self) -> ()
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_sign_slow_
    CUDA: foreach_tensor_sign_cuda_
  autogen: _foreach_sign.out

- func: _foreach_sin(Tensor[] self) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_sin_slow
    CUDA: foreach_tensor_sin_cuda

- func: _foreach_sin_(Tensor(a!)[] self) -> ()
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_sin_slow_
    CUDA: foreach_tensor_sin_cuda_
  autogen: _foreach_sin.out

- func: _foreach_sinh(Tensor[] self) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_sinh_slow
    CUDA: foreach_tensor_sinh_cuda

- func: _foreach_sinh_(Tensor(a!)[] self) -> ()
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_sinh_slow_
    CUDA: foreach_tensor_sinh_cuda_
  autogen: _foreach_sinh.out

- func: _foreach_sqrt(Tensor[] self) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_sqrt_slow
    CUDA: foreach_tensor_sqrt_cuda

- func: _foreach_sqrt_(Tensor(a!)[] self) -> ()
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_sqrt_slow_
    CUDA: foreach_tensor_sqrt_cuda_
  autogen: _foreach_sqrt.out

- func: _foreach_tan(Tensor[] self) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_tan_slow
    CUDA: foreach_tensor_tan_cuda

- func: _foreach_tan_(Tensor(a!)[] self) -> ()
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_tan_slow_
    CUDA: foreach_tensor_tan_cuda_
  autogen: _foreach_tan.out

- func: _foreach_tanh(Tensor[] self) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_tanh_slow
    CUDA: foreach_tensor_tanh_cuda

- func: _foreach_tanh_(Tensor(a!)[] self) -> ()
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_tanh_slow_
    CUDA: foreach_tensor_tanh_cuda_
  autogen: _foreach_tanh.out

- func: _foreach_trunc(Tensor[] self) -> Tensor[]
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_trunc_slow
    CUDA: foreach_tensor_trunc_cuda

- func: _foreach_trunc_(Tensor(a!)[] self) -> ()
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_trunc_slow_
    CUDA: foreach_tensor_trunc_cuda_
  autogen: _foreach_trunc.out

- func: _foreach_zero_(Tensor(a!)[] self) -> ()
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_zero_slow_
    CUDA: foreach_tensor_zero_cuda_
  autogen: _foreach_zero, _foreach_zero.out

- func: _foreach_copy_(Tensor(a!)[] self, Tensor[] src, bool non_blocking=False) -> ()
  device_check: NoCheck   # foreach kernels fall back to slow path when tensor are on different devices
  variants: function
  dispatch:
    CompositeExplicitAutograd: foreach_tensor_copy_list_kernel_slow_
    CUDA: foreach_tensor_copy_list_kernel_cuda_
  autogen: _foreach_copy.out

- func: _foreach_copy(Tensor[] self, Tensor[] src, bool non_blocking=False) -> Tensor[] self_out
  device_check: NoCheck
  variants: function
  dispatch:
    CompositeExplicitAutograd: _foreach_copy

- func: bucketize.Tensor(Tensor self, Tensor boundaries, *, bool out_int32=False, bool right=False) -> Tensor
  dispatch:
    CPU: bucketize_cpu
    CUDA: bucketize_cuda
    MPS: bucketize_mps

- func: bucketize.Tensor_out(Tensor self, Tensor boundaries, *, bool out_int32=False, bool right=False, Tensor(a!) out) -> Tensor(a!)
  dispatch:
    CPU: bucketize_out_cpu
    CUDA: bucketize_out_cuda
    MPS: bucketize_out_mps

- func: bucketize.Scalar(Scalar self, Tensor boundaries, *, bool out_int32=False, bool right=False) -> Tensor
  dispatch:
    CPU: bucketize_cpu
    CUDA: bucketize_cuda
    MPS: bucketize_mps
  autogen: bucketize.Scalar_out

- func: searchsorted.Tensor(Tensor sorted_sequence, Tensor self, *, bool out_int32=False, bool right=False, str? side=None, Tensor? sorter=None) -> Tensor
  dispatch:
    CPU: searchsorted_cpu
    CUDA: searchsorted_cuda
    MPS: searchsorted_mps

- func: searchsorted.Tensor_out(Tensor sorted_sequence, Tensor self, *, bool out_int32=False, bool right=False, str? side=None, Tensor? sorter=None, Tensor(a!) out) -> Tensor(a!)
  dispatch:
    CPU: searchsorted_out_cpu
    CUDA: searchsorted_out_cuda
    MPS: searchsorted_out_mps

- func: searchsorted.Scalar(Tensor sorted_sequence, Scalar self, *, bool out_int32=False, bool right=False, str? side=None, Tensor? sorter=None) -> Tensor
  dispatch:
    CPU: searchsorted_cpu
    CUDA: searchsorted_cuda
    MPS: searchsorted_mps

- func: searchsorted.Scalar_out(Tensor sorted_sequence, Scalar self, *, bool out_int32=False, bool right=False, str? side=None, Tensor? sorter=None, Tensor(a!) out) -> Tensor(a!)
  dispatch:
    CPU: searchsorted_out_cpu
    CUDA: searchsorted_out_cuda
    MPS: searchsorted_out_mps

- func: _convert_indices_from_coo_to_csr(Tensor self, int size, *, bool out_int32=False) -> Tensor
  structured_delegate: _convert_indices_from_coo_to_csr.out

- func: _convert_indices_from_coo_to_csr.out(Tensor self, int size, *, bool out_int32=False, Tensor(a!) out) -> Tensor(a!)
  structured: True
  dispatch:
    CPU: _convert_indices_from_coo_to_csr_structured_cpu
    CUDA: _convert_indices_from_coo_to_csr_structured_cuda

- func: _convert_indices_from_csr_to_coo(Tensor crow_indices, Tensor col_indices, *, bool out_int32=False, bool transpose=False) -> Tensor
  structured_delegate: _convert_indices_from_csr_to_coo.out

- func: _convert_indices_from_csr_to_coo.out(Tensor crow_indices, Tensor col_indices, *, bool out_int32=False, bool transpose=False, Tensor(a!) out) -> Tensor(a!)
  structured: True
  dispatch:
    CPU: _convert_indices_from_csr_to_coo_structured_cpu
    CUDA: _convert_indices_from_csr_to_coo_structured_cuda

## NN wrappers

- func: mse_loss.out(Tensor self, Tensor target, int reduction=Mean, *, Tensor(a!) out) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  structured: True
  structured_inherits: TensorIteratorBase
  python_module: nn
  dispatch:
    CPU, CUDA: mse_loss_out
    MPS: mse_loss_out_mps

- func: mse_loss(Tensor self, Tensor target, int reduction=Mean) -> Tensor
  device_check: NoCheck   # TensorIterator
  structured_delegate: mse_loss.out
  python_module: nn

- func: mse_loss_backward.grad_input(Tensor grad_output, Tensor self, Tensor target, int reduction, *, Tensor(a!) grad_input) -> Tensor(a!)
  python_module: nn
  dispatch:
    CPU, CUDA: mse_loss_backward_out
    MPS: mse_loss_backward_out_mps

- func: mse_loss_backward(Tensor grad_output, Tensor self, Tensor target, int reduction) -> Tensor
  python_module: nn
  dispatch:
    CPU, CUDA: mse_loss_backward
    MPS: mse_loss_backward_mps

- func: l1_loss(Tensor self, Tensor target, int reduction=Mean) -> Tensor
  python_module: nn

- func: multi_margin_loss.out(Tensor self, Tensor target, Scalar p=1, Scalar margin=1, Tensor? weight=None, int reduction=Mean, *, Tensor(a!) out) -> Tensor(a!)
  python_module: nn
  dispatch:
    CPU: multi_margin_loss_cpu_out
    CUDA: multi_margin_loss_cuda_out

- func: multi_margin_loss(Tensor self, Tensor target, Scalar p=1, Scalar margin=1, Tensor? weight=None, int reduction=Mean) -> Tensor
  python_module: nn
  dispatch:
    CPU: multi_margin_loss_cpu
    CUDA: multi_margin_loss_cuda

- func: multi_margin_loss_backward.grad_input(Tensor grad_output, Tensor self, Tensor target, Scalar p, Scalar margin, Tensor? weight=None, int reduction=Mean, *, Tensor(a!) grad_input) -> Tensor(a!)
  python_module: nn
  dispatch:
    CPU: multi_margin_loss_cpu_backward_out
    CUDA: multi_margin_loss_cuda_backward_out

- func: multi_margin_loss_backward(Tensor grad_output, Tensor self, Tensor target, Scalar p, Scalar margin, Tensor? weight=None, int reduction=Mean) -> Tensor
  python_module: nn
  dispatch:
    CPU: multi_margin_loss_cpu_backward
    CUDA: multi_margin_loss_cuda_backward

- func: multilabel_margin_loss.out(Tensor self, Tensor target, int reduction=Mean, *, Tensor(a!) out) -> Tensor(a!)
  python_module: nn

- func: multilabel_margin_loss(Tensor self, Tensor target, int reduction=Mean) -> Tensor
  python_module: nn

- func: multilabel_margin_loss_forward.output(Tensor self, Tensor target, int reduction, *, Tensor(a!) output, Tensor(b!) is_target) -> (Tensor(a!), Tensor(b!))
  python_module: nn
  dispatch:
    CPU: multilabel_margin_loss_forward_out_cpu
    CUDA: multilabel_margin_loss_forward_out_cuda

- func: multilabel_margin_loss_forward(Tensor self, Tensor target, int reduction) -> (Tensor output, Tensor is_target)
  python_module: nn
  dispatch:
    CPU: multilabel_margin_loss_forward_cpu
    CUDA: multilabel_margin_loss_forward_cuda

- func: multilabel_margin_loss_backward.grad_input(Tensor grad_output, Tensor self, Tensor target, int reduction, Tensor is_target, *, Tensor(a!) grad_input) -> Tensor(a!)
  python_module: nn
  dispatch:
    CPU: multilabel_margin_loss_backward_cpu_out
    CUDA: multilabel_margin_loss_backward_cuda_out

- func: multilabel_margin_loss_backward(Tensor grad_output, Tensor self, Tensor target, int reduction, Tensor is_target) -> Tensor
  python_module: nn
  dispatch:
    CPU: multilabel_margin_loss_backward_cpu
    CUDA: multilabel_margin_loss_backward_cuda

- func: nll_loss.out(Tensor self, Tensor target, Tensor? weight=None, int reduction=Mean, SymInt ignore_index=-100, *, Tensor(a!) out) -> Tensor(a!)
  python_module: nn

- func: nll_loss_nd(Tensor self, Tensor target, Tensor? weight=None, int reduction=Mean, SymInt ignore_index=-100) -> Tensor
  python_module: nn
  dispatch:
    CompositeImplicitAutograd: nll_loss_nd_symint

- func: nll_loss(Tensor self, Tensor target, Tensor? weight=None, int reduction=Mean, SymInt ignore_index=-100) -> Tensor
  python_module: nn
  dispatch:
    CompositeImplicitAutograd: nll_loss_symint

- func: nll_loss_forward.output(Tensor self, Tensor target, Tensor? weight, int reduction, SymInt ignore_index, *, Tensor(a!) output, Tensor(b!) total_weight) -> (Tensor(a!), Tensor(b!))
  python_module: nn
  structured: True
  dispatch:
    CPU: nll_loss_forward_out_cpu
    CUDA: nll_loss_forward_out_cuda
    MPS: nll_loss_forward_out_mps

- func: nll_loss_forward(Tensor self, Tensor target, Tensor? weight, int reduction, SymInt ignore_index) -> (Tensor output, Tensor total_weight)
  python_module: nn
  structured_delegate: nll_loss_forward.output

- func: nll_loss_backward.grad_input(Tensor grad_output, Tensor self, Tensor target, Tensor? weight, int reduction, SymInt ignore_index, Tensor total_weight, *, Tensor(a!) grad_input) -> Tensor(a!)
  python_module: nn
  structured: True
  dispatch:
    CPU: nll_loss_backward_out_cpu
    CUDA: nll_loss_backward_out_cuda
    MPS: nll_loss_backward_out_mps

- func: nll_loss_backward(Tensor grad_output, Tensor self, Tensor target, Tensor? weight, int reduction, SymInt ignore_index, Tensor total_weight) -> Tensor
  python_module: nn
  structured_delegate: nll_loss_backward.grad_input

- func: nll_loss2d.out(Tensor self, Tensor target, Tensor? weight=None, int reduction=Mean, SymInt ignore_index=-100, *, Tensor(a!) out) -> Tensor(a!)
  python_module: nn

- func: nll_loss2d(Tensor self, Tensor target, Tensor? weight=None, int reduction=Mean, SymInt ignore_index=-100) -> Tensor
  python_module: nn
  dispatch:
    CompositeImplicitAutograd: nll_loss2d_symint

- func: nll_loss2d_forward.output(Tensor self, Tensor target, Tensor? weight, int reduction, SymInt ignore_index, *, Tensor(a!) output, Tensor(b!) total_weight) -> (Tensor(a!), Tensor(b!))
  python_module: nn
  dispatch:
    CPU: nll_loss2d_forward_out_cpu
    CUDA: nll_loss2d_forward_out_cuda
    MPS: nll_loss2d_forward_out_mps

- func: nll_loss2d_forward(Tensor self, Tensor target, Tensor? weight, int reduction, SymInt ignore_index) -> (Tensor output, Tensor total_weight)
  python_module: nn
  dispatch:
    CPU: nll_loss2d_forward_cpu
    CUDA: nll_loss2d_forward_cuda
    MPS: nll_loss2d_forward_mps

- func: nll_loss2d_backward.grad_input(Tensor grad_output, Tensor self, Tensor target, Tensor? weight, int reduction, SymInt ignore_index, Tensor total_weight, *, Tensor(a!) grad_input) -> Tensor(a!)
  python_module: nn
  dispatch:
    CPU: nll_loss2d_backward_out_cpu
    CUDA: nll_loss2d_backward_out_cuda
    MPS: nll_loss2d_backward_out_mps

- func: nll_loss2d_backward(Tensor grad_output, Tensor self, Tensor target, Tensor? weight, int reduction, SymInt ignore_index, Tensor total_weight) -> Tensor
  python_module: nn
  dispatch:
    CPU: nll_loss2d_backward_cpu
    CUDA: nll_loss2d_backward_cuda
    MPS: nll_loss2d_backward_mps

- func: smooth_l1_loss.out(Tensor self, Tensor target, int reduction=Mean, float beta=1.0, *, Tensor(a!) out) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  structured: True
  structured_inherits: TensorIteratorBase
  python_module: nn
  dispatch:
    CPU, CUDA: smooth_l1_loss_out
    MPS: smooth_l1_loss_out_mps

- func: smooth_l1_loss(Tensor self, Tensor target, int reduction=Mean, float beta=1.0) -> Tensor
  device_check: NoCheck   # TensorIterator
  structured_delegate: smooth_l1_loss.out
  python_module: nn

- func: smooth_l1_loss_backward.grad_input(Tensor grad_output, Tensor self, Tensor target, int reduction, float beta, *, Tensor(a!) grad_input) -> Tensor(a!)
  python_module: nn
  dispatch:
    CPU: smooth_l1_loss_backward_out
    CUDA: smooth_l1_loss_backward_out
    MPS: smooth_l1_loss_backward_out_mps

- func: smooth_l1_loss_backward(Tensor grad_output, Tensor self, Tensor target, int reduction, float beta) -> Tensor
  python_module: nn
  dispatch:
    CompositeExplicitAutograd: smooth_l1_loss_backward

- func: huber_loss.out(Tensor self, Tensor target, int reduction=Mean, float delta=1.0, *, Tensor(a!) out) -> Tensor(a!)
  python_module: nn
  dispatch:
    CPU, CUDA: huber_loss_out
    MPS: huber_loss_out_mps

- func: huber_loss(Tensor self, Tensor target, int reduction=Mean, float delta=1.0) -> Tensor
  python_module: nn
  dispatch:
    CPU, CUDA: huber_loss
    MPS: huber_loss_mps

- func: huber_loss_backward.out(Tensor grad_output, Tensor self, Tensor target, int reduction, float delta, *, Tensor(a!) grad_input) -> Tensor(a!)
  python_module: nn
  dispatch:
    CPU, CUDA: huber_loss_backward_out
    MPS: huber_loss_backward_out_mps

- func: huber_loss_backward(Tensor grad_output, Tensor self, Tensor target, int reduction, float delta) -> Tensor
  python_module: nn
  dispatch:
    CompositeExplicitAutograd: huber_loss_backward

- func: soft_margin_loss.out(Tensor self, Tensor target, int reduction=Mean, *, Tensor(a!) out) -> Tensor(a!)
  python_module: nn
  dispatch:
    CompositeExplicitAutograd: soft_margin_loss_out

- func: soft_margin_loss(Tensor self, Tensor target, int reduction=Mean) -> Tensor
  python_module: nn
  dispatch:
    CompositeExplicitAutograd: soft_margin_loss

- func: soft_margin_loss_backward.grad_input(Tensor grad_output, Tensor self, Tensor target, int reduction, *, Tensor(a!) grad_input) -> Tensor(a!)
  python_module: nn
  dispatch:
    CompositeExplicitAutograd: soft_margin_loss_backward_out

- func: soft_margin_loss_backward(Tensor grad_output, Tensor self, Tensor target, int reduction) -> Tensor
  python_module: nn
  dispatch:
    CompositeExplicitAutograd: soft_margin_loss_backward

- func: elu.out(Tensor self, Scalar alpha=1, Scalar scale=1, Scalar input_scale=1, *, Tensor(a!) out) -> Tensor(a!)
  structured: True
  structured_inherits: TensorIteratorBase
  device_check: NoCheck   # TensorIterator
  python_module: nn
  dispatch:
    CPU, CUDA: elu_out
    MPS: elu_out_mps

- func: elu(Tensor self, Scalar alpha=1, Scalar scale=1, Scalar input_scale=1) -> Tensor
  structured_delegate: elu.out
  device_check: NoCheck   # TensorIterator
  python_module: nn
  tags: pointwise

- func: elu_backward.grad_input(Tensor grad_output, Scalar alpha, Scalar scale, Scalar input_scale, bool is_result, Tensor self_or_result, *, Tensor(a!) grad_input) -> Tensor(a!)
  structured: True
  structured_inherits: TensorIteratorBase
  python_module: nn
  dispatch:
    CPU, CUDA: elu_backward_out
    MPS: elu_backward_out_mps

- func: elu_backward(Tensor grad_output, Scalar alpha, Scalar scale, Scalar input_scale, bool is_result, Tensor self_or_result) -> Tensor
  structured_delegate: elu_backward.grad_input
  python_module: nn

- func: elu_(Tensor(a!) self, Scalar alpha=1, Scalar scale=1, Scalar input_scale=1) -> Tensor(a!)
  structured_delegate: elu.out
  device_check: NoCheck   # TensorIterator
  python_module: nn

- func: glu.out(Tensor self, int dim=-1, *, Tensor(a!) out) -> Tensor(a!)
  structured: True
  structured_inherits: TensorIteratorBase
  python_module: nn
  dispatch:
    CPU, CUDA: glu_out
    MPS: glu_out_mps

- func: glu(Tensor self, int dim=-1) -> Tensor
  structured_delegate: glu.out
  device_check: NoCheck   # TensorIterator
  python_module: nn

- func: glu_backward.grad_input(Tensor grad_output, Tensor self, int dim, *, Tensor(a!) grad_input) -> Tensor(a!)
  python_module: nn
  dispatch:
    CPU: glu_backward_cpu_out
    CUDA: glu_backward_cuda_out
    MPS: glu_backward_mps_out

- func: glu_backward(Tensor grad_output, Tensor self, int dim) -> Tensor
  python_module: nn
  dispatch:
    CPU: glu_backward_cpu
    CUDA: glu_backward_cuda
    MPS: glu_backward_mps

- func: glu_jvp(Tensor glu, Tensor x, Tensor dx, int dim) -> Tensor
  python_module: nn
  dispatch:
    CPU, CUDA: glu_jvp
  autogen: glu_jvp.out

- func: glu_backward_jvp(Tensor grad_x, Tensor grad_glu, Tensor x, Tensor dgrad_glu, Tensor dx, int dim) -> Tensor
  python_module: nn
  dispatch:
    CPU, CUDA: glu_backward_jvp
  autogen: glu_backward_jvp.out

- func: hardsigmoid.out(Tensor self, *, Tensor(a!) out) -> Tensor(a!)
  structured: True
  structured_inherits: TensorIteratorBase
  device_check: NoCheck   # TensorIterator
  python_module: nn
  dispatch:
    CPU, CUDA: hardsigmoid_out
    MPS: hardsigmoid_out_mps
    QuantizedCPU: hardsigmoid_out_quantized_cpu

- func: hardsigmoid(Tensor self) -> Tensor
  structured_delegate: hardsigmoid.out
  device_check: NoCheck   # TensorIterator
  python_module: nn
  dispatch:
    QuantizedCPU: hardsigmoid_quantized_cpu
  tags: pointwise

- func: hardsigmoid_(Tensor(a!) self) -> Tensor(a!)
  structured_delegate: hardsigmoid.out
  device_check: NoCheck   # TensorIterator
  python_module: nn

- func: hardsigmoid_backward.grad_input(Tensor grad_output, Tensor self, *, Tensor(a!) grad_input) -> Tensor(a!)
  structured: True
  structured_inherits: TensorIteratorBase
  python_module: nn
  dispatch:
    CPU, CUDA: hardsigmoid_backward_out
    MPS: hardsigmoid_backward_out_mps

- func: hardsigmoid_backward(Tensor grad_output, Tensor self) -> Tensor
  structured_delegate: hardsigmoid_backward.grad_input
  python_module: nn

- func: hardtanh.out(Tensor self, Scalar min_val=-1, Scalar max_val=1, *, Tensor(a!) out) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  python_module: nn
  dispatch:
    CPU, CUDA, MPS: hardtanh_out
    QuantizedCPU: hardtanh_out_quantized_cpu

- func: hardtanh(Tensor self, Scalar min_val=-1, Scalar max_val=1) -> Tensor
  device_check: NoCheck   # TensorIterator
  python_module: nn
  dispatch:
    CPU, CUDA, MPS: hardtanh
    QuantizedCPU: hardtanh_quantized_cpu
  tags: [pointwise, core]

- func: hardtanh_backward.grad_input(Tensor grad_output, Tensor self, Scalar min_val, Scalar max_val, *, Tensor(a!) grad_input) -> Tensor(a!)
  python_module: nn
  dispatch:
    CPU, CUDA: hardtanh_backward_out
    MPS: hardtanh_backward_out_mps

- func: hardtanh_backward(Tensor grad_output, Tensor self, Scalar min_val, Scalar max_val) -> Tensor
  python_module: nn
  dispatch:
    CPU, CUDA: hardtanh_backward
    MPS: hardtanh_backward_mps

- func: hardtanh_(Tensor(a!) self, Scalar min_val=-1, Scalar max_val=1) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  python_module: nn
  dispatch:
    CPU, CUDA, MPS: hardtanh_
    QuantizedCPU: hardtanh_quantized_cpu_

- func: hardswish.out(Tensor self, *, Tensor(a!) out) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  python_module: nn
  dispatch:
    CPU, CUDA: hardswish_out
    MPS: hardswish_out_mps

- func: hardswish(Tensor self) -> Tensor
  device_check: NoCheck   # TensorIterator
  python_module: nn
  dispatch:
    CPU, CUDA: hardswish
    MPS: hardswish_mps

- func: hardswish_(Tensor(a!) self) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  python_module: nn
  dispatch:
    CPU, CUDA: hardswish_
    MPS: hardswish_mps_

- func: hardswish_backward(Tensor grad_output, Tensor self) -> Tensor
  python_module: nn
  dispatch:
    CPU, CUDA: hardswish_backward
    MPS: hardswish_backward_mps
  autogen: hardswish_backward.out

- func: leaky_relu.out(Tensor self, Scalar negative_slope=0.01, *, Tensor(a!) out) -> Tensor(a!)
  structured: True
  structured_inherits: TensorIteratorBase
  device_check: NoCheck   # TensorIterator
  python_module: nn
  dispatch:
    CPU, CUDA: leaky_relu_out
    MPS: leaky_relu_out_mps
    QuantizedCPU: leaky_relu_out_quantized_cpu

- func: leaky_relu(Tensor self, Scalar negative_slope=0.01) -> Tensor
  structured_delegate: leaky_relu.out
  device_check: NoCheck   # TensorIterator
  python_module: nn
  dispatch:
    QuantizedCPU: leaky_relu_quantized_cpu
  tags: core

- func: leaky_relu_backward.grad_input(Tensor grad_output, Tensor self, Scalar negative_slope, bool self_is_result, *, Tensor(a!) grad_input) -> Tensor(a!)
  structured: True
  structured_inherits: TensorIteratorBase
  python_module: nn
  dispatch:
    CPU, CUDA: leaky_relu_backward_out
    MPS: leaky_relu_backward_out_mps

- func: leaky_relu_backward(Tensor grad_output, Tensor self, Scalar negative_slope, bool self_is_result) -> Tensor
  structured_delegate: leaky_relu_backward.grad_input
  python_module: nn

- func: leaky_relu_(Tensor(a!) self, Scalar negative_slope=0.01) -> Tensor(a!)
  structured_delegate: leaky_relu.out
  device_check: NoCheck   # TensorIterator
  python_module: nn
  dispatch:
    QuantizedCPU: leaky_relu_quantized_cpu_

- func: log_sigmoid.out(Tensor self, *, Tensor(a!) out) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  python_module: nn

- func: log_sigmoid(Tensor self) -> Tensor
  device_check: NoCheck   # TensorIterator
  python_module: nn

- func: log_sigmoid_forward.output(Tensor self, *, Tensor(a!) output, Tensor(b!) buffer) -> (Tensor(a!), Tensor(b!))
  device_check: NoCheck   # TensorIterator
  python_module: nn
  dispatch:
    CPU: log_sigmoid_forward_out_cpu
    CUDA: log_sigmoid_forward_out_cuda
    MPS: log_sigmoid_forward_out_mps

- func: log_sigmoid_forward(Tensor self) -> (Tensor output, Tensor buffer)
  device_check: NoCheck   # TensorIterator
  python_module: nn
  dispatch:
    CPU: log_sigmoid_forward_cpu
    CUDA: log_sigmoid_forward_cuda
    MPS: log_sigmoid_forward_mps

- func: log_sigmoid_backward.grad_input(Tensor grad_output, Tensor self, Tensor buffer, *, Tensor(a!) grad_input) -> Tensor(a!)
  python_module: nn
  dispatch:
    CPU: log_sigmoid_backward_cpu_out
    CUDA: log_sigmoid_backward_cuda_out
    MPS: log_sigmoid_backward_mps_out

- func: log_sigmoid_backward(Tensor grad_output, Tensor self, Tensor buffer) -> Tensor
  python_module: nn
  dispatch:
    CPU: log_sigmoid_backward_cpu
    CUDA: log_sigmoid_backward_cuda
    MPS: log_sigmoid_backward_mps

- func: rrelu_with_noise.out(Tensor self, Tensor(b!) noise, Scalar lower=0.125, Scalar upper=0.3333333333333333, bool training=False, Generator? generator=None, *, Tensor(a!) out) -> Tensor(a!)
  python_module: nn
  tags: nondeterministic_seeded
  dispatch:
    CPU: rrelu_with_noise_out_cpu
    CUDA: rrelu_with_noise_out_cuda

- func: rrelu_with_noise(Tensor self, Tensor(b!) noise, Scalar lower=0.125, Scalar upper=0.3333333333333333, bool training=False, Generator? generator=None) -> Tensor
  python_module: nn
  dispatch:
    CPU: rrelu_with_noise_cpu
    CUDA: rrelu_with_noise_cuda
  tags: nondeterministic_seeded
  autogen: rrelu_with_noise_functional

- func: rrelu_with_noise_backward(Tensor grad_output, Tensor self, Tensor noise, Scalar lower, Scalar upper, bool training, bool self_is_result) -> Tensor
  python_module: nn
  dispatch:
    CompositeExplicitAutograd: rrelu_with_noise_backward
  autogen: rrelu_with_noise_backward.out

- func: rrelu_with_noise_(Tensor(a!) self, Tensor(b!) noise, Scalar lower=0.125, Scalar upper=0.3333333333333333, bool training=False, Generator? generator=None) -> Tensor(a!)
  python_module: nn
  tags: nondeterministic_seeded
  dispatch:
    CPU: rrelu_with_noise_cpu_
    CUDA: rrelu_with_noise_cuda_

- func: softplus.out(Tensor self, Scalar beta=1, Scalar threshold=20, *, Tensor(a!) out) -> Tensor(a!)
  structured: True
  structured_inherits: TensorIteratorBase
  device_check: NoCheck   # TensorIterator
  python_module: nn
  dispatch:
    CPU, CUDA: softplus_out
    MPS: softplus_out_mps

- func: softplus(Tensor self, Scalar beta=1, Scalar threshold=20) -> Tensor
  structured_delegate: softplus.out
  device_check: NoCheck   # TensorIterator
  python_module: nn
  tags: pointwise

- func: softplus_backward.grad_input(Tensor grad_output, Tensor self, Scalar beta, Scalar threshold, *, Tensor(a!) grad_input) -> Tensor(a!)
  structured: True
  structured_inherits: TensorIteratorBase
  python_module: nn
  dispatch:
    CPU, CUDA: softplus_backward_out
    MPS: softplus_backward_out_mps

- func: softplus_backward(Tensor grad_output, Tensor self, Scalar beta, Scalar threshold) -> Tensor
  structured_delegate: softplus_backward.grad_input
  python_module: nn

- func: softshrink.out(Tensor self, Scalar lambd=0.5, *, Tensor(a!) out) -> Tensor(a!)
  structured: True
  structured_inherits: TensorIteratorBase
  device_check: NoCheck   # TensorIterator
  python_module: nn
  dispatch:
    CPU, CUDA: softshrink_out
    MPS: softshrink_out_mps

- func: softshrink(Tensor self, Scalar lambd=0.5) -> Tensor
  structured_delegate: softshrink.out
  device_check: NoCheck   # TensorIterator
  python_module: nn
  tags: pointwise

- func: softshrink_backward.grad_input(Tensor grad_output, Tensor self, Scalar lambd, *, Tensor(a!) grad_input) -> Tensor(a!)
  structured: True
  structured_inherits: TensorIteratorBase
  python_module: nn
  dispatch:
    CPU, CUDA: softshrink_backward_out
    MPS: softshrink_backward_out_mps

- func: softshrink_backward(Tensor grad_output, Tensor self, Scalar lambd) -> Tensor
  structured_delegate: softshrink_backward.grad_input
  python_module: nn

- func: adaptive_avg_pool2d.out(Tensor self, SymInt[2] output_size, *, Tensor(a!) out) -> Tensor(a!)
  python_module: nn
  dispatch:
    CPU: adaptive_avg_pool2d_out_cpu
    CUDA: adaptive_avg_pool2d_out_cuda
    MPS: adaptive_avg_pool2d_out_mps
    MkldnnCPU: mkldnn_adaptive_avg_pool2d_out_stub

- func: adaptive_avg_pool2d(Tensor self, SymInt[2] output_size) -> Tensor
  python_module: nn
  dispatch:
    CompositeImplicitAutograd: adaptive_avg_pool2d_symint

- func: mkldnn_adaptive_avg_pool2d(Tensor self, int[2] output_size) -> Tensor
  dispatch:
    MkldnnCPU: mkldnn_adaptive_avg_pool2d

- func: mkldnn_adaptive_avg_pool2d.out(Tensor self, int[2] output_size, *, Tensor(a!) out) -> Tensor(a!)
  dispatch:
    MkldnnCPU: mkldnn_adaptive_avg_pool2d_out

- func: mkldnn_adaptive_avg_pool2d_backward(Tensor grad_output, Tensor self) -> Tensor
  dispatch:
    MkldnnCPU: mkldnn_adaptive_avg_pool2d_backward
  autogen: mkldnn_adaptive_avg_pool2d_backward.out

- func: _adaptive_avg_pool2d(Tensor self, SymInt[2] output_size) -> Tensor
  dispatch:
    CPU: adaptive_avg_pool2d_cpu
    CUDA: adaptive_avg_pool2d_cuda
    MPS: adaptive_avg_pool2d_mps
    QuantizedCPU: adaptive_avg_pool2d_quantized_cpu
    QuantizedCUDA: adaptive_avg_pool2d_quantized_cuda
  autogen: _adaptive_avg_pool2d.out
  tags: core

- func: _adaptive_avg_pool2d_backward(Tensor grad_output, Tensor self) -> Tensor
  python_module: nn
  dispatch:
    CPU: adaptive_avg_pool2d_backward_cpu
    CUDA: adaptive_avg_pool2d_backward_cuda
    MPS: adaptive_avg_pool2d_backward_mps
  autogen: _adaptive_avg_pool2d_backward.out
  tags: core

- func: adaptive_avg_pool3d.out(Tensor self, SymInt[3] output_size, *, Tensor(a!) out) -> Tensor(a!)
  python_module: nn
  dispatch:
    CPU: adaptive_avg_pool3d_out_cpu
    CUDA: adaptive_avg_pool3d_out_cuda
    QuantizedCPU: adaptive_avg_pool3d_out_quantized_cpu

- func: adaptive_avg_pool3d(Tensor self, SymInt[3] output_size) -> Tensor
  python_module: nn
  dispatch:
    CompositeImplicitAutograd: adaptive_avg_pool3d_symint

- func: _adaptive_avg_pool3d(Tensor self, SymInt[3] output_size) -> Tensor
  dispatch:
    CPU: adaptive_avg_pool3d_cpu
    CUDA: adaptive_avg_pool3d_cuda
    QuantizedCPU: adaptive_avg_pool3d_quantized_cpu
  autogen: _adaptive_avg_pool3d.out
  tags: core

- func: adaptive_avg_pool3d_backward.grad_input(Tensor grad_output, Tensor self, *, Tensor(a!) grad_input) -> Tensor(a!)
  python_module: nn
  dispatch:
    CPU: adaptive_avg_pool3d_backward_out_cpu
    CUDA: adaptive_avg_pool3d_backward_out_cuda

- func: _adaptive_avg_pool3d_backward(Tensor grad_output, Tensor self) -> Tensor
  python_module: nn
  dispatch:
    CPU: adaptive_avg_pool3d_backward_cpu
    CUDA: adaptive_avg_pool3d_backward_cuda
  autogen: _adaptive_avg_pool3d_backward.out

# Return: (Tensor output, Tensor indices)
- func: adaptive_max_pool2d.out(Tensor self, int[2] output_size, *, Tensor(a!) out, Tensor(b!) indices) -> (Tensor(a!), Tensor(b!))
  python_module: nn
  structured: True
  dispatch:
    CPU: adaptive_max_pool2d_out_cpu
    CUDA: adaptive_max_pool2d_out_cuda
    MPS: adaptive_max_pool2d_out_mps

# Return: (Tensor output, Tensor indices)
- func: adaptive_max_pool2d(Tensor self, int[2] output_size) -> (Tensor, Tensor)
  python_module: nn
  structured_delegate: adaptive_max_pool2d.out

- func: adaptive_max_pool2d_backward.grad_input(Tensor grad_output, Tensor self, Tensor indices, *, Tensor(a!) grad_input) -> Tensor(a!)
  python_module: nn
  structured: True
  dispatch:
    CPU: adaptive_max_pool2d_backward_out_cpu
    CUDA: adaptive_max_pool2d_backward_out_cuda
    MPS: adaptive_max_pool2d_backward_out_mps

- func: adaptive_max_pool2d_backward(Tensor grad_output, Tensor self, Tensor indices) -> Tensor
  python_module: nn
  structured_delegate: adaptive_max_pool2d_backward.grad_input

# Return: (Tensor output, Tensor indices)
- func: adaptive_max_pool3d.out(Tensor self, int[3] output_size, *, Tensor(a!) out, Tensor(b!) indices) -> (Tensor(a!), Tensor(b!))
  python_module: nn
  structured: True
  dispatch:
    CPU: adaptive_max_pool3d_out_cpu
    CUDA: adaptive_max_pool3d_out_cuda

# Return: (Tensor output, Tensor indices)
- func: adaptive_max_pool3d(Tensor self, int[3] output_size) -> (Tensor, Tensor)
  python_module: nn
  structured_delegate: adaptive_max_pool3d.out

- func: adaptive_max_pool3d_backward.grad_input(Tensor grad_output, Tensor self, Tensor indices, *, Tensor(a!) grad_input) -> Tensor(a!)
  python_module: nn
  structured: True
  dispatch:
    CPU: adaptive_max_pool3d_backward_out_cpu
    CUDA: adaptive_max_pool3d_backward_out_cuda

- func: adaptive_max_pool3d_backward(Tensor grad_output, Tensor self, Tensor indices) -> Tensor
  python_module: nn
  structured_delegate: adaptive_max_pool3d_backward.grad_input

- func: avg_pool2d.out(Tensor self, int[2] kernel_size, int[2] stride=[], int[2] padding=0, bool ceil_mode=False, bool count_include_pad=True, int? divisor_override=None, *, Tensor(a!) out) -> Tensor(a!)
  python_module: nn
  structured: True
  precomputed:
  - kernel_size -> int kH, int kW
  - stride -> int dH, int dW
  - padding -> int padH, int padW
  dispatch:
    CPU: avg_pool2d_out_cpu
    CUDA: avg_pool2d_out_cuda
    MPS: avg_pool2d_out_mps
    MkldnnCPU: mkldnn_avg_pool2d_out

- func: avg_pool2d(Tensor self, int[2] kernel_size, int[2] stride=[], int[2] padding=0, bool ceil_mode=False, bool count_include_pad=True, int? divisor_override=None) -> Tensor
  python_module: nn
  structured_delegate: avg_pool2d.out
  dispatch:
    MkldnnCPU: mkldnn_avg_pool2d
    QuantizedCPU: avg_pool2d_quantized_cpu
  tags: core

- func: avg_pool2d_backward.grad_input(Tensor grad_output, Tensor self, int[2] kernel_size, int[2] stride, int[2] padding, bool ceil_mode, bool count_include_pad, int? divisor_override, *, Tensor(a!) grad_input) -> Tensor(a!)
  python_module: nn
  structured: True
  dispatch:
    CPU: avg_pool2d_backward_out_cpu
    CUDA: avg_pool2d_backward_out_cuda
    MPS: avg_pool2d_backward_out_mps
    MkldnnCPU: mkldnn_avg_pool2d_backward_out

- func: avg_pool2d_backward(Tensor grad_output, Tensor self, int[2] kernel_size, int[2] stride, int[2] padding, bool ceil_mode, bool count_include_pad, int? divisor_override) -> Tensor
  python_module: nn
  structured_delegate: avg_pool2d_backward.grad_input
  dispatch:
    MkldnnCPU: mkldnn_avg_pool2d_backward
  tags: core

- func: avg_pool3d.out(Tensor self, int[3] kernel_size, int[3] stride=[], int[3] padding=0, bool ceil_mode=False, bool count_include_pad=True, int? divisor_override=None, *, Tensor(a!) out) -> Tensor(a!)
  python_module: nn
  structured: True
  dispatch:
    CPU: avg_pool3d_out_cpu
    CUDA: avg_pool3d_out_cuda
    MkldnnCPU: mkldnn_avg_pool3d_out

- func: avg_pool3d(Tensor self, int[3] kernel_size, int[3] stride=[], int[3] padding=0, bool ceil_mode=False, bool count_include_pad=True, int? divisor_override=None) -> Tensor
  python_module: nn
  structured_delegate: avg_pool3d.out
  dispatch:
    MkldnnCPU: mkldnn_avg_pool3d
    QuantizedCPU: avg_pool3d_quantized_cpu
  tags: core

- func: avg_pool3d_backward.grad_input(Tensor grad_output, Tensor self, int[3] kernel_size, int[3] stride, int[3] padding, bool ceil_mode, bool count_include_pad, int? divisor_override, *, Tensor(a!) grad_input) -> Tensor(a!)
  python_module: nn
  structured: True
  dispatch:
    CPU: avg_pool3d_backward_out_cpu
    CUDA: avg_pool3d_backward_out_cuda
    MkldnnCPU: mkldnn_avg_pool3d_backward_out

- func: avg_pool3d_backward(Tensor grad_output, Tensor self, int[3] kernel_size, int[3] stride, int[3] padding, bool ceil_mode, bool count_include_pad, int? divisor_override) -> Tensor
  python_module: nn
  structured_delegate: avg_pool3d_backward.grad_input
  dispatch:
    MkldnnCPU: mkldnn_avg_pool3d_backward

# Return: (Tensor output, Tensor indices)
- func: fractional_max_pool2d.output(Tensor self, int[2] kernel_size, int[2] output_size, Tensor random_samples, *, Tensor(a!) output, Tensor(b!) indices) -> (Tensor(a!), Tensor(b!))
  python_module: nn
  structured: True
  dispatch:
    CPU: fractional_max_pool2d_out_cpu
    CUDA: fractional_max_pool2d_out_cuda

# Return: (Tensor output, Tensor indices)
- func: fractional_max_pool2d(Tensor self, int[2] kernel_size, int[2] output_size, Tensor random_samples) -> (Tensor, Tensor)
  python_module: nn
  structured_delegate: fractional_max_pool2d.output

- func: fractional_max_pool2d_backward.grad_input(Tensor grad_output, Tensor self, int[2] kernel_size, int[2] output_size, Tensor indices, *, Tensor(a!) grad_input) -> Tensor(a!)
  python_module: nn
  structured: True
  dispatch:
    CPU: fractional_max_pool2d_backward_cpu
    CUDA: fractional_max_pool2d_backward_cuda

- func: fractional_max_pool2d_backward(Tensor grad_output, Tensor self, int[2] kernel_size, int[2] output_size, Tensor indices) -> Tensor
  python_module: nn
  structured_delegate: fractional_max_pool2d_backward.grad_input

# Return: (Tensor output, Tensor indices)
- func: fractional_max_pool3d.output(Tensor self, int[3] kernel_size, int[3] output_size, Tensor random_samples, *, Tensor(a!) output, Tensor(b!) indices) -> (Tensor(a!), Tensor(b!))
  python_module: nn
  structured: True
  precomputed:
  - kernel_size -> int poolSizeT, int poolSizeH, int poolSizeW
  - output_size -> int outputT, int outputH, int outputW
  - int numBatch, int numPlanes, int inputT, int inputH, int inputW
  dispatch:
    CPU: fractional_max_pool3d_out_cpu
    CUDA: fractional_max_pool3d_out_cuda

# Return: (Tensor output, Tensor indices)
- func: fractional_max_pool3d(Tensor self, int[3] kernel_size, int[3] output_size, Tensor random_samples) -> (Tensor, Tensor)
  python_module: nn
  structured_delegate: fractional_max_pool3d.output

- func: fractional_max_pool3d_backward.grad_input(Tensor grad_output, Tensor self, int[3] kernel_size, int[3] output_size, Tensor indices, *, Tensor(a!) grad_input) -> Tensor(a!)
  python_module: nn
  dispatch:
    CPU: fractional_max_pool3d_backward_out_cpu
    CUDA: fractional_max_pool3d_backward_out_cuda

- func: fractional_max_pool3d_backward(Tensor grad_output, Tensor self, int[3] kernel_size, int[3] output_size, Tensor indices) -> Tensor
  python_module: nn
  dispatch:
    CPU: fractional_max_pool3d_backward_cpu
    CUDA: fractional_max_pool3d_backward_cuda

# Return: (Tensor output, Tensor indices)
- func: max_pool2d_with_indices.out(Tensor self, int[2] kernel_size, int[2] stride=[], int[2] padding=0, int[2] dilation=1, bool ceil_mode=False, *, Tensor(a!) out, Tensor(b!) indices) -> (Tensor(a!), Tensor(b!))
  python_module: nn
  structured: True
  dispatch:
    CPU: max_pool2d_with_indices_out_cpu
    CUDA: max_pool2d_with_indices_out_cuda
    MPS: max_pool2d_with_indices_out_mps

# Return: (Tensor output, Tensor indices)
- func: max_pool2d_with_indices(Tensor self, int[2] kernel_size, int[2] stride=[], int[2] padding=0, int[2] dilation=1, bool ceil_mode=False) -> (Tensor, Tensor)
  python_module: nn
  structured_delegate: max_pool2d_with_indices.out
  tags: core

- func: max_pool2d_with_indices_backward.grad_input(Tensor grad_output, Tensor self, int[2] kernel_size, int[2] stride, int[2] padding, int[2] dilation, bool ceil_mode, Tensor indices, *, Tensor(a!) grad_input) -> Tensor(a!)
  python_module: nn
  structured: True
  dispatch:
    CPU: max_pool2d_with_indices_backward_out_cpu
    CUDA: max_pool2d_with_indices_backward_out_cuda
    MPS: max_pool2d_with_indices_backward_out_mps

- func: max_pool2d_with_indices_backward(Tensor grad_output, Tensor self, int[2] kernel_size, int[2] stride, int[2] padding, int[2] dilation, bool ceil_mode, Tensor indices) -> Tensor
  python_module: nn
  structured_delegate: max_pool2d_with_indices_backward.grad_input
  tags: core

# Return: (Tensor output, Tensor indices)
- func: max_pool3d_with_indices.out(Tensor self, int[3] kernel_size, int[3] stride=[], int[3] padding=0, int[3] dilation=1, bool ceil_mode=False, *, Tensor(a!) out, Tensor(b!) indices) -> (Tensor(a!), Tensor(b!))
  python_module: nn
  dispatch:
    CPU: max_pool3d_with_indices_out_cpu
    CUDA: max_pool3d_with_indices_out_cuda

# Return: (Tensor output, Tensor indices)
- func: max_pool3d_with_indices(Tensor self, int[3] kernel_size, int[3] stride=[], int[3] padding=0, int[3] dilation=1, bool ceil_mode=False) -> (Tensor, Tensor)
  python_module: nn
  dispatch:
    CPU: max_pool3d_with_indices_cpu
    CUDA: max_pool3d_with_indices_cuda
  tags: core

- func: max_pool3d_with_indices_backward.grad_input(Tensor grad_output, Tensor self, int[3] kernel_size, int[3] stride, int[3] padding, int[3] dilation, bool ceil_mode, Tensor indices, *, Tensor(a!) grad_input) -> Tensor(a!)
  python_module: nn
  dispatch:
    CPU: max_pool3d_with_indices_backward_out_cpu
    CUDA: max_pool3d_with_indices_backward_out_cuda

- func: max_pool3d_with_indices_backward(Tensor grad_output, Tensor self, int[3] kernel_size, int[3] stride, int[3] padding, int[3] dilation, bool ceil_mode, Tensor indices) -> Tensor
  python_module: nn
  dispatch:
    CPU: max_pool3d_with_indices_backward_cpu
    CUDA: max_pool3d_with_indices_backward_cuda

- func: max_unpool2d.out(Tensor self, Tensor indices, SymInt[2] output_size, *, Tensor(a!) out) -> Tensor(a!)
  python_module: nn
  dispatch:
    CPU: max_unpooling2d_forward_out_cpu
    CUDA: max_unpooling2d_forward_out_cuda

- func: max_unpool2d(Tensor self, Tensor indices, SymInt[2] output_size) -> Tensor
  python_module: nn
  dispatch:
    CPU: max_unpooling2d_forward_cpu
    CUDA: max_unpooling2d_forward_cuda

- func: max_unpool3d.out(Tensor self, Tensor indices, SymInt[3] output_size, int[3] stride, int[3] padding, *, Tensor(a!) out) -> Tensor(a!)
  python_module: nn
  dispatch:
    CPU: max_unpooling3d_forward_out_cpu
    CUDA: max_unpooling3d_forward_out_cuda

- func: max_unpool3d(Tensor self, Tensor indices, SymInt[3] output_size, int[3] stride, int[3] padding) -> Tensor
  python_module: nn
  dispatch:
    CPU: max_unpooling3d_forward_cpu
    CUDA: max_unpooling3d_forward_cuda

- func: reflection_pad1d.out(Tensor self, SymInt[2] padding, *, Tensor(a!) out) -> Tensor(a!)
  python_module: nn
  structured: True
  dispatch:
    CPU: reflection_pad1d_out_cpu
    QuantizedCPU: reflection_pad1d_out_quantized_cpu
    CUDA: reflection_pad1d_out_cuda
    MPS: reflection_pad1d_out_mps

- func: reflection_pad1d(Tensor self, SymInt[2] padding) -> Tensor
  python_module: nn
  structured_delegate: reflection_pad1d.out
  tags: core

- func: reflection_pad1d_backward.grad_input(Tensor grad_output, Tensor self, SymInt[2] padding, *, Tensor(a!) grad_input) -> Tensor(a!)
  python_module: nn
  structured: True
  dispatch:
    CPU: reflection_pad1d_backward_out_cpu
    CUDA: reflection_pad1d_backward_out_cuda
    MPS: reflection_pad1d_backward_out_mps

- func: reflection_pad1d_backward(Tensor grad_output, Tensor self, SymInt[2] padding) -> Tensor
  python_module: nn
  structured_delegate: reflection_pad1d_backward.grad_input

- func: reflection_pad2d.out(Tensor self, SymInt[4] padding, *, Tensor(a!) out) -> Tensor(a!)
  python_module: nn
  dispatch:
    CPU, QuantizedCPU: reflection_pad2d_out_cpu
    CUDA: reflection_pad2d_out_cuda
    MPS: reflection_pad2d_out_mps

- func: reflection_pad2d(Tensor self, SymInt[4] padding) -> Tensor
  python_module: nn
  dispatch:
    CPU: reflection_pad2d_cpu
    QuantizedCPU: reflection_pad2d_quantized_cpu
    CUDA: reflection_pad2d_cuda
    MPS: reflection_pad2d_mps
  tags: core

- func: reflection_pad2d_backward.grad_input(Tensor grad_output, Tensor self, SymInt[4] padding, *, Tensor(a!) grad_input) -> Tensor(a!)
  python_module: nn
  dispatch:
    CPU: reflection_pad2d_backward_out_cpu
    CUDA: reflection_pad2d_backward_out_cuda
    MPS: reflection_pad2d_backward_out_mps

- func: reflection_pad2d_backward(Tensor grad_output, Tensor self, SymInt[4] padding) -> Tensor
  python_module: nn
  dispatch:
    CPU: reflection_pad2d_backward_cpu
    CUDA: reflection_pad2d_backward_cuda
    MPS: reflection_pad2d_backward_mps

- func: reflection_pad3d.out(Tensor self, SymInt[6] padding, *, Tensor(a!) out) -> Tensor(a!)
  python_module: nn
  structured: True
  dispatch:
    CPU: reflection_pad3d_out_cpu
    CUDA: reflection_pad3d_out_cuda
    MPS: reflection_pad3d_out_mps

- func: reflection_pad3d(Tensor self, SymInt[6] padding) -> Tensor
  python_module: nn
  structured_delegate: reflection_pad3d.out
  tags: core

- func: reflection_pad3d_backward.grad_input(Tensor grad_output, Tensor self, SymInt[6] padding, *, Tensor(a!) grad_input) -> Tensor(a!)
  python_module: nn
  structured: True
  dispatch:
    CPU: reflection_pad3d_backward_out_cpu
    CUDA: reflection_pad3d_backward_out_cuda
    MPS: reflection_pad3d_backward_out_mps

- func: reflection_pad3d_backward(Tensor grad_output, Tensor self, SymInt[6] padding) -> Tensor
  python_module: nn
  structured_delegate: reflection_pad3d_backward.grad_input

- func: replication_pad1d.out(Tensor self, SymInt[2] padding, *, Tensor(a!) out) -> Tensor(a!)
  python_module: nn
  structured: True
  dispatch:
    CPU: replication_pad1d_out_cpu
    CUDA: replication_pad1d_out_cuda
    MPS: replication_pad1d_out_mps

- func: replication_pad1d(Tensor self, SymInt[2] padding) -> Tensor
  python_module: nn
  structured_delegate: replication_pad1d.out

- func: replication_pad1d_backward.grad_input(Tensor grad_output, Tensor self, SymInt[2] padding, *, Tensor(a!) grad_input) -> Tensor(a!)
  python_module: nn
  structured: True
  dispatch:
    CPU: replication_pad1d_backward_out_cpu
    CUDA: replication_pad1d_backward_out_cuda
    MPS: replication_pad1d_backward_out_mps

- func: replication_pad1d_backward(Tensor grad_output, Tensor self, SymInt[2] padding) -> Tensor
  python_module: nn
  structured_delegate: replication_pad1d_backward.grad_input

- func: replication_pad2d.out(Tensor self, SymInt[4] padding, *, Tensor(a!) out) -> Tensor(a!)
  python_module: nn
  structured: True
  dispatch:
    CPU: replication_pad2d_out_cpu
    CUDA: replication_pad2d_out_cuda
    MPS: replication_pad2d_out_mps

- func: replication_pad2d(Tensor self, SymInt[4] padding) -> Tensor
  python_module: nn
  structured_delegate: replication_pad2d.out
  tags: core

- func: replication_pad2d_backward.grad_input(Tensor grad_output, Tensor self, SymInt[4] padding, *, Tensor(a!) grad_input) -> Tensor(a!)
  python_module: nn
  dispatch:
    CPU: replication_pad2d_backward_out_cpu
    CUDA: replication_pad2d_backward_out_cuda
    MPS: replication_pad2d_backward_out_mps

- func: replication_pad2d_backward(Tensor grad_output, Tensor self, SymInt[4] padding) -> Tensor
  python_module: nn
  dispatch:
    CPU: replication_pad2d_backward_cpu
    CUDA: replication_pad2d_backward_cuda
    MPS: replication_pad2d_backward_mps

- func: replication_pad3d.out(Tensor self, SymInt[6] padding, *, Tensor(a!) out) -> Tensor(a!)
  python_module: nn
  structured: True
  dispatch:
    CPU: replication_pad3d_out_cpu
    CUDA: replication_pad3d_out_cuda
    MPS: replication_pad3d_out_mps

- func: replication_pad3d(Tensor self, SymInt[6] padding) -> Tensor
  python_module: nn
  structured_delegate: replication_pad3d.out
  tags: core


- func: replication_pad3d_backward.grad_input(Tensor grad_output, Tensor self, SymInt[6] padding, *, Tensor(a!) grad_input) -> Tensor(a!)
  python_module: nn
  dispatch:
    CPU: replication_pad3d_backward_out_cpu
    CUDA: replication_pad3d_backward_out_cuda
    MPS: replication_pad3d_backward_out_mps

- func: replication_pad3d_backward(Tensor grad_output, Tensor self, SymInt[6] padding) -> Tensor
  python_module: nn
  dispatch:
    CPU: replication_pad3d_backward_cpu
    CUDA: replication_pad3d_backward_cuda
    MPS: replication_pad3d_backward_mps

- func: _pad_circular(Tensor self, SymInt[] pad) -> Tensor
  python_module: nn
  dispatch:
    CompositeImplicitAutograd: _pad_circular_symint

- func: _pad_enum(Tensor self, SymInt[] pad, int mode, float? value=None) -> Tensor
  python_module: nn
  dispatch:
    CompositeImplicitAutograd: _pad_enum_symint

- func: pad(Tensor self, SymInt[] pad, str mode=`
  - `, bool use_cutlass=True) -> (Tensor, Tensor, Tensor, Tensor, Tensor)
  dispatch:
    CUDA: _sparse_semi_structured_tile

- func: _sparse_semi_structured_apply(Tensor input, Tensor thread_masks) -> (Tensor, Tensor)
  dispatch:
    CUDA: _sparse_semi_structured_apply

- func: _sparse_semi_structured_apply_dense(Tensor input, Tensor thread_masks) -> Tensor
  dispatch:
    CUDA: _sparse_semi_structured_apply_dense

# DEPRECATED: Use torch.__sparse_semi_structured_mm/torch._sparse_semi_structured_addmm instead
- func: _sparse_semi_structured_linear(Tensor input, Tensor weight, Tensor meta, *, Tensor? bias=None, str? activation=None, ScalarType? out_dtype=None) -> Tensor
  dispatch:
    CUDA: _sparse_semi_structured_linear

- func: _sparse_semi_structured_mm(Tensor mat1, Tensor mat1_meta, Tensor mat2, *, ScalarType? out_dtype=None) -> Tensor
  dispatch:
    CUDA: _sparse_semi_structured_mm

- func: _sparse_semi_structured_addmm(Tensor input, Tensor mat1, Tensor mat1_meta, Tensor mat2, *, Scalar alpha=1, Scalar beta=1, ScalarType? out_dtype=None) -> Tensor
  dispatch:
    CUDA: _sparse_semi_structured_addmm

- func: _mixed_dtypes_linear(Tensor input, Tensor weight, Tensor scale, *, Tensor? bias=None, str? activation=None) -> Tensor
  dispatch:
    CUDA: _mixed_dtypes_linear

- func: fbgemm_linear_int8_weight_fp32_activation(Tensor input, Tensor weight, Tensor packed, Tensor col_offsets, Scalar weight_scale, Scalar weight_zero_point, Tensor bias) -> Tensor

- func: fbgemm_linear_int8_weight(Tensor input, Tensor weight, Tensor packed, Tensor col_offsets, Scalar weight_scale, Scalar weight_zero_point, Tensor bias) -> Tensor

- func: fbgemm_linear_quantize_weight(Tensor input) -> (Tensor, Tensor, float, int)

- func: fbgemm_pack_gemm_matrix_fp16(Tensor input) -> Tensor

- func: _wrapped_linear_prepack(Tensor weight, Tensor weight_scale, Tensor weight_zero_point, Tensor bias) -> Tensor

- func: _wrapped_quantized_linear_prepacked(Tensor input, Tensor input_scale, Tensor input_zero_point, Tensor packed_weight, Tensor output_scale, Tensor output_zero_point, int out_channel) -> Tensor

- func: fbgemm_linear_fp16_weight_fp32_activation(Tensor input, Tensor packed_weight, Tensor bias) -> Tensor

- func: fbgemm_linear_fp16_weight(Tensor input, Tensor packed_weight, Tensor bias) -> Tensor

- func: fbgemm_pack_quantized_matrix(Tensor input) -> Tensor

- func: fbgemm_pack_quantized_matrix.KN(Tensor input, int K, int N) -> Tensor

- func: ldexp.Tensor(Tensor self, Tensor other) -> Tensor
  variants: function, method

- func: ldexp_(Tensor(a!) self, Tensor other) -> Tensor(a!)
  variants: function, method
  tags: pointwise

- func: ldexp.out(Tensor self, Tensor other, *, Tensor(a!) out) -> Tensor(a!)
  tags: pointwise

- func: linspace(Scalar start, Scalar end, int steps, *, ScalarType? dtype=None, Layout? layout=None, Device? device=None, bool? pin_memory=None) -> Tensor
  dispatch:
    CompositeExplicitAutograd: linspace

- func: linspace.Tensor_Tensor(Tensor start, Tensor end, int steps, *, ScalarType? dtype=None, Layout? layout=None, Device? device=None, bool? pin_memory=None) -> Tensor
  category_override: factory
  dispatch:
    CompositeExplicitAutograd: linspace

- func: linspace.Tensor_Scalar(Tensor start, Scalar end, int steps, *, ScalarType? dtype=None, Layout? layout=None, Device? device=None, bool? pin_memory=None) -> Tensor
  category_override: factory
  dispatch:
    CompositeExplicitAutograd: linspace

- func: linspace.Scalar_Tensor(Scalar start, Tensor end, int steps, *, ScalarType? dtype=None, Layout? layout=None, Device? device=None, bool? pin_memory=None) -> Tensor
  category_override: factory
  dispatch:
    CompositeExplicitAutograd: linspace

- func: linspace.out(Scalar start, Scalar end, int steps, *, Tensor(a!) out) -> Tensor(a!)
  dispatch:
    CPU, Meta: linspace_out
    CUDA: linspace_cuda_out
    MPS: linspace_out_mps

- func: linspace.Tensor_Tensor_out(Tensor start, Tensor end, int steps, *, Tensor(a!) out) -> Tensor(a!)
  category_override: factory
  dispatch:
    CompositeExplicitAutograd: linspace_out

- func: linspace.Tensor_Scalar_out(Tensor start, Scalar end, int steps, *, Tensor(a!) out) -> Tensor(a!)
  category_override: factory
  dispatch:
    CompositeExplicitAutograd: linspace_out

- func: linspace.Scalar_Tensor_out(Scalar start, Tensor end, int steps, *, Tensor(a!) out) -> Tensor(a!)
  category_override: factory
  dispatch:
    CompositeExplicitAutograd: linspace_out

- func: log(Tensor self) -> Tensor
  device_check: NoCheck   # TensorIterator
  structured_delegate: log.out
  variants: function, method
  tags: [core, pointwise]

- func: log_(Tensor(a!) self) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  structured_delegate: log.out
  variants: function, method
  tags: pointwise

- func: log.out(Tensor self, *, Tensor(a!) out) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  structured: True
  structured_inherits: TensorIteratorBase
  dispatch:
    CPU, CUDA: log_out
    MPS: log_out_mps
  tags: pointwise

- func: log10(Tensor self) -> Tensor
  device_check: NoCheck   # TensorIterator
  structured_delegate: log10.out
  variants: function, method
  tags: [core, pointwise]

- func: log10_(Tensor(a!) self) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  structured_delegate: log10.out
  variants: function, method
  tags: pointwise

- func: log10.out(Tensor self, *, Tensor(a!) out) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  structured: True
  structured_inherits: TensorIteratorBase
  dispatch:
    CPU, CUDA: log10_out
    MPS: log10_out_mps
  tags: pointwise

- func: log1p(Tensor self) -> Tensor
  device_check: NoCheck   # TensorIterator
  structured_delegate: log1p.out
  variants: function, method
  dispatch:
    SparseCPU, SparseCUDA: log1p_sparse
    SparseCsrCPU, SparseCsrCUDA, SparseCsrMeta: log1p_sparse_csr
  tags: [core, pointwise]

- func: log1p_(Tensor(a!) self) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  structured_delegate: log1p.out
  variants: function, method
  dispatch:
    SparseCPU, SparseCUDA: log1p_sparse_
    SparseCsrCPU, SparseCsrCUDA, SparseCsrMeta: log1p_sparse_csr_
  tags: pointwise

- func: log1p.out(Tensor self, *, Tensor(a!) out) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  structured: True
  structured_inherits: TensorIteratorBase
  dispatch:
    CPU, CUDA: log1p_out
    MPS: log1p_out_mps
    SparseCPU, SparseCUDA: log1p_sparse_out
    SparseCsrCPU, SparseCsrCUDA, SparseCsrMeta: log1p_sparse_csr_out
  tags: pointwise

- func: log2(Tensor self) -> Tensor
  device_check: NoCheck   # TensorIterator
  structured_delegate: log2.out
  variants: function, method
  tags: [core, pointwise]

- func: log2_(Tensor(a!) self) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  structured_delegate: log2.out
  variants: function, method
  tags: pointwise

- func: log2.out(Tensor self, *, Tensor(a!) out) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  structured: True
  structured_inherits: TensorIteratorBase
  dispatch:
    CPU, CUDA: log2_out
    MPS: log2_out_mps
  tags: pointwise

- func: logaddexp.out(Tensor self, Tensor other, *, Tensor(a!) out) -> Tensor(a!)
  structured: True
  structured_inherits: TensorIteratorBase
  dispatch:
    CPU, CUDA: logaddexp_out
    MPS: logaddexp_out_mps
  tags: pointwise

- func: logaddexp(Tensor self, Tensor other) -> Tensor
  variants: method, function
  structured_delegate: logaddexp.out
  tags: pointwise

- func: logaddexp2.out(Tensor self, Tensor other, *, Tensor(a!) out) -> Tensor(a!)
  structured: True
  structured_inherits: TensorIteratorBase
  dispatch:
    CPU, CUDA: logaddexp2_out
    MPS: logaddexp2_out_mps
  tags: pointwise

- func: logaddexp2(Tensor self, Tensor other) -> Tensor
  variants: method, function
  structured_delegate: logaddexp2.out
  tags: pointwise

- func: xlogy.Tensor(Tensor self, Tensor other) -> Tensor
  device_check: NoCheck   # TensorIterator
  structured_delegate: xlogy.OutTensor
  variants: function, method
  tags: pointwise

- func: xlogy.Scalar_Self(Scalar self, Tensor other) -> Tensor
  device_check: NoCheck   # TensorIterator
  variants: function
  dispatch:
    CompositeExplicitAutograd: xlogy
  tags: pointwise

- func: xlogy.Scalar_Other(Tensor self, Scalar other) -> Tensor
  device_check: NoCheck   # TensorIterator
  variants: function, method
  dispatch:
    CompositeExplicitAutograd: xlogy
  tags: pointwise

# xlogy: inplace variant
- func: xlogy_.Tensor(Tensor(a!) self, Tensor other) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  variants: function, method
  structured_delegate: xlogy.OutTensor
  tags: pointwise

- func: xlogy_.Scalar_Other(Tensor(a!) self, Scalar other) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  variants: function, method
  dispatch:
    CompositeExplicitAutograd: xlogy_

# xlogy: out variant
- func: xlogy.OutTensor(Tensor self, Tensor other, *, Tensor(a!) out) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  structured: True
  structured_inherits: TensorIteratorBase
  variants: function
  dispatch:
    CPU, CUDA: xlogy_out
    MPS: xlogy_out_mps
  tags: pointwise

- func: xlogy.OutScalar_Self(Scalar self, Tensor other, *, Tensor(a!) out) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  variants: function
  dispatch:
    CompositeExplicitAutograd: xlogy_out
  tags: pointwise

- func: xlogy.OutScalar_Other(Tensor self, Scalar other, *, Tensor(a!) out) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  variants: function
  dispatch:
    CompositeExplicitAutograd: xlogy_out
  tags: pointwise

- func: logspace(Scalar start, Scalar end, int steps, float base=10.0, *, ScalarType? dtype=None, Layout? layout=None, Device? device=None, bool? pin_memory=None) -> Tensor
  dispatch:
    CompositeExplicitAutograd: logspace

- func: logspace.Tensor_Tensor(Tensor start, Tensor end, int steps, float base=10.0, *, ScalarType? dtype=None, Layout? layout=None, Device? device=None, bool? pin_memory=None) -> Tensor
  category_override: factory
  dispatch:
    CompositeExplicitAutograd: logspace

- func: logspace.Tensor_Scalar(Tensor start, Scalar end, int steps, float base=10.0, *, ScalarType? dtype=None, Layout? layout=None, Device? device=None, bool? pin_memory=None) -> Tensor
  category_override: factory
  dispatch:
    CompositeExplicitAutograd: logspace

- func: logspace.Scalar_Tensor(Scalar start, Tensor end, int steps, float base=10.0, *, ScalarType? dtype=None, Layout? layout=None, Device? device=None, bool? pin_memory=None) -> Tensor
  category_override: factory
  dispatch:
    CompositeExplicitAutograd: logspace

- func: logspace.out(Scalar start, Scalar end, int steps, float base=10.0, *, Tensor(a!) out) -> Tensor(a!)
  dispatch:
    CPU, Meta: logspace_out
    CUDA: logspace_cuda_out

- func: logspace.Tensor_Tensor_out(Tensor start, Tensor end, int steps, float base=10.0, *, Tensor(a!) out) -> Tensor(a!)
  category_override: factory
  dispatch:
    CompositeExplicitAutograd: logspace_out

- func: logspace.Tensor_Scalar_out(Tensor start, Scalar end, int steps, float base=10.0, *, Tensor(a!) out) -> Tensor(a!)
  category_override: factory
  dispatch:
    CompositeExplicitAutograd: logspace_out

- func: logspace.Scalar_Tensor_out(Scalar start, Tensor end, int steps, float base=10.0, *, Tensor(a!) out) -> Tensor(a!)
  category_override: factory
  dispatch:
    CompositeExplicitAutograd: logspace_out

# log_softmax allows positional dtype, unlike most operators, because kwonly is BC-breaking when loading jit models.
- func: log_softmax.int(Tensor self, int dim, ScalarType? dtype=None) -> Tensor
  variants: function, method

- func: log_softmax.int_out(Tensor self, int dim, ScalarType? dtype=None, *, Tensor(a!) out) -> Tensor(a!)
  variants: function
  dispatch:
    CompositeExplicitAutograd: log_softmax_out

- func: log_softmax.Dimname(Tensor self, Dimname dim, *, ScalarType? dtype=None) -> Tensor
  variants: function, method

- func: _log_softmax(Tensor self, int dim, bool half_to_float) -> Tensor
  structured_delegate: _log_softmax.out
  tags: core

- func: _log_softmax.out(Tensor self, int dim, bool half_to_float, *, Tensor(a!) out) -> Tensor(a!)
  structured: True
  dispatch:
    CPU: log_softmax_cpu_out
    CUDA: log_softmax_cuda_out
    MPS: log_softmax_mps_out

- func: _log_softmax_backward_data(Tensor grad_output, Tensor output, int dim, ScalarType input_dtype) -> Tensor
  structured_delegate: _log_softmax_backward_data.out

- func: _log_softmax_backward_data.out(Tensor grad_output, Tensor output, int dim, ScalarType input_dtype, *, Tensor(a!) out) -> Tensor(a!)
  structured: True
  dispatch:
    CPU: log_softmax_backward_cpu_out
    CUDA: log_softmax_backward_cuda_out
    MPS: log_softmax_backward_mps_out

- func: _logcumsumexp(Tensor self, int dim) -> Tensor
  dispatch:
    CPU: _logcumsumexp_cpu
    CUDA: _logcumsumexp_cuda

- func: _logcumsumexp.out(Tensor self, int dim, *, Tensor(a!) out) -> Tensor(a!)
  dispatch:
    CPU: _logcumsumexp_out_cpu
    CUDA: _logcumsumexp_out_cuda

- func: logcumsumexp(Tensor self, int dim) -> Tensor
  variants: function, method
  dispatch:
    CompositeExplicitAutograd: logcumsumexp

- func: logcumsumexp.out(Tensor self, int dim, *, Tensor(a!) out) -> Tensor(a!)
  dispatch:
    CompositeExplicitAutograd: logcumsumexp_out

- func: logcumsumexp.dimname(Tensor self, Dimname dim) -> Tensor
  variants: function, method

- func: logcumsumexp.dimname_out(Tensor self, Dimname dim, *, Tensor(a!) out) -> Tensor(a!)

- func: logsumexp(Tensor self, int[1] dim, bool keepdim=False) -> Tensor
  device_check: NoCheck   # TensorIterator
  variants: function, method
  dispatch:
    CompositeExplicitAutograd: logsumexp

- func: logsumexp.out(Tensor self, int[1] dim, bool keepdim=False, *, Tensor(a!) out) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  dispatch:
    # calls squeeze
    CompositeExplicitAutogradNonFunctional: logsumexp_out

- func: logsumexp.names(Tensor self, Dimname[1] dim, bool keepdim=False) -> Tensor
  device_check: NoCheck   # TensorIterator
  variants: function, method

- func: logsumexp.names_out(Tensor self, Dimname[1] dim, bool keepdim=False, *, Tensor(a!) out) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator

- func: margin_ranking_loss(Tensor input1, Tensor input2, Tensor target, float margin=0.0, int reduction=Mean) -> Tensor

- func: matmul(Tensor self, Tensor other) -> Tensor
  variants: function, method
  dispatch:
    CompositeImplicitAutograd: matmul
    NestedTensorCPU, NestedTensorCUDA: matmul_nested

- func: matmul_backward(Tensor grad, Tensor self, Tensor other, bool[2] mask) -> (Tensor, Tensor)
  dispatch:
    NestedTensorCPU, NestedTensorCUDA: matmul_backward_nested
  autogen: matmul_backward.out

- func: matmul.out(Tensor self, Tensor other, *, Tensor(a!) out) -> Tensor(a!)
  dispatch:
    CompositeImplicitAutograd: matmul_out
    NestedTensorCPU, NestedTensorCUDA: matmul_out_nested

# Alias to linalg.matrix_power
- func: matrix_power(Tensor self, int n) -> Tensor
  variants: function, method

# Alias to linalg.matrix_power
- func: matrix_power.out(Tensor self, int n, *, Tensor(a!) out) -> Tensor(a!)

# Alias to linalg.matrix_exp
- func: matrix_exp(Tensor self) -> Tensor
  variants: function, method

# This function should be deprecated in favor of differential_analytic_matrix_function in FunctionsManual.cpp
- func: matrix_exp_backward(Tensor self, Tensor grad) -> Tensor

# DEPRECATED: Use torch.aminmax instead
- func: _aminmax(Tensor self) -> (Tensor, Tensor)
  dispatch:
    CPU, CUDA: _aminmax_all
  autogen: _aminmax.out

# DEPRECATED: Use torch.aminmax instead
- func: _aminmax.dim(Tensor self, int dim, bool keepdim=False) -> (Tensor, Tensor)
  dispatch:
    CPU, CUDA: _aminmax
  autogen: _aminmax.dim_out

- func: aminmax(Tensor self, *, int? dim=None, bool keepdim=False) -> (Tensor min, Tensor max)
  device_check: NoCheck   # TensorIterator
  structured_delegate: aminmax.out
  variants: function, method

- func: aminmax.out(Tensor self, *, int? dim=None, bool keepdim=False, Tensor(a!) min, Tensor(b!) max) -> (Tensor(a!) min, Tensor(b!) max)
  device_check: NoCheck   # TensorIterator
  structured: True
  dispatch:
    CPU, CUDA: aminmax_out
    MPS: aminmax_out_mps

- func: _compute_linear_combination(Tensor input, Tensor coefficients) -> Tensor
  dispatch:
    CPU, CUDA: _compute_linear_combination

- func: _compute_linear_combination.out(Tensor input, Tensor coefficients, *, Tensor(a!) out) -> Tensor(a!)
  dispatch:
    CPU, CUDA: _compute_linear_combination_out

- func: max.dim(Tensor self, int dim, bool keepdim=False) -> (Tensor values, Tensor indices)
  device_check: NoCheck   # TensorIterator
  structured_delegate: max.dim_max
  variants: function, method
  dispatch:
    QuantizedCPU, QuantizedCUDA: qmax
  tags: core

- func: max.dim_max(Tensor self, int dim, bool keepdim=False, *, Tensor(a!) max, Tensor(b!) max_values) -> (Tensor(a!) values, Tensor(b!) indices)
  device_check: NoCheck   # TensorIterator
  structured: True
  precomputed:
  - dim -> int dim
  dispatch:
    CPU, CUDA: max_out
    MPS: max_out_mps

- func: max.names_dim(Tensor self, Dimname dim, bool keepdim=False) -> (Tensor values, Tensor indices)
  device_check: NoCheck   # TensorIterator
  variants: function, method

- func: max.names_dim_max(Tensor self, Dimname dim, bool keepdim=False, *, Tensor(a!) max, Tensor(b!) max_values) -> (Tensor(a!) values, Tensor(b!) indices)
  device_check: NoCheck   # TensorIterator

- func: value_selecting_reduction_backward(Tensor grad, int dim, Tensor indices, SymInt[] sizes, bool keepdim) -> Tensor
  variants: function
  device_check: NoCheck
  device_guard: False
  dispatch:
    CompositeImplicitAutograd: value_selecting_reduction_backward_symint
    NestedTensorCPU, NestedTensorCUDA: value_selecting_reduction_backward_nested_symint

- func: amax(Tensor self, int[1] dim=[], bool keepdim=False) -> Tensor
  variants: function, method
  structured_delegate: amax.out
  tags: core

- func: amax.out(Tensor self, int[1] dim=[], bool keepdim=False, *, Tensor(a!) out) -> Tensor(a!)
  structured: True
  dispatch:
    CPU, CUDA: amax_out
    MPS: amax_out_mps

# Return: (Tensor output, Tensor indices)
- func: max_pool1d_with_indices(Tensor self, int[1] kernel_size, int[1] stride=[], int[1] padding=0, int[1] dilation=1, bool ceil_mode=False) -> (Tensor, Tensor)

- func: max_pool1d(Tensor self, int[1] kernel_size, int[1] stride=[], int[1] padding=0, int[1] dilation=1, bool ceil_mode=False) -> Tensor

- func: max_pool2d(Tensor self, int[2] kernel_size, int[2] stride=[], int[2] padding=0, int[2] dilation=1, bool ceil_mode=False) -> Tensor
  dispatch:
    CompositeImplicitAutograd: max_pool2d
    MPS: mps_max_pool2d

- func: max_pool2d_backward(Tensor grad_output, Tensor self, int[2] kernel_size, int[2] stride=[], int[2] padding=0, int[2] dilation=1, bool ceil_mode=False) -> Tensor
  dispatch:
    MPS: mps_max_pool2d_backward
  autogen: max_pool2d_backward.out

- func: mkldnn_max_pool2d(Tensor self, int[2] kernel_size, int[2] stride=[], int[2] padding=0, int[2] dilation=1, bool ceil_mode=False) -> Tensor
  dispatch:
    MkldnnCPU: mkldnn_max_pool2d
  autogen: mkldnn_max_pool2d.out

- func: mkldnn_max_pool2d_backward(Tensor grad_output, Tensor output, Tensor input, int[2] kernel_size, int[2] stride=[], int[2] padding=0, int[2] dilation=1, bool ceil_mode=False) -> Tensor
  dispatch:
    MkldnnCPU: mkldnn_max_pool2d_backward
  autogen: mkldnn_max_pool2d_backward.out

- func: mkldnn_max_pool3d(Tensor self, int[3] kernel_size, int[3] stride=[], int[3] padding=0, int[3] dilation=1, bool ceil_mode=False) -> Tensor
  dispatch:
    MkldnnCPU: mkldnn_max_pool3d
  autogen: mkldnn_max_pool3d.out

- func: mkldnn_max_pool3d_backward(Tensor grad_output, Tensor output, Tensor input, int[3] kernel_size, int[3] stride=[], int[3] padding=0, int[3] dilation=1, bool ceil_mode=False) -> Tensor
  dispatch:
    MkldnnCPU: mkldnn_max_pool3d_backward
  autogen: mkldnn_max_pool3d_backward.out

- func: quantized_max_pool1d(Tensor self, int[1] kernel_size, int[1] stride=[], int[1] padding=0, int[1] dilation=1, bool ceil_mode=False) -> Tensor
  dispatch:
    QuantizedCPU: quantized_max_pool1d
  autogen: quantized_max_pool1d.out

- func: quantized_max_pool2d(Tensor self, int[2] kernel_size, int[2] stride=[], int[2] padding=0, int[2] dilation=1, bool ceil_mode=False) -> Tensor
  dispatch:
    QuantizedCPU: quantized_max_pool2d
    QuantizedCUDA: quantized_max_pool2d_cudnn
  autogen: quantized_max_pool2d.out

- func: quantized_max_pool3d(Tensor self, int[3] kernel_size, int[3] stride=[], int[3] padding=0, int[3] dilation=1, bool ceil_mode=False) -> Tensor
  dispatch:
    QuantizedCPU: quantized_max_pool3d
  autogen: quantized_max_pool3d.out

- func: max_pool3d(Tensor self, int[3] kernel_size, int[3] stride=[], int[3] padding=0, int[3] dilation=1, bool ceil_mode=False) -> Tensor

# The CPU and GPU dispatch variants are named weirdly here because otherwise there
# are namespacing issues in C++
- func: mean(Tensor self, *, ScalarType? dtype=None) -> Tensor
  device_check: NoCheck   # TensorIterator
  variants: function, method
  dispatch:
    CompositeExplicitAutograd: mean
  tags: core

# For normal naming convention this should be `mean.out`. However since we already have `mean.out` we have to rename this.
- func: mean.dtype_out(Tensor self, *, ScalarType? dtype=None, Tensor(a!) out) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  dispatch:
    CompositeExplicitAutograd: mean_dtype_out

- func: mean.dim(Tensor self, int[1]? dim, bool keepdim=False, *, ScalarType? dtype=None) -> Tensor
  structured_delegate: mean.out
  device_check: NoCheck   # TensorIterator
  variants: function, method
  dispatch:
    QuantizedCPU: mean_quantized_cpu
  tags: core

- func: mean.out(Tensor self, int[1]? dim, bool keepdim=False, *, ScalarType? dtype=None, Tensor(a!) out) -> Tensor(a!)
  structured: True
  device_check: NoCheck   # TensorIterator
  dispatch:
    CPU, CUDA: mean_out
    MPS: mean_out_mps
    QuantizedCPU: mean_out_quantized_cpu

- func: mean.names_dim(Tensor self, Dimname[1] dim, bool keepdim=False, *, ScalarType? dtype=None) -> Tensor
  device_check: NoCheck   # TensorIterator
  variants: function, method

- func: mean.names_out(Tensor self, Dimname[1] dim, bool keepdim=False, *, ScalarType? dtype=None, Tensor(a!) out) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator

- func: nanmean(Tensor self, int[1]? dim=None, bool keepdim=False, *, ScalarType? dtype=None) -> Tensor
  device_check: NoCheck   # Composite
  variants: function, method

- func: nanmean.out(Tensor self, int[1]? dim=None, bool keepdim=False, *, ScalarType? dtype=None, Tensor(a!) out) -> Tensor(a!)
  device_check: NoCheck   # Composite

- func: median(Tensor self) -> Tensor
  variants: function, method
  dispatch:
    CPU: median_cpu
    CUDA: median_cuda
    MPS: median_mps
  autogen: median.out

- func: median.dim(Tensor self, int dim, bool keepdim=False) -> (Tensor values, Tensor indices)
  variants: function, method
  dispatch:
    CompositeExplicitAutograd: median

- func: median.dim_values(Tensor self, int dim, bool keepdim=False, *, Tensor(a!) values, Tensor(b!) indices) -> (Tensor(a!) values, Tensor(b!) indices)
  dispatch:
    CPU: median_out_cpu
    CUDA: median_out_cuda
    MPS: median_out_mps

- func: median.names_dim(Tensor self, Dimname dim, bool keepdim=False) -> (Tensor values, Tensor indices)
  variants: function, method

- func: median.names_dim_values(Tensor self, Dimname dim, bool keepdim=False, *, Tensor(a!) values, Tensor(b!) indices) -> (Tensor(a!) values, Tensor(b!) indices)

- func: nanmedian(Tensor self) -> Tensor
  variants: function, method
  dispatch:
    CPU: nanmedian_cpu
    CUDA: nanmedian_cuda
  autogen: nanmedian.out

- func: nanmedian.dim(Tensor self, int dim, bool keepdim=False) -> (Tensor values, Tensor indices)
  variants: function, method
  dispatch:
    CompositeExplicitAutograd: nanmedian

- func: nanmedian.dim_values(Tensor self, int dim, bool keepdim=False, *, Tensor(a!) values, Tensor(b!) indices) -> (Tensor(a!) values, Tensor(b!) indices)
  dispatch:
    CPU: nanmedian_out_cpu
    CUDA: nanmedian_out_cuda

- func: nanmedian.names_dim(Tensor self, Dimname dim, bool keepdim=False) -> (Tensor values, Tensor indices)
  variants: function, method

- func: nanmedian.names_dim_values(Tensor self, Dimname dim, bool keepdim=False, *, Tensor(a!) values, Tensor(b!) indices) -> (Tensor(a!) values, Tensor(b!) indices)

- func: min.dim(Tensor self, int dim, bool keepdim=False) -> (Tensor values, Tensor indices)
  device_check: NoCheck   # TensorIterator
  structured_delegate: min.dim_min
  variants: function, method
  dispatch:
    QuantizedCPU, QuantizedCUDA: qmin
  tags: core

- func: min.dim_min(Tensor self, int dim, bool keepdim=False, *, Tensor(a!) min, Tensor(b!) min_indices) -> (Tensor(a!) values, Tensor(b!) indices)
  device_check: NoCheck   # TensorIterator
  structured: True
  precomputed:
  - dim -> int dim
  dispatch:
    CPU, CUDA: min_out
    MPS: min_out_mps

- func: min.names_dim(Tensor self, Dimname dim, bool keepdim=False) -> (Tensor values, Tensor indices)
  device_check: NoCheck   # TensorIterator
  variants: function, method

- func: min.names_dim_min(Tensor self, Dimname dim, bool keepdim=False, *, Tensor(a!) min, Tensor(b!) min_indices) -> (Tensor(a!) values, Tensor(b!) indices)
  device_check: NoCheck   # TensorIterator

- func: amin(Tensor self, int[1] dim=[], bool keepdim=False) -> Tensor
  variants: function, method
  structured_delegate: amin.out
  tags: core

- func: amin.out(Tensor self, int[1] dim=[], bool keepdim=False, *, Tensor(a!) out) -> Tensor(a!)
  structured: True
  dispatch:
    CPU, CUDA: amin_out
    MPS: amin_out_mps

# TODO: Add this function to MPS dispatch key so that we avoid declaring it in
# native_functions.yaml
# https://github.com/pytorch/pytorch/issues/77394
- func: _mps_convolution(Tensor self, Tensor weight, Tensor? bias, SymInt[] padding, SymInt[] stride, SymInt[] dilation, SymInt groups) -> Tensor
  dispatch:
    MPS: _mps_convolution
  autogen: _mps_convolution.out

- func: mps_convolution_backward(Tensor self, Tensor grad_output, Tensor weight, SymInt[] padding, SymInt[] stride, SymInt[] dilation, SymInt groups, bool[3] output_mask) -> (Tensor, Tensor, Tensor)
  dispatch:
    MPS: mps_convolution_backward
  autogen: mps_convolution_backward.out

- func: mkldnn_convolution(Tensor self, Tensor weight, Tensor? bias, SymInt[] padding, SymInt[] stride, SymInt[] dilation, SymInt groups) -> Tensor
  dispatch:
    CompositeExplicitAutograd: mkldnn_convolution
  autogen: mkldnn_convolution.out

- func: mkldnn_rnn_layer(Tensor input, Tensor weight0, Tensor weight1, Tensor weight2, Tensor weight3, Tensor hx_, Tensor cx_, bool reverse, int[] batch_sizes, int mode, int hidden_size, int num_layers, bool has_biases, bool bidirectional, bool batch_first, bool train) -> (Tensor, Tensor, Tensor, Tensor)
  dispatch:
    CPU: mkldnn_rnn_layer
    MkldnnCPU: mkldnn_rnn_layer
  autogen: mkldnn_rnn_layer.out

- func: mkldnn_rnn_layer_backward(Tensor input, Tensor weight1, Tensor weight2, Tensor weight3, Tensor weight4, Tensor hx_, Tensor cx_tmp, Tensor output, Tensor hy_, Tensor cy_, Tensor? grad_output, Tensor? grad_hy, Tensor? grad_cy, bool reverse, int mode, int hidden_size, int num_layers, bool has_biases, bool train, bool bidirectional, int[] batch_sizes, bool batch_first, Tensor workspace) -> (Tensor, Tensor, Tensor, Tensor, Tensor, Tensor, Tensor)
  dispatch:
    CPU: mkldnn_rnn_layer_backward
  autogen: mkldnn_rnn_layer_backward.out

- func: miopen_batch_norm(Tensor input, Tensor weight, Tensor? bias, Tensor? running_mean, Tensor? running_var, bool training, float exponential_average_factor, float epsilon) -> (Tensor, Tensor, Tensor)
  dispatch:
    CUDA: miopen_batch_norm
  autogen: miopen_batch_norm.out

- func: miopen_batch_norm_backward(Tensor input, Tensor grad_output, Tensor weight, Tensor? running_mean, Tensor? running_var, Tensor? save_mean, Tensor? save_var, float epsilon) -> (Tensor, Tensor, Tensor)
  dispatch:
    CUDA: miopen_batch_norm_backward
  autogen: miopen_batch_norm_backward.out

- func: miopen_convolution(Tensor self, Tensor weight, Tensor? bias, SymInt[] padding, SymInt[] stride, SymInt[] dilation, SymInt groups, bool benchmark, bool deterministic) -> Tensor
  dispatch:
    CUDA: miopen_convolution
  autogen: miopen_convolution.out

- func: miopen_convolution_transpose(Tensor self, Tensor weight, Tensor? bias, SymInt[] padding, SymInt[] output_padding, SymInt[] stride, SymInt[] dilation, SymInt groups, bool benchmark, bool deterministic) -> Tensor
  dispatch:
    CUDA: miopen_convolution_transpose
  autogen: miopen_convolution_transpose.out

- func: miopen_depthwise_convolution(Tensor self, Tensor weight, Tensor? bias, SymInt[] padding, SymInt[] stride, SymInt[] dilation, SymInt groups, bool benchmark, bool deterministic) -> Tensor
  dispatch:
    CUDA: miopen_depthwise_convolution
  autogen: miopen_depthwise_convolution.out

- func: miopen_convolution_relu(Tensor self, Tensor weight, Tensor? bias, SymInt[] stride, SymInt[] padding, SymInt[] dilation, SymInt groups) -> Tensor
  dispatch:
    CUDA: miopen_convolution_relu

- func: miopen_convolution_add_relu(Tensor self, Tensor weight, Tensor z, Scalar? alpha, Tensor? bias, SymInt[] stride, SymInt[] padding, SymInt[] dilation, SymInt groups) -> Tensor
  dispatch:
    CUDA: miopen_convolution_add_relu

- func: miopen_rnn(Tensor input, Tensor[] weight, int weight_stride0, Tensor hx, Tensor? cx, int mode, int hidden_size, int num_layers, bool batch_first, float dropout, bool train, bool bidirectional, int[] batch_sizes, Tensor? dropout_state) -> (Tensor, Tensor, Tensor, Tensor, Tensor)
  dispatch:
    CUDA: miopen_rnn
  autogen: miopen_rnn.out
  tags: nondeterministic_seeded


- func: miopen_rnn_backward(Tensor input, Tensor[] weight, int weight_stride0, Tensor weight_buf, Tensor hx, Tensor? cx, Tensor output, Tensor? grad_output, Tensor? grad_hy, Tensor? grad_cy, int mode, int hidden_size, int num_layers, bool batch_first, float dropout, bool train, bool bidirectional, int[] batch_sizes, Tensor? dropout_state, Tensor reserve, bool[4] output_mask) -> (Tensor, Tensor, Tensor, Tensor[])
  dispatch:
    CUDA: miopen_rnn_backward
  autogen: miopen_rnn_backward.out

- func: mm(Tensor self, Tensor mat2) -> Tensor
  structured_delegate: mm.out
  variants: function, method
  dispatch:
    SparseCPU, SparseCUDA: _sparse_mm
    SparseCsrCPU, SparseCsrCUDA, SparseCsrMeta: _sparse_csr_mm
  tags: core

- func: mm.out(Tensor self, Tensor mat2, *, Tensor(a!) out) -> Tensor(a!)
  structured: True
  dispatch:
    CPU: mm_out_cpu
    CUDA: mm_out_cuda
    MPS: mm_out_mps
    XPU: mm_out_xpu
    SparseCPU, SparseCUDA: _sparse_mm_out
    SparseCsrCPU, SparseCsrCUDA, SparseCsrMeta: _sparse_csr_mm_out

- func: _int_mm(Tensor self, Tensor mat2) -> Tensor
  dispatch:
    CPU: _int_mm_cpu
    CUDA: _int_mm_cuda

- func: _int_mm.out(Tensor self, Tensor mat2, *, Tensor(a!) out) -> Tensor(a!)
  dispatch:
    CPU: _int_mm_out_cpu
    CUDA: _int_mm_out_cuda

- func: _convert_weight_to_int4pack(Tensor self, int innerKTiles) -> Tensor
  dispatch:
    CUDA: _convert_weight_to_int4pack_cuda
    MPS: _convert_weight_to_int4pack_mps

- func: _weight_int4pack_mm(Tensor self, Tensor mat2, int qGroupSize, Tensor qScaleAndZeros) -> Tensor
  dispatch:
    MPS: _weight_int4pack_mm_mps
    CUDA: _weight_int4pack_mm_cuda

# Split int4 pack weight between cpu and other devices due to
# https://github.com/pytorch/ao/issues/1117#issuecomment-2451252756.
- func: _convert_weight_to_int4pack_for_cpu(Tensor self, int innerKTiles) -> Tensor
  dispatch:
    CPU: _convert_weight_to_int4pack_cpu

- func: _weight_int4pack_mm_for_cpu(Tensor self, Tensor mat2, int qGroupSize, Tensor qScaleAndZeros) -> Tensor
  dispatch:
    CPU: _weight_int4pack_mm_cpu

- func: _dyn_quant_pack_4bit_weight(Tensor weights, Tensor scales_zeros, Tensor? bias, int block_size, int in_features, int out_features) -> Tensor
  dispatch:
    CPU: _dyn_quant_pack_4bit_weight_cpu

- func: _dyn_quant_matmul_4bit(Tensor inp, Tensor packed_weights, int block_size, int in_features, int out_features) -> Tensor
  dispatch:
    CPU: _dyn_quant_matmul_4bit_cpu

- func: _weight_int8pack_mm(Tensor self, Tensor mat2, Tensor scales) -> Tensor
  dispatch:
    CPU: _weight_int8pack_mm_cpu
    MPS: _weight_int8pack_mm_mps

- func: _sparse_mm(Tensor sparse, Tensor dense) -> Tensor
  python_module: sparse

- func: _sparse_mm.reduce(Tensor sparse, Tensor dense, str reduce) -> Tensor
  python_module: sparse

- func: _sparse_sparse_matmul(Tensor self, Tensor other) -> Tensor
  dispatch:
    SparseCPU: sparse_sparse_matmul_cpu
    SparseCUDA: sparse_sparse_matmul_cuda
  autogen: _sparse_sparse_matmul.out

- func: mode(Tensor self, int dim=-1, bool keepdim=False) -> (Tensor values, Tensor indices)
  variants: function, method
  dispatch:
    CPU, CUDA: mode

- func: mode.values(Tensor self, int dim=-1, bool keepdim=False, *, Tensor(a!) values, Tensor(b!) indices) -> (Tensor(a!) values, Tensor(b!) indices)
  dispatch:
    CompositeExplicitAutograd: mode_out

- func: mode.dimname(Tensor self, Dimname dim, bool keepdim=False) -> (Tensor values, Tensor indices)
  variants: function, method

- func: mode.dimname_out(Tensor self, Dimname dim, bool keepdim=False, *, Tensor(a!) values, Tensor(b!) indices) -> (Tensor(a!) values, Tensor(b!) indices)

- func: mul.Tensor(Tensor self, Tensor other) -> Tensor
  device_check: NoCheck   # TensorIterator
  structured_delegate: mul.out
  variants: function, method
  dispatch:
    SparseCPU, SparseCUDA: mul_sparse
    SparseCsrCPU, SparseCsrCUDA, SparseCsrMeta: mul_sparse_csr
    MkldnnCPU: mkldnn_mul
    ZeroTensor: mul_zerotensor
    NestedTensorCPU, NestedTensorCUDA: NestedTensor_mul_Tensor
  tags: [core, pointwise]

- func: mul_.Tensor(Tensor(a!) self, Tensor other) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  structured_delegate: mul.out
  variants: method
  dispatch:
    SparseCPU, SparseCUDA: mul_sparse_
    SparseCsrCPU, SparseCsrCUDA, SparseCsrMeta: mul_sparse_csr_
    MkldnnCPU: mkldnn_mul_
    NestedTensorCPU, NestedTensorCUDA: NestedTensor_mul__Tensor
  tags: pointwise

- func: mul.out(Tensor self, Tensor other, *, Tensor(a!) out) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  structured: True
  structured_inherits: TensorIteratorBase
  dispatch:
    CPU, CUDA: mul_out
    MPS: mul_out_mps
    SparseCPU: mul_out_sparse_cpu
    SparseCUDA: mul_out_sparse_cuda
    SparseCsrCPU, SparseCsrCUDA, SparseCsrMeta: mul_out_sparse_csr
    MkldnnCPU: mkldnn_mul_out
  tags: pointwise
  # For C++ only, until we have conversion from C++ numbers to Tensor

- func: mul.Scalar(Tensor self, Scalar other) -> Tensor
  device_check: NoCheck   # TensorIterator
  variants: function, method
  dispatch:
    CompositeExplicitAutograd: mul
    SparseCsrCPU, SparseCsrCUDA, SparseCsrMeta: mul_scalar_sparse_csr
    NestedTensorCPU, NestedTensorCUDA: NestedTensor_mul_Scalar
  tags: [core, pointwise]

- func: mul_.Scalar(Tensor(a!) self, Scalar other) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  variants: method
  dispatch:
    CompositeExplicitAutograd: mul_
    SparseCsrCPU, SparseCsrCUDA, SparseCsrMeta: mul__scalar_sparse_csr
    NestedTensorCPU, NestedTensorCUDA: NestedTensor_mul__Scalar
  autogen: mul.Scalar_out
  tags: pointwise
# multiply, alias for mul

- func: multiply.Tensor(Tensor self, Tensor other) -> Tensor
  variants: function, method

- func: multiply_.Tensor(Tensor(a!) self, Tensor other) -> Tensor(a!)
  variants: method

- func: multiply.out(Tensor self, Tensor other, *, Tensor(a!) out) -> Tensor(a!)

- func: multiply.Scalar(Tensor self, Scalar other) -> Tensor
  variants: function, method

- func: multiply_.Scalar(Tensor(a!) self, Scalar other) -> Tensor(a!)
  variants: method

- func: mv(Tensor self, Tensor vec) -> Tensor
  variants: function, method
  dispatch:
    CompositeExplicitAutograd: mv
    SparseCPU, SparseCUDA: mv_sparse

- func: mv.out(Tensor self, Tensor vec, *, Tensor(a!) out) -> Tensor(a!)
  dispatch:
    CompositeExplicitAutograd: mv_out

- func: mvlgamma.out(Tensor self, int p, *, Tensor(a!) out) -> Tensor(a!)
  dispatch:
    CPU, CUDA: mvlgamma_out
  tags: pointwise

- func: mvlgamma(Tensor self, int p) -> Tensor
  device_check: NoCheck   # TensorIterator
  variants: function, method
  dispatch:
    CompositeExplicitAutograd: mvlgamma
  tags: pointwise

- func: mvlgamma_(Tensor(a!) self, int p) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  variants: method
  dispatch:
    CompositeExplicitAutograd: mvlgamma_
  tags: pointwise

- func: narrow_copy(Tensor self, int dim, SymInt start, SymInt length) -> Tensor
  variants: function, method
  dispatch:
    CPU: narrow_copy_dense_cpu
    SparseCPU, SparseCUDA: narrow_copy_sparse
    CompositeExplicitAutogradNonFunctional: narrow_copy_dense_symint
  tags: view_copy

- func: narrow_copy.out(Tensor self, int dim, SymInt start, SymInt length, *, Tensor(a!) out) -> Tensor(a!)
  dispatch:
    CPU: narrow_copy_dense_cpu_out

- func: narrow(Tensor(a) self, int dim, SymInt start, SymInt length) -> Tensor(a)
  variants: function, method
  device_check: NoCheck
  device_guard: False
  dispatch:
    CompositeImplicitAutograd: narrow_symint
    NestedTensorCPU, NestedTensorCUDA: narrow_nested_symint

- func: narrow.Tensor(Tensor(a) self, int dim, Tensor start, SymInt length) -> Tensor(a)
  variants: function, method
  device_check: NoCheck
  device_guard: False
  dispatch:
    CompositeImplicitAutograd: narrow_tensor_symint

- func: native_batch_norm(Tensor input, Tensor? weight, Tensor? bias, Tensor? running_mean, Tensor? running_var, bool training, float momentum, float eps) -> (Tensor, Tensor, Tensor)
  dispatch:
    CPU: batch_norm_cpu
    CUDA: batch_norm_cuda
    MPS: batch_norm_mps
    MkldnnCPU: mkldnn_batch_norm

- func: native_batch_norm.out(Tensor input, Tensor? weight, Tensor? bias, Tensor? running_mean, Tensor? running_var, bool training, float momentum, float eps, *, Tensor(a!) out, Tensor(b!) save_mean, Tensor(c!) save_invstd) -> (Tensor(a!), Tensor(b!), Tensor(c!))
  dispatch:
    CUDA: batch_norm_cuda_out
    MPS: batch_norm_mps_out
    CPU: batch_norm_cpu_out

# TODO: In 2 weeks, we should make native_batch_norm composite implicit so that this correct schema percolates correctly through our dispatching
- func: _native_batch_norm_legit(Tensor input, Tensor? weight, Tensor? bias, Tensor(a!) running_mean, Tensor(b!) running_var, bool training, float momentum, float eps) -> (Tensor, Tensor, Tensor)
  dispatch:
    CPU: _batch_norm_legit_cpu
    CUDA: _batch_norm_legit_cuda
    MPS: _batch_norm_legit_mps
    MkldnnCPU: _mkldnn_batch_norm_legit
  autogen: _native_batch_norm_legit_functional
  tags: core

# HACK: identical to _native_batch_norm_legit, but training is known to be False,
# So we known that running stats will not be mutated.
# The real fix here is batch norm consolidation.
- func: _native_batch_norm_legit_no_training(Tensor input, Tensor? weight, Tensor? bias, Tensor running_mean, Tensor running_var, float momentum, float eps) -> (Tensor, Tensor, Tensor)
  dispatch:
    CompositeExplicitAutograd: _batch_norm_legit_no_training
  autogen: _native_batch_norm_legit_no_training.out
  tags: core

- func: _native_batch_norm_legit.out(Tensor input, Tensor? weight, Tensor? bias, Tensor(a!) running_mean, Tensor(b!) running_var, bool training, float momentum, float eps, *, Tensor(d!) out, Tensor(e!) save_mean, Tensor(f!) save_invstd) -> (Tensor(d!), Tensor(e!), Tensor(f!))
  dispatch:
    CPU: _batch_norm_legit_cpu_out
    CUDA: _batch_norm_legit_cuda_out
    MPS: _batch_norm_legit_mps_out

- func: _native_batch_norm_legit.no_stats(Tensor input, Tensor? weight, Tensor? bias, bool training, float momentum, float eps) -> (Tensor, Tensor, Tensor)
  dispatch:
    CPU: _batch_norm_legit_no_stats_cpu
    CUDA: _batch_norm_legit_no_stats_cuda
    MPS: _batch_norm_legit_no_stats_mps
    MkldnnCPU: _mkldnn_batch_norm_legit_no_stats
  tags: core

- func: _native_batch_norm_legit.no_stats_out(Tensor input, Tensor? weight, Tensor? bias, bool training, float momentum, float eps, *, Tensor(a!) out, Tensor(b!) save_mean, Tensor(c!) save_invstd) -> (Tensor(a!), Tensor(b!), Tensor(c!))
  dispatch:
    CPU: _batch_norm_legit_no_stats_cpu_out
    CUDA: _batch_norm_legit_no_stats_cuda_out
    MPS: _batch_norm_legit_no_stats_mps_out

- func: batch_norm_stats(Tensor input, float eps) -> (Tensor, Tensor)
  dispatch:
    CUDA: batch_norm_stats_cuda
  autogen: batch_norm_stats.out

- func: batch_norm_elemt(Tensor input, Tensor? weight, Tensor? bias, Tensor mean, Tensor invstd, float eps) -> Tensor
  dispatch:
    CUDA: batch_norm_elemt_cuda

- func: batch_norm_elemt.out(Tensor input, Tensor? weight, Tensor? bias, Tensor mean, Tensor invstd, float eps, *, Tensor(a!) out) -> Tensor(a!)
  dispatch:
    CUDA: batch_norm_elemt_cuda_out

# for backward compatibility
- func: batch_norm_gather_stats(Tensor input, Tensor mean, Tensor invstd, Tensor? running_mean, Tensor? running_var, float momentum, float eps, int count) -> (Tensor, Tensor)
  dispatch:
    CUDA: batch_norm_gather_stats_cuda
  autogen: batch_norm_gather_stats.out

- func: batch_norm_gather_stats_with_counts(Tensor input, Tensor mean, Tensor invstd, Tensor? running_mean, Tensor? running_var, float momentum, float eps, Tensor counts) -> (Tensor, Tensor)
  dispatch:
    CUDA: batch_norm_gather_stats_with_counts_cuda
  autogen: batch_norm_gather_stats_with_counts.out

- func: native_batch_norm_backward(Tensor grad_out, Tensor input, Tensor? weight, Tensor? running_mean, Tensor? running_var, Tensor? save_mean, Tensor? save_invstd, bool train, float eps, bool[3] output_mask) -> (Tensor, Tensor, Tensor)
  dispatch:
    CPU: batch_norm_backward_cpu
    CUDA: batch_norm_backward_cuda
    MPS: batch_norm_backward_mps
    MkldnnCPU: mkldnn_batch_norm_backward
  autogen: native_batch_norm_backward.out

- func: batch_norm_backward_reduce(Tensor grad_out, Tensor input, Tensor mean, Tensor invstd, Tensor? weight, bool input_g, bool weight_g, bool bias_g) -> (Tensor, Tensor, Tensor, Tensor)
  dispatch:
    CUDA: batch_norm_backward_reduce_cuda
  autogen: batch_norm_backward_reduce.out

- func: batch_norm_backward_elemt(Tensor grad_out, Tensor input, Tensor mean, Tensor invstd, Tensor? weight, Tensor sum_dy, Tensor sum_dy_xmu, Tensor count) -> Tensor
  dispatch:
    CUDA: batch_norm_backward_elemt_cuda
  autogen: batch_norm_backward_elemt.out

- func: batch_norm_update_stats(Tensor input, Tensor? running_mean, Tensor? running_var, float momentum) -> (Tensor, Tensor)
  dispatch:
    CPU: batch_norm_update_stats_cpu
    CUDA: batch_norm_update_stats_cuda
  autogen: batch_norm_update_stats.out

- func: is_vulkan_available() -> bool

- func: _nnpack_available() -> bool

- func: _nnpack_spatial_convolution(Tensor input, Tensor weight, Tensor? bias, SymInt[2] padding, SymInt[2] stride=1) -> Tensor
  variants: function
  dispatch:
    CompositeExplicitAutograd: _nnpack_spatial_convolution
  autogen: _nnpack_spatial_convolution.out

- func: ones.names(int[] size, *, Dimname[]? names, ScalarType? dtype=None, Layout? layout=None, Device? device=None, bool? pin_memory=None) -> Tensor
  device_check: NoCheck
  device_guard: False
  dispatch:
    CompositeExplicitAutograd: ones
  autogen: ones.names_out

- func: ones(SymInt[] size, *, ScalarType? dtype=None, Layout? layout=None, Device? device=None, bool? pin_memory=None) -> Tensor
  dispatch:
    CompositeExplicitAutograd: ones

- func: ones.out(SymInt[] size, *, Tensor(a!) out) -> Tensor(a!)
  dispatch:
    CompositeExplicitAutograd: ones_out

- func: ones_like(Tensor self, *, ScalarType? dtype=None, Layout? layout=None, Device? device=None, bool? pin_memory=None, MemoryFormat? memory_format=None) -> Tensor
  dispatch:
    # NB: Although this composite mutates on the inside, it is
    # non-differentiable so NonFunctional doesn`
  - `t support boolean indexing, to avoid dynamic output shapes
- func: _unsafe_masked_index(Tensor self, Tensor mask, Tensor?[] indices, Scalar fill) -> Tensor
  variants: function
  dispatch:
    CompositeExplicitAutograd: _unsafe_masked_index

- func: _unsafe_masked_index_put_accumulate(Tensor self, Tensor mask, Tensor?[] indices, Tensor values) -> Tensor
  variants: function
  dispatch:
    CompositeExplicitAutograd: _unsafe_masked_index_put_accumulate

- func: index_copy.out(Tensor self, int dim, Tensor index, Tensor source, *, Tensor(a!) out) -> Tensor(a!)
  structured: True
  variants: function
  precomputed:
  - dim -> int dim
  dispatch:
    CPU, CUDA: index_copy_out

- func: index_copy_(Tensor(a!) self, int dim, Tensor index, Tensor source) -> Tensor(a!)
  variants: method
  structured_delegate: index_copy.out

- func: index_copy(Tensor self, int dim, Tensor index, Tensor source) -> Tensor
  variants: function, method
  structured_delegate: index_copy.out

- func: index_copy_.dimname(Tensor(a!) self, Dimname dim, Tensor index, Tensor source) -> Tensor(a!)
  variants: method

- func: index_copy.dimname(Tensor self, Dimname dim, Tensor index, Tensor source) -> Tensor
  variants: function, method

- func: index_put_(Tensor(a!) self, Tensor?[] indices, Tensor values, bool accumulate=False) -> Tensor(a!)
  device_check: NoCheck   # delegate to _index_put_impl_, which leverages TensorIterator
  variants: function, method
  dispatch:
    CompositeExplicitAutograd: index_put_
  autogen: index_put.out
  # NB: The following functions are declared in aten/src/ATen/templates/TensorBody.h and defined in aten/src/ATen/TensorIndexing.cpp:
  # - Tensor & Tensor::index_put_(ArrayRef<TensorIndex> indices, Tensor const & rhs)
  # - Tensor & Tensor::index_put_(ArrayRef<TensorIndex> indices, Scalar v)
  # - Tensor & Tensor::index_put_(std::initializer_list<TensorIndex> indices, Tensor const & rhs)
  # - Tensor & Tensor::index_put_(std::initializer_list<TensorIndex> indices, Scalar v)

- func: index_put(Tensor self, Tensor?[] indices, Tensor values, bool accumulate=False) -> Tensor
  device_check: NoCheck   # delegate to _index_put_impl_ after clone, which leverages TensorIterator
  variants: function, method
  dispatch:
    CompositeExplicitAutograd: index_put
  tags: core

- func: _unsafe_index_put(Tensor self, Tensor?[] indices, Tensor values, bool accumulate=False) -> Tensor
  device_check: NoCheck   # delegate to _index_put_impl_ after clone, which leverages TensorIterator
  variants: function
  dispatch:
    CompositeExplicitAutograd: _unsafe_index_put

- func: _index_put_impl_(Tensor(a!) self, Tensor?[] indices, Tensor values, bool accumulate=False, bool unsafe=False) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  variants: function
  dispatch:
    CPU, CUDA, MPS: _index_put_impl_
    QuantizedCPU: _index_put_impl_quantized_cpu_
    QuantizedCUDA: _index_put_impl_quantized_cuda_
  autogen: _index_put_impl, _index_put_impl.out

- func: instance_norm(Tensor input, Tensor? weight, Tensor? bias, Tensor? running_mean, Tensor? running_var, bool use_input_stats, float momentum, float eps, bool cudnn_enabled) -> Tensor
  variants: function

- func: isclose(Tensor self, Tensor other, float rtol=1e-05, float atol=1e-08, bool equal_nan=False) -> Tensor
  variants: function, method

- func: isin.Tensor_Tensor_out(Tensor elements, Tensor test_elements, *, bool assume_unique=False, bool invert=False, Tensor(a!) out) -> Tensor(a!)
  variants: function
  structured: True
  dispatch:
    CPU, CUDA: isin_Tensor_Tensor_out
    MPS: isin_Tensor_Tensor_out_mps

- func: isin.Tensor_Tensor(Tensor elements, Tensor test_elements, *, bool assume_unique=False, bool invert=False) -> Tensor
  variants: function
  structured_delegate: isin.Tensor_Tensor_out

- func: isin.Tensor_Scalar_out(Tensor elements, Scalar test_element, *, bool assume_unique=False, bool invert=False, Tensor(a!) out) -> Tensor(a!)
  variants: function
  structured: True
  dispatch:
    CPU, CUDA: isin_Tensor_Scalar_out

- func: isin.Tensor_Scalar(Tensor elements, Scalar test_element, *, bool assume_unique=False, bool invert=False) -> Tensor
  variants: function
  structured_delegate: isin.Tensor_Scalar_out

- func: isin.Scalar_Tensor_out(Scalar element, Tensor test_elements, *, bool assume_unique=False, bool invert=False, Tensor(a!) out) -> Tensor(a!)
  variants: function
  structured: True
  dispatch:
    CPU, CUDA: isin_Scalar_Tensor_out

- func: isin.Scalar_Tensor(Scalar element, Tensor test_elements, *, bool assume_unique=False, bool invert=False) -> Tensor
  variants: function
  structured_delegate: isin.Scalar_Tensor_out

- func: isnan(Tensor self) -> Tensor
  variants: function, method
  device_check: NoCheck
  device_guard: False
  dispatch:
    CPU, CUDA, MPS: isnan
    NestedTensorCPU, NestedTensorCUDA: NestedTensor_isnan
    SparseCPU, SparseCUDA: isnan_sparse
    SparseCsrCPU, SparseCsrCUDA, SparseCsrMeta: isnan_sparse_csr
  autogen: isnan.out
  tags: [core, pointwise]

- func: is_distributed(Tensor self) -> bool
  variants: function, method
  device_check: NoCheck
  device_guard: False

- func: is_floating_point(Tensor self) -> bool
  variants: function, method
  device_check: NoCheck
  device_guard: False
  manual_cpp_binding: True

- func: is_complex(Tensor self) -> bool
  variants: function, method
  device_check: NoCheck
  device_guard: False
  manual_cpp_binding: True

- func: is_conj(Tensor self) -> bool
  variants: function, method
  device_guard: False
  manual_cpp_binding: True

- func: _is_zerotensor(Tensor self) -> bool
  variants: function, method
  device_guard: False
  manual_cpp_binding: True

- func: is_neg(Tensor self) -> bool
  variants: function, method
  device_guard: False
  manual_cpp_binding: True

- func: isreal(Tensor self) -> Tensor
  variants: function, method

- func: is_nonzero(Tensor self) -> bool
  variants: function, method
  device_check: NoCheck
  device_guard: False

- func: is_same_size(Tensor self, Tensor other) -> bool
  variants: function, method
  device_check: NoCheck
  device_guard: False
  dispatch:
    NestedTensorCPU, NestedTensorCUDA: nested_is_same_size
    CompositeExplicitAutograd: is_same_size

- func: is_signed(Tensor self) -> bool
  variants: function, method
  device_check: NoCheck
  device_guard: False
  manual_cpp_binding: True

- func: is_inference(Tensor self) -> bool
  variants: function, method
  device_check: NoCheck
  device_guard: False
  manual_cpp_binding: True

- func: kl_div(Tensor self, Tensor target, int reduction=Mean, *, bool log_target=False) -> Tensor

- func: kron(Tensor self, Tensor other) -> Tensor
  variants: function, method

- func: kron.out(Tensor self, Tensor other, *, Tensor(a!) out) -> Tensor(a!)

- func: kthvalue(Tensor self, int k, int dim=-1, bool keepdim=False) -> (Tensor values, Tensor indices)
  variants: function, method
  dispatch:
    CompositeExplicitAutograd: kthvalue

- func: kthvalue.values(Tensor self, int k, int dim=-1, bool keepdim=False, *, Tensor(a!) values, Tensor(b!) indices) -> (Tensor(a!) values, Tensor(b!) indices)
  dispatch:
    CPU: kthvalue_out_cpu
    CUDA: kthvalue_out_cuda

- func: kthvalue.dimname(Tensor self, int k, Dimname dim, bool keepdim=False) -> (Tensor values, Tensor indices)
  variants: function, method

- func: kthvalue.dimname_out(Tensor self, int k, Dimname dim, bool keepdim=False, *, Tensor(a!) values, Tensor(b!) indices) -> (Tensor(a!) values, Tensor(b!) indices)

- func: layer_norm(Tensor input, SymInt[] normalized_shape, Tensor? weight=None, Tensor? bias=None, float eps=1e-05, bool cudnn_enable=True) -> Tensor
  dispatch:
    CompositeImplicitAutograd: layer_norm_symint

- func: native_layer_norm(Tensor input, SymInt[] normalized_shape, Tensor? weight, Tensor? bias, float eps) -> (Tensor, Tensor, Tensor)
  dispatch:
    CPU: layer_norm_cpu
    CUDA: layer_norm_cuda
    MPS: layer_norm_mps
    CompositeExplicitAutograd: math_native_layer_norm
    NestedTensorCPU, NestedTensorCUDA: nested_layer_norm
  autogen: native_layer_norm.out
  tags: core

- func: native_layer_norm_backward(Tensor grad_out, Tensor input, SymInt[] normalized_shape, Tensor mean, Tensor rstd, Tensor? weight, Tensor? bias, bool[3] output_mask) -> (Tensor, Tensor, Tensor)
  dispatch:
    CPU: layer_norm_backward_cpu
    CUDA: layer_norm_backward_cuda
    MPS: layer_norm_backward_mps
    NestedTensorCPU, NestedTensorCUDA: layer_norm_backward_nested
  autogen: native_layer_norm_backward.out
  tags: core

- func: rms_norm(Tensor input, SymInt[] normalized_shape, Tensor? weight=None, float? eps=None) -> Tensor
  dispatch:
    CompositeImplicitAutograd: rms_norm_symint

- func: nan_to_num(Tensor self, float? nan=None, float? posinf=None, float? neginf=None) -> Tensor
  variants: function, method
  dispatch:
    CompositeExplicitAutograd: nan_to_num
    SparseCPU, SparseCUDA: nan_to_num_sparse
  tags: pointwise

- func: nan_to_num_(Tensor(a!) self, float? nan=None, float? posinf=None, float? neginf=None) -> Tensor(a!)
  variants: function, method
  dispatch:
    CompositeExplicitAutograd: nan_to_num_
    SparseCPU, SparseCUDA: nan_to_num_sparse_
  tags: pointwise

- func: nan_to_num.out(Tensor self, float? nan=None, float? posinf=None, float? neginf=None, *, Tensor(a!) out) -> Tensor(a!)
  dispatch:
    CPU, CUDA: nan_to_num_out
    MPS: nan_to_num_out_mps
    SparseCPU, SparseCUDA: nan_to_num_sparse_out
  tags: pointwise

- func: linear(Tensor input, Tensor weight, Tensor? bias=None) -> Tensor
  python_module: nn
  dispatch:
    CompositeImplicitAutograd: linear
    NestedTensorCPU, NestedTensorCUDA: nested_linear
    MPS: _mps_linear

- func: linear_backward(Tensor self, Tensor grad_output, Tensor weight, bool[3] output_mask) -> (Tensor, Tensor, Tensor)
  dispatch:
    NestedTensorCPU, NestedTensorCUDA: nested_linear_backward
    MPS: mps_linear_backward
  autogen: linear_backward.out

- func: linear.out(Tensor input, Tensor weight, Tensor? bias=None, *, Tensor(a!) out) -> Tensor(a!)
  python_module: nn
  dispatch:
    CompositeExplicitAutograd: linear_out

- func: mkldnn_linear(Tensor self, Tensor weight, Tensor? bias=None) -> Tensor
  python_module: nn
  dispatch:
    MkldnnCPU: mkldnn_linear
  autogen: mkldnn_linear.out

- func: mkldnn_linear_backward_input(int[] input_size, Tensor grad_output, Tensor weight) -> Tensor
  dispatch:
    MkldnnCPU: mkldnn_linear_backward_input
  autogen: mkldnn_linear_backward_input.out

- func: mkldnn_linear_backward_weights(Tensor grad_output, Tensor input, Tensor weight, bool bias_defined) -> (Tensor, Tensor)
  dispatch:
    MkldnnCPU: mkldnn_linear_backward_weights
  autogen: mkldnn_linear_backward_weights.out

- func: mkldnn_linear_backward(Tensor self, Tensor grad_output, Tensor weight, bool[3] output_mask) -> (Tensor, Tensor, Tensor)
  dispatch:
    MkldnnCPU: mkldnn_linear_backward
  autogen: mkldnn_linear_backward.out

- func: _cslt_compress(Tensor input) -> Tensor
  dispatch:
    CUDA: _cslt_compress

- func: _cslt_sparse_mm(Tensor compressed_A, Tensor dense_B, Tensor? bias=None, Tensor? alpha=None, ScalarType? out_dtype=None, bool transpose_result=False, int alg_id=0, int split_k=1, bool split_k_one_kernel=True) -> Tensor
  dispatch:
    CUDA: _cslt_sparse_mm
  tags: needs_fixed_stride_order

- func: _cslt_sparse_mm_search(Tensor compressed_A, Tensor dense_B, Tensor? bias=None, Tensor? alpha=None, ScalarType? out_dtype=None, bool transpose_result=False) -> int
  dispatch:
    CUDA: _cslt_sparse_mm_search

- func: _sparse_semi_structured_tile(Tensor input, str algorithm=`
  - `t require gradient. Gradient for `grid` is always
# computed (only `output_mask[0]` is checked by the implementations).
- func: grid_sampler_3d_backward(Tensor grad_output, Tensor input, Tensor grid, int interpolation_mode, int padding_mode, bool align_corners, bool[2] output_mask) -> (Tensor, Tensor)
  dispatch:
    CPU: grid_sampler_3d_backward_cpu
    CUDA: grid_sampler_3d_backward_cuda
  autogen: grid_sampler_3d_backward.out

- func: hann_window(int window_length, *, ScalarType? dtype=None, Layout? layout=None, Device? device=None, bool? pin_memory=None) -> Tensor
  dispatch:
    CompositeExplicitAutograd: hann_window
  autogen: hann_window.out

- func: hann_window.periodic(int window_length, bool periodic, *, ScalarType? dtype=None, Layout? layout=None, Device? device=None, bool? pin_memory=None) -> Tensor
  dispatch:
    CompositeExplicitAutograd: hann_window
  autogen: hann_window.periodic_out

- func: hamming_window(int window_length, *, ScalarType? dtype=None, Layout? layout=None, Device? device=None, bool? pin_memory=None) -> Tensor
  dispatch:
    CompositeExplicitAutograd: hamming_window
  autogen: hamming_window.out

- func: hamming_window.periodic(int window_length, bool periodic, *, ScalarType? dtype=None, Layout? layout=None, Device? device=None, bool? pin_memory=None) -> Tensor
  dispatch:
    CompositeExplicitAutograd: hamming_window
  autogen: hamming_window.periodic_out

- func: hamming_window.periodic_alpha(int window_length, bool periodic, float alpha, *, ScalarType? dtype=None, Layout? layout=None, Device? device=None, bool? pin_memory=None) -> Tensor
  dispatch:
    CompositeExplicitAutograd: hamming_window
  autogen: hamming_window.periodic_alpha_out

- func: hamming_window.periodic_alpha_beta(int window_length, bool periodic, float alpha, float beta, *, ScalarType? dtype=None, Layout? layout=None, Device? device=None, bool? pin_memory=None) -> Tensor
  dispatch:
    CompositeExplicitAutograd: hamming_window
  autogen: hamming_window.periodic_alpha_beta_out

- func: kaiser_window(int window_length, *, ScalarType? dtype=None, Layout? layout=None, Device? device=None, bool? pin_memory=None) -> Tensor
  dispatch:
    CompositeExplicitAutograd: kaiser_window
  autogen: kaiser_window.out

- func: kaiser_window.periodic(int window_length, bool periodic, *, ScalarType? dtype=None, Layout? layout=None, Device? device=None, bool? pin_memory=None) -> Tensor
  dispatch:
    CompositeExplicitAutograd: kaiser_window
  autogen: kaiser_window.periodic_out

- func: kaiser_window.beta(int window_length, bool periodic, float beta, *, ScalarType? dtype=None, Layout? layout=None, Device? device=None, bool? pin_memory=None) -> Tensor
  dispatch:
    CompositeExplicitAutograd: kaiser_window
  autogen: kaiser_window.beta_out

- func: hinge_embedding_loss(Tensor self, Tensor target, float margin=1.0, int reduction=Mean) -> Tensor

- func: group_norm(Tensor input, int num_groups, Tensor? weight=None, Tensor? bias=None, float eps=1e-05, bool cudnn_enabled=True) -> Tensor

- func: native_group_norm(Tensor input, Tensor? weight, Tensor? bias, SymInt N, SymInt C, SymInt HxW, int group, float eps) -> (Tensor, Tensor, Tensor)
  dispatch:
    CPU, CUDA: native_group_norm
    CompositeExplicitAutograd: math_group_norm
  autogen: native_group_norm.out
  tags: core

- func: native_group_norm_backward(Tensor grad_out, Tensor input, Tensor mean, Tensor rstd, Tensor? weight, SymInt N, SymInt C, SymInt HxW, int group, bool[3] output_mask) -> (Tensor, Tensor, Tensor)
  dispatch:
    CPU, CUDA: native_group_norm_backward
  autogen: native_group_norm_backward.out
  tags: core

# Real to complex forward FFT
- func: _fft_r2c(Tensor self, int[] dim, int normalization, bool onesided) -> Tensor
  variants: function
  dispatch:
    CPU: _fft_r2c_mkl
    CUDA: _fft_r2c_cufft
    MPS: _fft_r2c_mps
  tags: core

- func: _fft_r2c.out(Tensor self, int[] dim, int normalization, bool onesided, *, Tensor(a!) out) -> Tensor(a!)
  variants: function
  dispatch:
    CPU: _fft_r2c_mkl_out
    CUDA: _fft_r2c_cufft_out
    MPS: _fft_r2c_mps_out

# Complex to real inverse FFT
- func: _fft_c2r(Tensor self, int[] dim, int normalization, SymInt last_dim_size) -> Tensor
  variants: function
  dispatch:
    CPU: _fft_c2r_mkl
    CUDA: _fft_c2r_cufft
    MPS: _fft_c2r_mps

- func: _fft_c2r.out(Tensor self, int[] dim, int normalization, SymInt last_dim_size, *, Tensor(a!) out) -> Tensor(a!)
  variants: function
  dispatch:
    CPU: _fft_c2r_mkl_out
    CUDA: _fft_c2r_cufft_out
    MPS: _fft_c2r_mps_out

# Standard complex to complex FFT (forward or backward)
- func: _fft_c2c(Tensor self, SymInt[] dim, int normalization, bool forward) -> Tensor
  variants: function
  dispatch:
    CPU: _fft_c2c_mkl
    CUDA: _fft_c2c_cufft
    MPS: _fft_c2c_mps

- func: _fft_c2c.out(Tensor self, SymInt[] dim, int normalization, bool forward, *, Tensor(a!) out) -> Tensor(a!)
  variants: function
  dispatch:
    CPU: _fft_c2c_mkl_out
    CUDA: _fft_c2c_cufft_out
    MPS: _fft_c2c_mps_out

- func: _validate_compressed_sparse_indices(bool is_crow, Tensor compressed_idx, Tensor plain_idx, int cdim, int dim, int nnz) -> ()
  device_check: NoCheck
  variants: function
  dispatch:
    CPU: _validate_compressed_sparse_indices_cpu
    CUDA: _validate_compressed_sparse_indices_cuda

- func: _cufft_get_plan_cache_size(DeviceIndex device_index) -> int

- func: _cufft_get_plan_cache_max_size(DeviceIndex device_index) -> int

- func: _cufft_set_plan_cache_max_size(DeviceIndex device_index, int max_size) -> ()

- func: _cufft_clear_plan_cache(DeviceIndex device_index) -> ()

- func: index.Tensor(Tensor self, Tensor?[] indices) -> Tensor
  device_check: NoCheck   # TensorIterator
  structured_delegate: index.Tensor_out
  variants: function, method
  dispatch:
    QuantizedCPU: quantized_index
  tags: [core, dynamic_output_shape]
  # NB: This function is special-cased in tools/autograd/gen_variable_type.py
  # NB: The following functions are declared in aten/src/ATen/templates/TensorBody.h and defined in aten/src/ATen/TensorIndexing.cpp:
  # - Tensor Tensor::index(ArrayRef<TensorIndex> indices)
  # - Tensor Tensor::index(std::initializer_list<TensorIndex> indices)

- func: index.Tensor_out(Tensor self, Tensor?[] indices, *, Tensor(a!) out) -> Tensor(a!)
  device_check: NoCheck
  structured: True
  structured_inherits: TensorIteratorBase
  precomputed:
  - indices -> DimVector sizes, DimVector strides
  dispatch:
    CPU, CUDA, MPS: index_out

# Used by inductor to signal indexing without bounds checks
# Note that we don`
  - ` and be bound to the desired Python name in
#   torch/linalg/__init__.py, and the desired C++ name in torch/csrc/api/include/torch/linalg.h.
#   The `
  - `s autograd behavior.
# 2) Implement the corresponding functions and have them redispatch to the
#      original function.
# 3) Add docstrings to the new function that reference the original function,
#      and document the method as usual (if it exists.)
#    (See torch/_torch_docs.py and docs/source/torch.rst if adding a function,
#     torch/_tensor_docs.py and docs/source/tensors.rst if adding a method,
#     or module-specific doc bindings (like torch/linalg/__init__.py) if
#     adding an alias in a namespace.)
# 4) Update torch/overrides.py consistent with the original function.
# 5) Update the alias_map in torch/csrc/jit/passes/normalize_ops.cpp.
# 6) Add aliases argument to existing OpInfo/UnaryUfuncInfo or create new OpInfo/UnaryUfuncInfo entry
# in op_db list in torch/testing/_internal/common_methods_invocations.py
#
# See torch.absolute, an alias for torch.abs, as an example.
# Absolute, alias for abs

- func: absolute(Tensor self) -> Tensor
  device_check: NoCheck   # TensorIterator
  variants: function, method

- func: absolute_(Tensor(a!) self) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  variants: method

- func: absolute.out(Tensor self, *, Tensor(a!) out) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator

- func: angle(Tensor self) -> Tensor
  device_check: NoCheck   # TensorIterator
  variants: function, method
  dispatch:
    CPU, CUDA: angle
    MPS: angle_mps
    SparseCsrCPU, SparseCsrCUDA, SparseCsrMeta: angle_sparse_csr
  tags: pointwise

- func: angle.out(Tensor self, *, Tensor(a!) out) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  dispatch:
    CPU, CUDA: angle_out
    MPS: angle_out_mps
    SparseCsrCPU, SparseCsrCUDA, SparseCsrMeta: angle_sparse_csr_out
  tags: pointwise

- func: view_as_real(Tensor(a) self) -> Tensor(a)
  variants: function
  dispatch:
    CPU, CUDA, MPS, Meta: view_as_real

- func: view_as_complex(Tensor(a) self) -> Tensor(a)
  variants: function
  dispatch:
    CPU, CUDA, MPS, Meta: view_as_complex

- func: sgn(Tensor self) -> Tensor
  variants: function, method
  structured_delegate: sgn.out
  dispatch:
    SparseCPU, SparseCUDA: sgn_sparse
    SparseCsrCPU, SparseCsrCUDA, SparseCsrMeta: sgn_sparse_csr
    NestedTensorCPU, NestedTensorCUDA: NestedTensor_sgn
  tags: pointwise

- func: sgn_(Tensor(a!) self) -> Tensor(a!)
  variants: method
  structured_delegate: sgn.out
  dispatch:
    SparseCPU, SparseCUDA: sgn_sparse_
    SparseCsrCPU, SparseCsrCUDA, SparseCsrMeta: sgn_sparse_csr_
    NestedTensorCPU, NestedTensorCUDA: NestedTensor_sgn_
  tags: pointwise

- func: sgn.out(Tensor self, *, Tensor(a!) out) -> Tensor(a!)
  structured: True
  structured_inherits: TensorIteratorBase
  dispatch:
    CPU, CUDA: sgn_out
    MPS: sgn_out_mps
    SparseCPU, SparseCUDA: sgn_sparse_out
    SparseCsrCPU, SparseCsrCUDA, SparseCsrMeta: sgn_sparse_csr_out
  tags: pointwise

- func: chalf(Tensor self, *, MemoryFormat? memory_format=None) -> Tensor
  variants: method

- func: real(Tensor(a) self) -> Tensor(a)
  device_check: NoCheck   # TensorIterator
  variants: function

- func: imag(Tensor(a) self) -> Tensor(a)
  device_check: NoCheck   # TensorIterator
  variants: function

- func: _conj(Tensor(a) self) -> Tensor(a)
  variants: function, method
  dispatch:
    CompositeExplicitAutograd: _conj

- func: conj(Tensor(a) self) -> Tensor(a)
  variants: function, method
  manual_cpp_binding: True

- func: _conj_physical(Tensor self) -> Tensor
  variants: function, method
  dispatch:
    CompositeExplicitAutograd: _conj_physical
    SparseCsrCPU, SparseCsrCUDA, SparseCsrMeta: conj_physical_sparse_csr
  autogen: _conj_physical.out

- func: conj_physical(Tensor self) -> Tensor
  variants: function, method
  tags: [pointwise, maybe_aliasing_or_mutating]

- func: conj_physical.out(Tensor self, *, Tensor(a!) out) -> Tensor(a!)
  dispatch:
    CPU, CUDA: conj_physical_out
    MPS: conj_physical_out_mps
    SparseCPU, SparseCUDA: conj_physical_out_sparse
    SparseCsrCPU, SparseCsrCUDA, SparseCsrMeta: conj_physical_sparse_csr_out
  tags: pointwise

- func: conj_physical_(Tensor(a!) self) -> Tensor(a!)
  variants: function, method
  dispatch:
    CompositeExplicitAutograd: conj_physical_
    SparseCsrCPU, SparseCsrCUDA, SparseCsrMeta: conj_physical_sparse_csr_
  tags: pointwise

- func: resolve_conj(Tensor(a) self) -> Tensor(a)
  variants: function, method

- func: resolve_neg(Tensor(a) self) -> Tensor(a)
  variants: function, method

- func: _neg_view(Tensor(a) self) -> Tensor(a)
  variants: function, method
  dispatch:
    CompositeExplicitAutograd: _neg_view

- func: acos(Tensor self) -> Tensor
  device_check: NoCheck   # TensorIterator
  variants: function, method
  structured_delegate: acos.out
  tags: [core, pointwise]

- func: acos_(Tensor(a!) self) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  variants: function, method
  structured_delegate: acos.out
  tags: pointwise

- func: acos.out(Tensor self, *, Tensor(a!) out) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  structured: True
  structured_inherits: TensorIteratorBase
  dispatch:
    CPU, CUDA: acos_out
    MPS: acos_out_mps
  tags: pointwise

# arccos, alias of acos
- func: arccos(Tensor self) -> Tensor
  variants: function, method

- func: arccos_(Tensor(a!) self) -> Tensor(a!)
  variants: function, method

- func: arccos.out(Tensor self, *, Tensor(a!) out) -> Tensor(a!)

- func: avg_pool1d(Tensor self, int[1] kernel_size, int[1] stride=[], int[1] padding=0, bool ceil_mode=False, bool count_include_pad=True) -> Tensor
  tags: core
  autogen: avg_pool1d.out

- func: adaptive_avg_pool1d(Tensor self, int[1] output_size) -> Tensor
  tags: core
  autogen: adaptive_avg_pool1d.out

# Return: (Tensor output, Tensor indices)
- func: adaptive_max_pool1d(Tensor self, int[1] output_size) -> (Tensor, Tensor)

- func: add.Tensor(Tensor self, Tensor other, *, Scalar alpha=1) -> Tensor
  device_check: NoCheck   # TensorIterator
  structured_delegate: add.out
  variants: function, method
  dispatch:
    SparseCPU, SparseCUDA, SparseMeta: add_sparse
    SparseCsrCPU, SparseCsrCUDA, SparseCsrMeta: add_sparse_csr
    MkldnnCPU: mkldnn_add
    ZeroTensor: add_zerotensor
    NestedTensorCPU, NestedTensorCUDA: NestedTensor_add_Tensor
  tags: [core, pointwise]

- func: add_.Tensor(Tensor(a!) self, Tensor other, *, Scalar alpha=1) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  variants: method
  structured_delegate: add.out
  dispatch:
    SparseCPU, SparseCUDA, SparseMeta: add_sparse_
    SparseCsrCPU, SparseCsrCUDA, SparseCsrMeta: add_sparse_csr_
    MkldnnCPU: mkldnn_add_
    NestedTensorCPU, NestedTensorCUDA: NestedTensor_add__Tensor
  tags: pointwise

- func: add.out(Tensor self, Tensor other, *, Scalar alpha=1, Tensor(a!) out) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  structured: True
  structured_inherits: TensorIteratorBase
  ufunc_inner_loop:
    Generic: add (AllAndComplex, BFloat16, Half, ComplexHalf)
    ScalarOnly: add (Bool)
  dispatch:
    SparseCPU, SparseMeta: add_out_sparse_cpu
    SparseCUDA: add_out_sparse_cuda
    SparseCsrCPU, SparseCsrMeta: add_out_sparse_compressed_cpu
    SparseCsrCUDA: add_out_sparse_compressed_cuda
    MkldnnCPU: mkldnn_add_out
    MPS: add_out_mps
  tags: pointwise

- func: _add_relu.Tensor(Tensor self, Tensor other, *, Scalar alpha=1) -> Tensor
  variants: function
  dispatch:
    CPU: add_relu

- func: _add_relu_.Tensor(Tensor(a!) self, Tensor other, *, Scalar alpha=1) -> Tensor(a!)
  variants: function
  dispatch:
    CPU: add_relu_

- func: _add_relu.out(Tensor self, Tensor other, *, Scalar alpha=1, Tensor(a!) out) -> Tensor(a!)
  variants: function
  dispatch:
    CPU: add_relu_out

- func: _add_relu.Scalar(Tensor self, Scalar other, Scalar alpha=1) -> Tensor
  variants: function
  dispatch:
    CPU: add_relu

- func: _add_relu_.Scalar(Tensor(a!) self, Scalar other, Scalar alpha=1) -> Tensor(a!)
  variants: function
  dispatch:
    CPU: add_relu_
  autogen: _add_relu.Scalar_out

# For C++ only, until we have conversion from C++ numbers to Tensor
- func: add.Scalar(Tensor self, Scalar other, Scalar alpha=1) -> Tensor
  device_check: NoCheck   # TensorIterator
  variants: function, method
  dispatch:
    CompositeExplicitAutograd: add
  tags: [core, pointwise]

- func: add_.Scalar(Tensor(a!) self, Scalar other, Scalar alpha=1) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  variants: method
  dispatch:
    CompositeExplicitAutograd: add_
  autogen: add.Scalar_out
  tags: pointwise

- func: addmv(Tensor self, Tensor mat, Tensor vec, *, Scalar beta=1, Scalar alpha=1) -> Tensor
  structured_delegate: addmv.out
  variants: function, method

- func: addmv_(Tensor(a!) self, Tensor mat, Tensor vec, *, Scalar beta=1, Scalar alpha=1) -> Tensor(a!)
  structured_delegate: addmv.out
  variants: function, method

- func: addmv.out(Tensor self, Tensor mat, Tensor vec, *, Scalar beta=1, Scalar alpha=1, Tensor(a!) out) -> Tensor(a!)
  structured: True
  dispatch:
    CPU: addmv_out_cpu
    CUDA: addmv_out_cuda
    MPS: addmv_out_mps
    XPU: addmv_out_xpu
    SparseCsrCPU: addmv_out_sparse_compressed
    SparseCsrCUDA: addmv_out_sparse_compressed_cuda

- func: addr(Tensor self, Tensor vec1, Tensor vec2, *, Scalar beta=1, Scalar alpha=1) -> Tensor
  variants: function, method
  dispatch:
    CPU, CUDA: addr
    MPS: addr_mps
    CompositeExplicitAutograd: math_addr

- func: addr_(Tensor(a!) self, Tensor vec1, Tensor vec2, *, Scalar beta=1, Scalar alpha=1) -> Tensor(a!)
  variants: method
  dispatch:
    CompositeExplicitAutograd: addr_

- func: addr.out(Tensor self, Tensor vec1, Tensor vec2, *, Scalar beta=1, Scalar alpha=1, Tensor(a!) out) -> Tensor(a!)
  dispatch:
    CPU, CUDA: addr_out
    MPS: addr_out_mps
    CompositeExplicitAutograd: math_addr_out

- func: affine_grid_generator(Tensor theta, SymInt[] size, bool align_corners) -> Tensor
  variants: function
  dispatch:
    CompositeExplicitAutograd: affine_grid_generator
  autogen: affine_grid_generator.out

- func: affine_grid_generator_backward(Tensor grad, SymInt[] size, bool align_corners) -> Tensor
  variants: function

- func: _is_all_true(Tensor self) -> Tensor
  variants: function, method
  dispatch:
    CompositeExplicitAutograd: _is_all_true

- func: _is_any_true(Tensor self) -> Tensor
  variants: function, method
  dispatch:
    CompositeExplicitAutograd: _is_any_true

# Note: this function is only for testing.
- func: _test_check_tensor(Tensor self) -> Tensor
  variants: function

# Note; this function is only for testing
- func: _test_functorch_fallback(Tensor self, Tensor other) -> Tensor
  variants: function
  dispatch:
    CPU: _test_functorch_fallback
  autogen: _test_functorch_fallback.out

- func: all.dim(Tensor self, int dim, bool keepdim=False) -> Tensor
  device_check: NoCheck   # TensorIterator
  structured_delegate: all.out
  variants: function, method
  dispatch:
    NestedTensorCPU, NestedTensorCUDA: NestedTensor_all


- func: all.dims(Tensor self, int[]? dim=None, bool keepdim=False) -> Tensor
  device_check: NoCheck   # TensorIterator
  structured_delegate: all.dims_out
  variants: function, method
  cpp_no_default_args: [`
  - `t apply
    CompositeExplicitAutograd: full_like
  autogen: full_like.out
  tags: core

- func: from_file(str filename, bool? shared=None, int? size=0, *, ScalarType? dtype=None, Layout? layout=None, Device? device=None, bool? pin_memory=None) -> Tensor
  dispatch:
    CPU: from_file
  autogen: from_file.out

- func: gcd.out(Tensor self, Tensor other, *, Tensor(a!) out) -> Tensor(a!)
  structured: True
  structured_inherits: TensorIteratorBase
  dispatch:
    CPU, CUDA: gcd_out
  tags: pointwise

- func: gcd(Tensor self, Tensor other) -> Tensor
  structured_delegate: gcd.out
  variants: function, method
  tags: pointwise

- func: gcd_(Tensor(a!) self, Tensor other) -> Tensor(a!)
  structured_delegate: gcd.out
  variants: function, method

- func: lcm.out(Tensor self, Tensor other, *, Tensor(a!) out) -> Tensor(a!)
  structured: True
  structured_inherits: TensorIteratorBase
  dispatch:
    CPU, CUDA: lcm_out
  tags: pointwise

- func: lcm(Tensor self, Tensor other) -> Tensor
  structured_delegate: lcm.out
  variants: function, method
  tags: pointwise

- func: lcm_(Tensor(a!) self, Tensor other) -> Tensor(a!)
  structured_delegate: lcm.out
  variants: function, method

# NOTE [ grid_sampler Native Functions ]
# `grid_sampler` is _supposed to_ do all the shape checking and then dispatch to
# one of `cudnn_grid_sampler`, `grid_sampler_2d`, or `grid_sampler_3d`, each of
# which has the corresponding backward defined as native functions as well.
# However, we do shape checking everywhere for now since each of the mentioned
# functions can be called directly, which will lead to crashes otherwise.
# See https://github.com/pytorch/pytorch/issues/73187 for more information.
#
# There is also _grid_sampler_2d_backward_cpu_fallback which is an
# implementation detail of grid_sampler_2d and is only exposed here for testing
# purposes.
#
# Additionally, arguments `padding_mode` and `interpolation_mode` are cast to
# enums defined in `native/GridSampler.h`. `cudnn_grid_sampler` doesn`
  - ` underscore and be bound to the desired Python name in
#   torch/nested/__init__.py, and the desired C++ name in torch/csrc/api/include/torch/nested.h.
#   The `
  - ` underscore and be bound to the desired Python name in
#   torch/special/__init__.py, and the desired C++ name in torch/csrc/api/include/torch/special.h.
#   The `
  - ` style; that is,
# C code in the THNN/ or THCUNN/ directory.  A slow_ convolution is
# one that is written in the native style: modern C++.  Algorithmically,
# these are the same thing, but we give them different prefixes to
# make the operational distinction clear.
  tags: pointwise

- func: slow_conv_transpose2d.out(Tensor self, Tensor weight, SymInt[2] kernel_size, Tensor? bias=None, SymInt[2] stride=1, SymInt[2] padding=0, SymInt[2] output_padding=0, SymInt[2] dilation=1, *, Tensor(a!) out) -> Tensor(a!)
  python_module: nn
  structured: True
  dispatch:
    CPU: slow_conv_transpose2d_structured_cpu
    CUDA: slow_conv_transpose2d_structured_cuda

- func: slow_conv_transpose2d(Tensor self, Tensor weight, SymInt[2] kernel_size, Tensor? bias=None, SymInt[2] stride=1, SymInt[2] padding=0, SymInt[2] output_padding=0, SymInt[2] dilation=1) -> Tensor
  python_module: nn
  structured_delegate: slow_conv_transpose2d.out

- func: slow_conv_transpose3d.out(Tensor self, Tensor weight, SymInt[3] kernel_size, Tensor? bias=None, SymInt[3] stride=1, SymInt[3] padding=0, SymInt[3] output_padding=0, SymInt[3] dilation=1, *, Tensor(a!) out) -> Tensor(a!)
  python_module: nn
  dispatch:
    CPU: slow_conv_transpose3d_out_cpu
    CUDA: slow_conv_transpose3d_out_cuda

- func: slow_conv_transpose3d(Tensor self, Tensor weight, SymInt[3] kernel_size, Tensor? bias=None, SymInt[3] stride=1, SymInt[3] padding=0, SymInt[3] output_padding=0, SymInt[3] dilation=1) -> Tensor
  python_module: nn
  dispatch:
    CPU: slow_conv_transpose3d_cpu
    CUDA: slow_conv_transpose3d_cuda

- func: thnn_conv2d.out(Tensor self, Tensor weight, SymInt[2] kernel_size, Tensor? bias=None, SymInt[2] stride=1, SymInt[2] padding=0, *, Tensor(a!) out) -> Tensor(a!)
  python_module: nn

- func: thnn_conv2d(Tensor self, Tensor weight, SymInt[2] kernel_size, Tensor? bias=None, SymInt[2] stride=1, SymInt[2] padding=0) -> Tensor
  python_module: nn

- func: _slow_conv2d_forward.output(Tensor self, Tensor weight, SymInt[2] kernel_size, Tensor? bias, SymInt[2] stride, SymInt[2] padding, *, Tensor(a!) output) -> Tensor(a!)
  python_module: nn
  dispatch:
    CPU: slow_conv2d_forward_out_cpu
    CUDA: slow_conv2d_forward_out_cuda

- func: _slow_conv2d_forward(Tensor self, Tensor weight, SymInt[2] kernel_size, Tensor? bias, SymInt[2] stride, SymInt[2] padding) -> Tensor
  python_module: nn
  dispatch:
    CPU: slow_conv2d_forward_cpu
    CUDA: slow_conv2d_forward_cuda

- func: _slow_conv2d_backward.grad_input(Tensor grad_output, Tensor self, Tensor weight, SymInt[2] kernel_size, SymInt[2] stride, SymInt[2] padding, *, Tensor(a!) grad_input, Tensor(b!) grad_weight, Tensor(c!) grad_bias) -> (Tensor(a!), Tensor(b!), Tensor(c!))
  python_module: nn
  dispatch:
    CPU: slow_conv2d_backward_out_cpu
    CUDA: slow_conv2d_backward_out_cuda

- func: _slow_conv2d_backward.output_mask(Tensor grad_output, Tensor self, Tensor weight, SymInt[2] kernel_size, SymInt[2] stride, SymInt[2] padding, bool[3] output_mask) -> (Tensor grad_input, Tensor grad_weight, Tensor grad_bias)
  python_module: nn
  dispatch:
    CPU: slow_conv2d_backward_cpu
    CUDA: slow_conv2d_backward_cuda
  autogen: _slow_conv2d_backward.output_mask_out

- func: _conv_depthwise2d.out(Tensor self, Tensor weight, SymInt[2] kernel_size, Tensor? bias, SymInt[2] stride, SymInt[2] padding, SymInt[2] dilation, *, Tensor(a!) out) -> Tensor(a!)
  python_module: nn
  dispatch:
    CUDA: conv_depthwise2d_cuda_out

- func: _conv_depthwise2d(Tensor self, Tensor weight, SymInt[2] kernel_size, Tensor? bias, SymInt[2] stride, SymInt[2] padding, SymInt[2] dilation) -> Tensor
  python_module: nn
  dispatch:
    CUDA: conv_depthwise2d_cuda

- func: conv_depthwise3d(Tensor self, Tensor weight, SymInt[3] kernel_size, Tensor? bias, SymInt[3] stride, SymInt[3] padding, SymInt[3] dilation) -> Tensor
  python_module: nn
  dispatch:
    CUDA: conv_depthwise3d_cuda
  autogen: conv_depthwise3d.out

- func: slow_conv3d.out(Tensor self, Tensor weight, SymInt[3] kernel_size, Tensor? bias=None, SymInt[3] stride=1, SymInt[3] padding=0, *, Tensor(a!) out) -> Tensor(a!)
  python_module: nn

- func: slow_conv3d(Tensor self, Tensor weight, SymInt[3] kernel_size, Tensor? bias=None, SymInt[3] stride=1, SymInt[3] padding=0) -> Tensor
  python_module: nn

- func: slow_conv3d_forward.output(Tensor self, Tensor weight, SymInt[3] kernel_size, Tensor? bias, SymInt[3] stride, SymInt[3] padding, *, Tensor(a!) output) -> Tensor(a!)
  python_module: nn
  dispatch:
    CPU: slow_conv3d_forward_out_cpu

- func: slow_conv3d_forward(Tensor self, Tensor weight, SymInt[3] kernel_size, Tensor? bias, SymInt[3] stride, SymInt[3] padding) -> Tensor
  python_module: nn
  dispatch:
    CPU: slow_conv3d_forward_cpu

- func: slow_conv_dilated2d(Tensor self, Tensor weight, SymInt[2] kernel_size, Tensor? bias=None, SymInt[2] stride=1, SymInt[2] padding=0, SymInt[2] dilation=1) -> Tensor
  python_module: nn
  dispatch:
    CPU: slow_conv_dilated2d_cpu
    CUDA: slow_conv_dilated2d_cuda
  autogen: slow_conv_dilated2d.out

- func: slow_conv_dilated3d(Tensor self, Tensor weight, SymInt[3] kernel_size, Tensor? bias=None, SymInt[3] stride=1, SymInt[3] padding=0, SymInt[3] dilation=1) -> Tensor
  python_module: nn
  dispatch:
    CPU: slow_conv_dilated3d_cpu
    CUDA: slow_conv_dilated3d_cuda
  autogen: slow_conv_dilated3d.out

- func: col2im.out(Tensor self, SymInt[2] output_size, int[2] kernel_size, int[2] dilation, int[2] padding, int[2] stride, *, Tensor(a!) out) -> Tensor(a!)
  python_module: nn
  dispatch:
    CPU: col2im_out_cpu
    CUDA: col2im_out_cuda

- func: col2im(Tensor self, SymInt[2] output_size, int[2] kernel_size, int[2] dilation, int[2] padding, int[2] stride) -> Tensor
  python_module: nn
  dispatch:
    CPU: col2im_cpu
    CUDA: col2im_cuda
  tags: core

- func: column_stack(Tensor[] tensors) -> Tensor

- func: column_stack.out(Tensor[] tensors, *, Tensor(a!) out) -> Tensor(a!)

- func: im2col.out(Tensor self, int[2] kernel_size, int[2] dilation, int[2] padding, int[2] stride, *, Tensor(a!) out) -> Tensor(a!)
  python_module: nn
  dispatch:
    CPU: im2col_out_cpu
    CUDA: im2col_out_cuda
    MPS: im2col_out_mps

- func: im2col(Tensor self, int[2] kernel_size, int[2] dilation, int[2] padding, int[2] stride) -> Tensor
  python_module: nn
  dispatch:
    CPU: im2col_cpu
    CUDA: im2col_cuda
    MPS: im2col_mps

- func: isfinite(Tensor self) -> Tensor
  variants: function, method
  device_check: NoCheck
  device_guard: False
  tags: pointwise

- func: isinf(Tensor self) -> Tensor
  variants: function, method
  device_check: NoCheck
  device_guard: False
  dispatch:
    CompositeExplicitAutograd: isinf
    NestedTensorCPU, NestedTensorCUDA: NestedTensor_isinf
    SparseCPU, SparseCUDA: isinf_sparse
    SparseMeta: isinf_sparse_meta
    SparseCsrCPU, SparseCsrCUDA, SparseCsrMeta: isinf_sparse_csr
  autogen: isinf.out
  tags: [core, pointwise]

- func: record_stream(Tensor(a!) self, Stream s) -> ()
  variants: method
  dispatch:
    CUDA: record_stream_cuda

- func: isposinf(Tensor self) -> Tensor
  variants: function, method
  structured_delegate: isposinf.out
  dispatch:
    NestedTensorCPU, NestedTensorCUDA: NestedTensor_isposinf
    SparseCPU, SparseCUDA: isposinf_sparse
    SparseCsrCPU, SparseCsrCUDA, SparseCsrMeta: isposinf_sparse_csr
  tags: pointwise

- func: isposinf.out(Tensor self, *, Tensor(a!) out) -> Tensor(a!)
  structured: True
  structured_inherits: TensorIteratorBase
  dispatch:
    CPU, CUDA, MPS: isposinf_out
    SparseCPU, SparseCUDA: isposinf_sparse_out
    SparseCsrCPU, SparseCsrCUDA, SparseCsrMeta: isposinf_sparse_csr_out
  tags: pointwise

- func: isneginf(Tensor self) -> Tensor
  variants: function, method
  structured_delegate: isneginf.out
  dispatch:
    NestedTensorCPU, NestedTensorCUDA: NestedTensor_isneginf
    SparseCPU, SparseCUDA: isneginf_sparse
    SparseCsrCPU, SparseCsrCUDA, SparseCsrMeta: isneginf_sparse_csr
  tags: pointwise

- func: isneginf.out(Tensor self, *, Tensor(a!) out) -> Tensor(a!)
  structured: True
  structured_inherits: TensorIteratorBase
  dispatch:
    CPU, CUDA, MPS: isneginf_out
    SparseCPU, SparseCUDA: isneginf_sparse_out
    SparseCsrCPU, SparseCsrCUDA, SparseCsrMeta: isneginf_sparse_csr_out
  tags: pointwise

# NOTE [_add_batch_dim and _remove_batch_dim]
# _add_batch_dim and _remove_batch_dim are meant to be used in the implementation
# of the vmap frontend API (see torch/_vmap_internals.py). They are not
# user-facing, hence the leading underscore. Please don`
  - ` to indicate that they should be used with care. We provide:
#
#   + `_indices()`: returns the *raw* indices within the sparse tensor (not just
#                   sharing storage). Any inplace operation will change the
#                   actual indices, including t_, set_, as_strided_, resize_,
#                   etc.
#   + `_values()`: returns the *raw* values within the sparse tensor. Similar
#                  semantics as `_indices()`
#   + `_nnz()`: returns the number of non-zero entries. This will always be
#               determined by the shapes of indices and values.
#   + `_coalesced_(bool)`: inplace sets whether the tensor is coalesced, and
#                          returns itself.
#
# These methods are very useful in writing new operations, e.g., a custom
# autograd Function.
#
# We also provide other public *safe* APIs:
#   + `indices()`: returns a **view** of the indices tensor if the sparse tensor
#                  is **coalesced**.
#   + `values()`: returns a **view** of the values tensor if the containing
#                 sparse tensor is **coalesced**.
#   + `sparse_dim()`: number of sparse dimensions
#   + `dense_dim()`: number of dense dimensions
#   + `is_coalesced()`: whether the sparse tensor is coalesced
#
# `_indices()` and `_values()` should returns the raw indices and values dense
# tensors within a sparse tensor. They can be quite unsafe with inplace
# operations like `t_()`, and exposes uncoalesced indices and values. The public
# recommended API is `indices()` and `values()`, both of which first check that
# the tensor is coalesced and return views on those tensors.
#
#
# Autograd Support
# ~~~~~~~~~~~~~~~~
#
# Autograd is supported on `values()` and sparse tensor ctor with indices and
# values tensors. E.g., `torch.sparse_coo_tensor(i, v).values().sum()` is
# differentiable w.r.t. `v`.
#
# NB: The `values()` and `_values()` operators are special in that they are
# layout-aware, i.e., the output depends not just on the data it represents, but
# also on the input layout details (in this case, the `indices` tensor). See
# NOTE [ as_strided Backward and layout-aware/agnostic autograd ] in Functions.cpp
# for discussion on layout-aware vs layout-agnostic autograd. Since PyTorch ops
# operate in the layout-agnostic mode, similar to `as_strided`, backward of
# these two operators need to consider them in a layout-agnostic way:
#   + `values()`:
#     Input is coalesced.
#     We just pretend having `input.indices()` as an additional argument
#     `input_indices`, then forward is similar to
#     `input.to(kStrided).index_select(input_indices)` regardless of the layout.
#     Note that `values()` normally is layout-aware even if we constrain
#     ourselves on sparse inputs since it may include all zeros values entries
#     as `
  - `]
  dispatch:
    CompositeImplicitAutograd: conv3d_padding_symint

- func: conv_tbc(Tensor self, Tensor weight, Tensor bias, int pad=0) -> Tensor
  dispatch:
    CompositeExplicitAutograd: conv_tbc
  autogen: conv_tbc.out

- func: conv_tbc_backward(Tensor self, Tensor input, Tensor weight, Tensor bias, int pad) -> (Tensor, Tensor, Tensor)

# NB: we inherit the goofy argument order from PyTorch torch.nn.functional
- func: conv_transpose1d(Tensor input, Tensor weight, Tensor? bias=None, SymInt[1] stride=1, SymInt[1] padding=0, SymInt[1] output_padding=0, SymInt groups=1, SymInt[1] dilation=1) -> Tensor
  dispatch:
    CompositeImplicitAutograd: conv_transpose1d_symint

- func: conv_transpose2d.input(Tensor input, Tensor weight, Tensor? bias=None, SymInt[2] stride=1, SymInt[2] padding=0, SymInt[2] output_padding=0, SymInt groups=1, SymInt[2] dilation=1) -> Tensor
  dispatch:
    CompositeImplicitAutograd: conv_transpose2d_symint

- func: conv_transpose3d.input(Tensor input, Tensor weight, Tensor? bias=None, SymInt[3] stride=1, SymInt[3] padding=0, SymInt[3] output_padding=0, SymInt groups=1, SymInt[3] dilation=1) -> Tensor
  dispatch:
    CompositeImplicitAutograd: conv_transpose3d_symint

- func: copy(Tensor self, Tensor src, bool non_blocking=False) -> Tensor
  variants: function
  dispatch:
    Meta: copy_meta
    CompositeExplicitAutogradNonFunctional: copy
  tags: core

- func: copy_(Tensor(a!) self, Tensor src, bool non_blocking=False) -> Tensor(a!)
  variants: method
  device_check: NoCheck
  device_guard: False
  dispatch:
    MkldnnCPU: copy_mkldnn_
    SparseCPU, SparseCUDA: copy_sparse_wrapper_
    CompositeExplicitAutograd: copy_
    SparseCsrCPU, SparseCsrCUDA, SparseCsrMeta: copy_sparse_compressed_
    NestedTensorCPU, NestedTensorCUDA: copy_nested_
  autogen: copy.out

- func: _copy_from(Tensor self, Tensor dst, bool non_blocking=False) -> Tensor
  dispatch:
    MPS: _copy_from_mps
  autogen: _copy_from.out

# We need this to be able to properly copy from a CPU to an XLA tensor with different sizes.
# See https://github.com/pytorch/xla/issues/2881
- func: _copy_from_and_resize(Tensor self, Tensor dst) -> Tensor
  dispatch:
    MPS: _copy_from_and_resize_mps
  autogen: _copy_from_and_resize.out

- func: cos(Tensor self) -> Tensor
  device_check: NoCheck   # TensorIterator
  variants: function, method
  structured_delegate: cos.out
  dispatch:
    NestedTensorCPU, NestedTensorCUDA: NestedTensor_cos
  tags: [core, pointwise]

- func: cos_(Tensor(a!) self) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  variants: function, method
  structured_delegate: cos.out
  tags: pointwise

- func: cos.out(Tensor self, *, Tensor(a!) out) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  structured: True
  structured_inherits: TensorIteratorBase
  dispatch:
    CPU, CUDA: cos_out
    MPS: cos_out_mps
  tags: pointwise

- func: cosh(Tensor self) -> Tensor
  device_check: NoCheck   # TensorIterator
  variants: function, method
  structured_delegate: cosh.out
  tags: [core, pointwise]

- func: cosh_(Tensor(a!) self) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  variants: function, method
  structured_delegate: cosh.out
  tags: pointwise

- func: cosh.out(Tensor self, *, Tensor(a!) out) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  structured: True
  structured_inherits: TensorIteratorBase
  dispatch:
    CPU, CUDA: cosh_out
    MPS: cosh_out_mps
  tags: pointwise

- func: cosine_embedding_loss(Tensor input1, Tensor input2, Tensor target, float margin=0.0, int reduction=Mean) -> Tensor

- func: count_nonzero.dim_IntList(Tensor self, int[] dim) -> Tensor
  variants: function, method
  dispatch:
    CPU: count_nonzero_cpu
    CUDA: count_nonzero_cuda
    MPS: count_nonzero_mps
  autogen: count_nonzero.dim_IntList_out

- func: count_nonzero(Tensor self, int? dim=None) -> Tensor
  variants: function, method
  dispatch:
    CompositeExplicitAutograd: count_nonzero
  autogen: count_nonzero.out

- func: cov(Tensor self, *, int correction=1, Tensor? fweights=None, Tensor? aweights=None) -> Tensor
  variants: function, method

- func: corrcoef(Tensor self) -> Tensor
  variants: function, method

- func: cudnn_affine_grid_generator(Tensor theta, int N, int C, int H, int W) -> Tensor grid
  dispatch:
    CUDA: cudnn_affine_grid_generator_forward
  autogen: cudnn_affine_grid_generator.out

# TODO: Why do I have to call this grad?!
- func: cudnn_affine_grid_generator_backward(Tensor grad, int N, int C, int H, int W) -> Tensor grad_theta
  dispatch:
    CUDA: cudnn_affine_grid_generator_backward
  autogen: cudnn_affine_grid_generator_backward.out

- func: cudnn_batch_norm(Tensor input, Tensor weight, Tensor? bias, Tensor? running_mean, Tensor? running_var, bool training, float exponential_average_factor, float epsilon) -> (Tensor, Tensor, Tensor, Tensor)
  dispatch:
    CUDA: cudnn_batch_norm
  autogen: cudnn_batch_norm.out

# NB: You can only use this if you used cudnn_batch_norm training=True
- func: cudnn_batch_norm_backward(Tensor input, Tensor grad_output, Tensor weight, Tensor? running_mean, Tensor? running_var, Tensor? save_mean, Tensor? save_var, float epsilon, Tensor reserveSpace) -> (Tensor, Tensor, Tensor)
  dispatch:
    CUDA: cudnn_batch_norm_backward
  autogen: cudnn_batch_norm_backward.out

- func: cudnn_convolution(Tensor self, Tensor weight, SymInt[] padding, SymInt[] stride, SymInt[] dilation, SymInt groups, bool benchmark, bool deterministic, bool allow_tf32) -> Tensor
  dispatch:
    CUDA: cudnn_convolution

- func: cudnn_convolution.out(Tensor self, Tensor weight, SymInt[] padding, SymInt[] stride, SymInt[] dilation, SymInt groups, bool benchmark, bool deterministic, bool allow_tf32, *, Tensor(a!) out) -> Tensor(a!)
  dispatch:
    CUDA: cudnn_convolution_out

- func: cudnn_convolution_transpose(Tensor self, Tensor weight, SymInt[] padding, SymInt[] output_padding, SymInt[] stride, SymInt[] dilation, SymInt groups, bool benchmark, bool deterministic, bool allow_tf32) -> Tensor
  dispatch:
    CUDA: cudnn_convolution_transpose
  autogen: cudnn_convolution_transpose.out

- func: _mps_convolution_transpose(Tensor self, Tensor weight, SymInt[] padding, SymInt[] output_padding, SymInt[] stride, SymInt[] dilation, SymInt groups) -> Tensor
  dispatch:
    MPS: _mps_convolution_transpose
  autogen: _mps_convolution_transpose.out

- func: mps_convolution_transpose_backward(Tensor self, Tensor grad_output, Tensor weight, SymInt[] padding, SymInt[] output_padding, SymInt[] stride, SymInt[] dilation, SymInt groups, bool[2] output_mask) -> (Tensor, Tensor)
  dispatch:
    MPS: mps_convolution_transpose_backward
  autogen: mps_convolution_transpose_backward.out

- func: cudnn_convolution_relu(Tensor self, Tensor weight, Tensor? bias, SymInt[] stride, SymInt[] padding, SymInt[] dilation, SymInt groups) -> Tensor
  dispatch:
    CUDA: cudnn_convolution_relu
  autogen: cudnn_convolution_relu.out

- func: cudnn_convolution_add_relu(Tensor self, Tensor weight, Tensor z, Scalar? alpha, Tensor? bias, SymInt[] stride, SymInt[] padding, SymInt[] dilation, SymInt groups) -> Tensor
  dispatch:
    CUDA: cudnn_convolution_add_relu
  autogen: cudnn_convolution_add_relu.out

# NB: input is special cased in a way I don`
  - `) -> Tensor
  structured_delegate: gelu_backward.grad_input
  python_module: nn
  dispatch:
    MkldnnCPU: mkldnn_gelu_backward
    NestedTensorCPU, NestedTensorCUDA: gelu_backwards_nested
  tags: pointwise

- func: infinitely_differentiable_gelu_backward(Tensor grad, Tensor self) -> Tensor
  variants: function
  python_module: nn
  device_check: NoCheck
  device_guard: False

- func: hardshrink.out(Tensor self, Scalar lambd=0.5, *, Tensor(a!) out) -> Tensor(a!)
  structured: True
  structured_inherits: TensorIteratorBase
  device_check: NoCheck   # TensorIterator
  dispatch:
    CPU, CUDA: hardshrink_out

- func: hardshrink(Tensor self, Scalar lambd=0.5) -> Tensor
  structured_delegate: hardshrink.out
  device_check: NoCheck   # TensorIterator
  variants: function, method
  tags: pointwise

- func: hardshrink_backward.grad_input(Tensor grad_out, Tensor self, Scalar lambd, *, Tensor(a!) grad_input) -> Tensor(a!)
  structured: True
  structured_inherits: TensorIteratorBase
  dispatch:
    CPU, CUDA: hardshrink_backward_out

- func: hardshrink_backward(Tensor grad_out, Tensor self, Scalar lambd) -> Tensor
  structured_delegate: hardshrink_backward.grad_input
  variants: function, method

- func: rsqrt(Tensor self) -> Tensor
  device_check: NoCheck   # TensorIterator
  structured_delegate: rsqrt.out
  variants: function, method
  tags: [core, pointwise]

- func: rsqrt_(Tensor(a!) self) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  structured_delegate: rsqrt.out
  variants: function, method
  tags: pointwise

- func: rsqrt.out(Tensor self, *, Tensor(a!) out) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  structured: True
  structured_inherits: TensorIteratorBase
  dispatch:
    CPU, CUDA: rsqrt_out
    MPS: rsqrt_out_mps
  tags: pointwise

- func: select.Dimname(Tensor(a) self, Dimname dim, int index) -> Tensor(a)
  variants: function, method
  device_check: NoCheck
  device_guard: False

- func: select.int(Tensor(a) self, int dim, SymInt index) -> Tensor(a)
  variants: function, method
  device_check: NoCheck
  device_guard: False
  dispatch:
    CompositeExplicitAutograd: select_symint
    SparseCsrCPU, SparseCsrCUDA, SparseCsrMeta: select_sparse_csr
    NestedTensorCPU, NestedTensorCUDA: select_nested
  tags: core

- func: select_backward(Tensor grad_output, SymInt[] input_sizes, int dim, SymInt index) -> Tensor
  variants: function
  device_check: NoCheck
  device_guard: False
  dispatch:
    CompositeExplicitAutogradNonFunctional: select_backward_symint
  autogen: select_backward.out

- func: _nested_select_backward(Tensor grad_output, Tensor self, int dim, SymInt index) -> Tensor
  variants: function
  device_check: NoCheck
  device_guard: False
  dispatch:
    NestedTensorCPU, NestedTensorCUDA: _nested_select_backward_symint

- func: selu(Tensor self) -> Tensor
  device_check: NoCheck   # TensorIterator
  tags: pointwise

- func: selu_(Tensor(a!) self) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator

- func: celu(Tensor self, Scalar alpha=1.0) -> Tensor
  device_check: NoCheck   # TensorIterator
  dispatch:
    CompositeExplicitAutograd: celu
  tags: pointwise

- func: celu_(Tensor(a!) self, Scalar alpha=1.0) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  dispatch:
    CompositeExplicitAutograd: celu_
  autogen: celu.out

- func: silu(Tensor self) -> Tensor
  structured_delegate: silu.out
  python_module: nn
  dispatch:
    NestedTensorCPU, NestedTensorCUDA: NestedTensor_silu
  tags: pointwise

- func: silu_(Tensor(a!) self) -> Tensor(a!)
  structured_delegate: silu.out
  python_module: nn
  dispatch:
    NestedTensorCPU, NestedTensorCUDA: NestedTensor_silu_
  tags: pointwise

- func: silu.out(Tensor self, *, Tensor(a!) out) -> Tensor(a!)
  structured: True
  structured_inherits: TensorIteratorBase
  python_module: nn
  dispatch:
    CPU, CUDA: silu_out
    MPS: silu_out_mps
  tags: pointwise

- func: silu_backward.grad_input(Tensor grad_output, Tensor self, *, Tensor(a!) grad_input) -> Tensor(a!)
  structured: True
  structured_inherits: TensorIteratorBase
  python_module: nn
  dispatch:
    CPU, CUDA: silu_backward_out
    MPS: silu_backward_out_mps
  tags: pointwise

- func: silu_backward(Tensor grad_output, Tensor self) -> Tensor
  structured_delegate: silu_backward.grad_input
  python_module: nn
  dispatch:
    CompositeImplicitAutograd: math_silu_backward
    NestedTensorCPU, NestedTensorCUDA: silu_backward_nested
  tags: pointwise

- func: mish(Tensor self) -> Tensor
  structured_delegate: mish.out
  python_module: nn
  tags: pointwise

- func: mish_(Tensor(a!) self) -> Tensor(a!)
  structured_delegate: mish.out
  python_module: nn

- func: mish.out(Tensor self, *, Tensor(a!) out) -> Tensor(a!)
  structured: True
  structured_inherits: TensorIteratorBase
  python_module: nn
  dispatch:
    CPU, CUDA: mish_out
    MPS: mish_out_mps

- func: mish_backward(Tensor grad_output, Tensor self) -> Tensor
  python_module: nn
  dispatch:
    CPU, CUDA: mish_backward
    MPS: mish_backward_mps
    CompositeImplicitAutograd: math_mish_backward

- func: sigmoid(Tensor self) -> Tensor
  device_check: NoCheck   # TensorIterator
  structured_delegate: sigmoid.out
  variants: function, method
  dispatch:
    QuantizedCPU: sigmoid_quantized_cpu
    MkldnnCPU: mkldnn_sigmoid
  tags: [core, pointwise]

- func: sigmoid_(Tensor(a!) self) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  structured_delegate: sigmoid.out
  variants: function, method
  dispatch:
    MkldnnCPU: mkldnn_sigmoid_
  tags: pointwise

- func: sigmoid.out(Tensor self, *, Tensor(a!) out) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  structured: True
  structured_inherits: TensorIteratorBase
  dispatch:
    CPU, CUDA: sigmoid_out
    MPS: sigmoid_out_mps
  tags: pointwise

- func: logit(Tensor self, float? eps=None) -> Tensor
  variants: function, method
  dispatch:
    CPU, CUDA: logit
    MPS: logit_mps
  tags: pointwise

- func: logit_(Tensor(a!) self, float? eps=None) -> Tensor(a!)
  variants: function, method
  dispatch:
    CPU, CUDA: logit_
  tags: pointwise

- func: logit.out(Tensor self, float? eps=None, *, Tensor(a!) out) -> Tensor(a!)
  dispatch:
    CPU, CUDA: logit_out
    MPS: logit_out_mps
  tags: pointwise

- func: sin(Tensor self) -> Tensor
  device_check: NoCheck   # TensorIterator
  structured_delegate: sin.out
  variants: function, method
  dispatch:
    SparseCsrCPU, SparseCsrCUDA, SparseCsrMeta: sin_sparse_csr
    SparseCPU, SparseCUDA: sin_sparse
    NestedTensorCPU, NestedTensorCUDA: NestedTensor_sin
  tags: [core, pointwise]

- func: sin_(Tensor(a!) self) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  structured_delegate: sin.out
  variants: function, method
  dispatch:
    SparseCsrCPU, SparseCsrCUDA, SparseCsrMeta: sin_sparse_csr_
    SparseCPU, SparseCUDA: sin_sparse_
  tags: pointwise

- func: sin.out(Tensor self, *, Tensor(a!) out) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  structured: True
  structured_inherits: TensorIteratorBase
  dispatch:
    CPU, CUDA: sin_out
    MPS: sin_out_mps
    SparseCsrCPU, SparseCsrCUDA, SparseCsrMeta: sin_sparse_csr_out
    SparseCPU, SparseCUDA: sin_sparse_out
  tags: pointwise

- func: sinc(Tensor self) -> Tensor
  structured_delegate: sinc.out
  variants: function, method
  tags: pointwise

- func: sinc_(Tensor(a!) self) -> Tensor(a!)
  structured_delegate: sinc.out
  variants: function, method
  tags: pointwise

- func: sinc.out(Tensor self, *, Tensor(a!) out) -> Tensor(a!)
  structured: True
  structured_inherits: TensorIteratorBase
  dispatch:
    CPU, CUDA, MPS: sinc_out
  tags: pointwise

- func: sinh(Tensor self) -> Tensor
  device_check: NoCheck   # TensorIterator
  structured_delegate: sinh.out
  variants: function, method
  dispatch:
    SparseCPU, SparseCUDA: sinh_sparse
    SparseCsrCPU, SparseCsrCUDA, SparseCsrMeta: sinh_sparse_csr
  tags: [core, pointwise]

- func: sinh_(Tensor(a!) self) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  structured_delegate: sinh.out
  variants: function, method
  dispatch:
    SparseCPU, SparseCUDA: sinh_sparse_
    SparseCsrCPU, SparseCsrCUDA, SparseCsrMeta: sinh_sparse_csr_
  tags: pointwise

- func: sinh.out(Tensor self, *, Tensor(a!) out) -> Tensor(a!)
  device_check: NoCheck   # TensorIterator
  structured: True
  structured_inherits: TensorIteratorBase
  dispatch:
    CPU, CUDA: sinh_out
    MPS: sinh_out_mps
    SparseCPU, SparseCUDA: sinh_sparse_out
    SparseCsrCPU, SparseCsrCUDA, SparseCsrMeta: sinh_sparse_csr_out

# Returns a copy of this `Variable` that is detached from its autograd graph.
# This method is OK to call if the `Variable` is a view.
#
# NOTE: Previously, if we change the tensor metadata (e.g. sizes / strides /
# storage / storage_offset) of a tensor created from `detach()`, those metadata
# in the original tensor will also be updated. However, the new behavior is that
# those metadata changes to the detached tensor will not update the original tensor
# anymore, and in the `detach()` function we need to set `allow_tensor_metadata_change_`
# to false to make such changes explicitly illegal, in order to prevent users from
# changing metadata of the detached tensor and expecting the original tensor to also
# be updated.
  tags: pointwise
- func: detach(Tensor(a) self) -> Tensor(a)
  variants: function, method
  dispatch:
    CompositeExplicitAutograd: detach
    NestedTensorCPU, NestedTensorCUDA: detach

# Like `detach()`, but modifies this `Variable` in-place. This method may
# only be called on non-view `Variable`s. You can use `is_view()` to check
# this. If this `Variable` is a view, throws an `std::runtime_error()`.
- func: detach_(Tensor(a!) self) -> Tensor(a!)
  variants: function, method
  tags: inplace_view
  dispatch:
    CompositeExplicitAutograd: detach_

- func: size.int(Tensor self, int dim) -> int
  variants: function
  device_check: NoCheck
  device_guard: False
  manual_cpp_binding: True

- func: size.Dimname(Tensor self, Dimname dim) -> int
  variants: function, method
  device_check: NoCheck
  device_guard: False

- func: sym_size.int(Tensor self, int dim) -> SymInt
  variants: function
  device_check: NoCheck
  device_guard: False
  tags: core
  manual_cpp_binding: True

- func: sym_numel(Tensor self) -> SymInt
  variants: function
  device_check: NoCheck
  device_guard: False
  tags: core
  manual_cpp_binding: True

- func: sym_storage_offset(Tensor self) -> SymInt
  variants: function
  device_check: NoCheck
  device_guard: False
  tags: core
  manual_cpp_binding: True

- func: slice.Tensor(Tensor(a) self, int dim=0, SymInt? start=None, SymInt? end=None, SymInt step=1) -> Tensor(a)
  variants: function, method
  device_check: NoCheck
  device_guard: False
  dispatch:
    CompositeExplicitAutograd: slice
  tags: core

# NOTE: The implementation of split_with_sizes bypasses the dispatcher to call this; undo
# that if adding specific implementations here!

- func: slice_backward(Tensor grad_output, SymInt[] input_sizes, int dim, SymInt start, SymInt end, SymInt step) -> Tensor
  variants: function
  device_check: NoCheck
  device_guard: False
  dispatch:
    CompositeExplicitAutograd: slice_backward
  autogen: slice_backward.out

# NB: This op exists to back the implementation of reverse view_funcs for various views (chunk,
# slice.Tensor, split_with_sizes, et al.). Currently, these are only used during fake-ification
# of PT2 graph input subclass instances that are views. This means:
# * This op shouldn`

**.venv/lib/python3.12/site-packages/torchgen/packaged/ATen/native/tags.yaml**:
  - `t guarantee bitwise equivalence
          across different runs of an operator with identical inputs.
- tag: needs_fixed_stride_order
  desc: |
          This tag indicates that the operator should be passed Tensors following
          the same stride permutation as observed in eager when compiled in inductor.
          Only one of {needs_fixed_stride_order, flexible_layout} can apply; if
          multiple are assigned then we assume the most restrictive one.
- tag: flexible_layout
  desc: |
          This tag indicates that the custom operator can accept inputs with varying
          strides/storage_offset and that when compiled, Inductor is allowed to change
          the strides/storage_offset of inputs to the custom operator.
          Only one of {needs_fixed_stride_order, flexible_layout} can apply; if
          multiple are assigned then we assume the most restrictive one.

# NOTE [Core ATen Ops]
- tag: core
  desc: |
          Core aten ops is a subset of aten ops that remains after aten-to-aten decomposition and
          functionalization pass. Core aten ops are fully functional and adhere to single static
          assignment (SSA): this implies there will be no `inplace` or `_out` variants in this opset.
          This opset is designed to serve as the functional IR to interface with compiler backends.
          In contrast to primTorch, core aten opset doesn`

**modules/unicode_utils_v2/config/.pre-commit-config.yaml**:
  - `

install:		## Install package in development mode
	pip install -e .

install-dev:		## Install package with development dependencies
	pip install -e .[dev]

test:			## Run tests
	pytest tests/ -v

test-all:		## Run all tests including slow ones
	pytest tests/ -v -m `
  - `

test-cov:		## Run tests with coverage
	pytest tests/ -v --cov=unicode_utils --cov-report=html --cov-report=term-missing

lint:			## Run linting tools
	black --check unicode_utils tests
	flake8 unicode_utils tests
	mypy unicode_utils
	isort --check-only unicode_utils tests

format:			## Format code
	black unicode_utils tests
	isort unicode_utils tests

clean:			## Clean build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	find . -type d -name __pycache__ -delete
	find . -type f -name `

**modules/unicode_utils_v2/k8s/kustomization.yaml**:
  - `

# Namespace for all resources
namespace: unicode-utils

# Images to replace
images:
- name: unicode-utils
  newName: ghcr.io/unicode-utils/unicode-utils
  newTag: v3.0.0

# ConfigMap generator for environment-specific configs
configMapGenerator:
- name: unicode-utils-config
  literals:
  - WORKERS=4
  - HOST=0.0.0.0
  - PORT=8000
  - UNICODE_UTILS_ENV=production
  - LOG_LEVEL=info
  - METRICS_ENABLED=true
  - CACHE_TTL=3600
  - MAX_REQUEST_SIZE=10485760  # 10MB
  - RATE_LIMIT_PER_MINUTE=1000
  - JWT_ALGORITHM=HS256

# Secret generator for sensitive data
secretGenerator:
- name: unicode-utils-secrets
  literals:
  - JWT_SECRET_KEY=change-me-in-production
  - REDIS_PASSWORD=change-me-in-production
  - DB_PASSWORD=change-me-in-production

# Patches for environment-specific modifications
patches:
# Increase resources for production
- target:
    kind: Deployment
    name: unicode-utils-api
  patch: |-
    - op: replace
      path: /spec/template/spec/containers/0/resources/requests/memory
      value: `
  - `kustomize.config.k8s.io/v1beta1`

**modules/unicode_utils_v2/k8s/rbac.yaml**:
  - `]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: prometheus
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: prometheus
subjects:
- kind: ServiceAccount
  name: prometheus
  namespace: monitoring
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: unicode-utils-api
  namespace: unicode-utils
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: unicode-utils
  name: unicode-utils-role
rules:
- apiGroups: [`

**modules/unicode_utils_v2/monitoring/prometheus_config.yaml**:
  - `
    kubernetes_sd_configs:
    - role: pod
      namespaces:
        names:
        - unicode-utils
    relabel_configs:
    - source_labels: [__meta_kubernetes_pod_label_app]
      action: keep
      regex: unicode-utils
    - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
      action: keep
      regex: true
    - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
      action: replace
      target_label: __metrics_path__
      regex: (.+)
    - source_labels: [__address__, __meta_kubernetes_pod_annotation_prometheus_io_port]
      action: replace
      regex: ([^:]+)(?::\d+)?;(\d+)
      replacement: $1:$2
      target_label: __address__
    - action: labelmap
      regex: __meta_kubernetes_pod_label_(.+)
    - source_labels: [__meta_kubernetes_namespace]
      action: replace
      target_label: kubernetes_namespace
    - source_labels: [__meta_kubernetes_pod_name]
      action: replace
      target_label: kubernetes_pod_name

  # Kubernetes metrics
  - job_name: `
  - `
    kubernetes_sd_configs:
    - role: endpoints
    scheme: https
    tls_config:
      ca_file: /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
    bearer_token_file: /var/run/secrets/kubernetes.io/serviceaccount/token
    relabel_configs:
    - source_labels: [__meta_kubernetes_namespace, __meta_kubernetes_service_name, __meta_kubernetes_endpoint_port_name]
      action: keep
      regex: default;kubernetes;https

  # Node exporter
  - job_name: `
  - `http://thanos-receive:19291/api/v1/receive`
  - `/api/v1/nodes/${1}/proxy/metrics`
  - `
    kubernetes_sd_configs:
    - role: node
    relabel_configs:
    - action: labelmap
      regex: __meta_kubernetes_node_label_(.+)
    - target_label: __address__
      replacement: kubernetes.default.svc:443
    - source_labels: [__meta_kubernetes_node_name]
      regex: (.+)
      target_label: __metrics_path__
      replacement: /api/v1/nodes/${1}/proxy/metrics

  # NVIDIA GPU metrics (if available)
  - job_name: `

**modules/unicode_utils_v2/k8s/istio/security.yaml**:
  - `//api.unicode-utils.com/.well-known/jwks.json`
  - `type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit`
  - `https://api.unicode-utils.com/.well-known/jwks.json`
  - `]
---
apiVersion: security.istio.io/v1beta1
kind: RequestAuthentication
metadata:
  name: unicode-utils-jwt
  namespace: unicode-utils
spec:
  selector:
    matchLabels:
      app: unicode-utils-api
  jwtRules:
  - issuer: `
  - `//api.unicode-utils.com`
  - `type.googleapis.com/udpa.type.v1.TypedStruct`
  - `
---
apiVersion: networking.istio.io/v1beta1
kind: EnvoyFilter
metadata:
  name: unicode-utils-rate-limit
  namespace: unicode-utils
spec:
  workloadSelector:
    labels:
      app: unicode-utils-api
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: SIDECAR_INBOUND
      listener:
        filterChain:
          filter:
            name: `
  - `/api/*`
  - `: type.googleapis.com/udpa.type.v1.TypedStruct
          type_url: type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit
          value:
            stat_prefix: unicode_utils_rate_limiter
            token_bucket:
              max_tokens: 1000
              tokens_per_fill: 1000
              fill_interval: 60s
            filter_enabled:
              runtime_key: unicode_utils_rate_limit_enabled
              default_value:
                numerator: 100
                denominator: HUNDRED
            filter_enforced:
              runtime_key: unicode_utils_rate_limit_enforced
              default_value:
                numerator: 100
                denominator: HUNDRED
            response_headers_to_add:
            - append: false
              header:
                key: x-local-rate-limit
                value: `

**modules/unicode_utils_v2/k8s/monitoring/prometheus.yaml**:
  - `

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: prometheus
  namespace: monitoring
  labels:
    app: prometheus
spec:
  replicas: 1
  selector:
    matchLabels:
      app: prometheus
  template:
    metadata:
      labels:
        app: prometheus
    spec:
      serviceAccountName: prometheus
      containers:
      - name: prometheus
        image: prom/prometheus:v2.45.0
        ports:
        - containerPort: 9090
          name: prometheus
        args:
        - `
  - `
      kubernetes_sd_configs:
      - role: pod
        namespaces:
          names:
          - unicode-utils
      relabel_configs:
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: true
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
        action: replace
        target_label: __metrics_path__
        regex: (.+)
      - source_labels: [__address__, __meta_kubernetes_pod_annotation_prometheus_io_port]
        action: replace
        regex: ([^:]+)(?::\d+)?;(\d+)
        replacement: $1:$2
        target_label: __address__
      - action: labelmap
        regex: __meta_kubernetes_pod_label_(.+)
      - source_labels: [__meta_kubernetes_namespace]
        action: replace
        target_label: kubernetes_namespace
      - source_labels: [__meta_kubernetes_pod_name]
        action: replace
        target_label: kubernetes_pod_name
      
    # Redis monitoring
    - job_name: `
  - `
      kubernetes_sd_configs:
      - role: node
      scheme: https
      tls_config:
        ca_file: /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
      bearer_token_file: /var/run/secrets/kubernetes.io/serviceaccount/token
      relabel_configs:
      - action: labelmap
        regex: __meta_kubernetes_node_label_(.+)

    # Custom Unicode Utils metrics
    - job_name: `
  - `
      kubernetes_sd_configs:
      - role: endpoints
      scheme: https
      tls_config:
        ca_file: /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
      bearer_token_file: /var/run/secrets/kubernetes.io/serviceaccount/token
      relabel_configs:
      - source_labels: [__meta_kubernetes_namespace, __meta_kubernetes_service_name, __meta_kubernetes_endpoint_port_name]
        action: keep
        regex: default;kubernetes;https

    # Node metrics
    - job_name: `

**modules/unicode_utils_v2/k8s/monitoring/grafana.yaml**:
  - `/etc/grafana/provisioning/datasources`
  - `: 24}
          }
        ]
      }
    }
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: grafana
  namespace: monitoring
  labels:
    app: grafana
spec:
  replicas: 1
  selector:
    matchLabels:
      app: grafana
  template:
    metadata:
      labels:
        app: grafana
    spec:
      containers:
      - name: grafana
        image: grafana/grafana:10.1.0
        ports:
        - containerPort: 3000
          name: grafana
        env:
        - name: GF_SECURITY_ADMIN_PASSWORD
          value: `
  - `/api/health`
  - `
      type: file
      disableDeletion: false
      updateIntervalSeconds: 10
      allowUiUpdates: true
      options:
        path: /var/lib/grafana/dashboards
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-dashboard-unicode-utils
  namespace: monitoring
data:
  unicode-utils-dashboard.json: |
    {
      `

**modules/unicode_utils_v2/.github/workflows/ci-cd.yaml**:
  - ` | base64 -d > kubeconfig
        export KUBECONFIG=kubeconfig
        
        # Apply namespace and RBAC
        kubectl apply -f k8s/rbac.yaml
        
        # Deploy Redis
        kubectl apply -f k8s/redis.yaml
        
        # Deploy application
        envsubst < k8s/deployment.yaml | kubectl apply -f -
        kubectl apply -f k8s/hpa.yaml
        kubectl apply -f k8s/ingress.yaml
        
        # Apply Istio configs
        kubectl apply -f k8s/istio/
        
        # Deploy monitoring
        kubectl apply -f k8s/monitoring/
        
        # Wait for deployment
        kubectl rollout status deployment/unicode-utils-api -n unicode-utils --timeout=300s
        
        # Run smoke tests
        kubectl run smoke-test --rm -i --restart=Never --image=curlimages/curl -- \
          curl -f http://unicode-utils-service.unicode-utils.svc.cluster.local/health
      env:
        IMAGE_TAG: ${{ github.sha }}

  deploy-production:
    name: Deploy to Production
    runs-on: ubuntu-latest
    needs: build
    if: startsWith(github.ref, `
  - `) }}
        restore-keys: |
          ${{ runner.os }}-pip-
          
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        
    - name: Run unit tests
      run: |
        python -m pytest tests/unit/ -v --cov=unicode_utils --cov-report=xml --cov-report=html
        
    - name: Run integration tests
      run: |
        python -m pytest tests/integration/ -v --no-cov
        
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        flags: unittests
        name: codecov-umbrella
        
    - name: Performance baseline test
      run: |
        python performance_baseline.py
        
    - name: Store test artifacts
      uses: actions/upload-artifact@v3
      if: always()
      with:
        name: test-results-${{ matrix.python-version }}
        path: |
          coverage.xml
          htmlcov/
          performance_baseline_report.json

  security-scan:
    name: Security Scan
    runs-on: ubuntu-latest
    needs: test
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4
      
    - name: Run Trivy vulnerability scanner
      uses: aquasecurity/trivy-action@master
      with:
        scan-type: `
  - `
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4
      
    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v3
      
    - name: Log in to Container Registry
      uses: docker/login-action@v3
      with:
        registry: ${{ env.REGISTRY }}
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}
        
    - name: Extract metadata
      id: meta
      uses: docker/metadata-action@v5
      with:
        images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
        tags: |
          type=ref,event=branch
          type=ref,event=pr
          type=semver,pattern={{version}}
          type=semver,pattern={{major}}.{{minor}}
          type=semver,pattern={{major}}
          type=sha,prefix={{branch}}-
          
    - name: Build and push Docker image
      uses: docker/build-push-action@v5
      with:
        context: .
        platforms: linux/amd64,linux/arm64
        push: true
        tags: ${{ steps.meta.outputs.tags }}
        labels: ${{ steps.meta.outputs.labels }}
        cache-from: type=gha
        cache-to: type=gha,mode=max
        
    - name: Generate SBOM
      uses: anchore/sbom-action@v0
      with:
        image: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ steps.meta.outputs.version }}

  deploy-staging:
    name: Deploy to Staging
    runs-on: ubuntu-latest
    needs: build
    if: github.ref == `
  - `docker/metadata-action@v5`
  - ` | base64 -d > kubeconfig
        export KUBECONFIG=kubeconfig
        
        # Blue-green deployment strategy
        # Apply configurations
        kubectl apply -f k8s/rbac.yaml
        kubectl apply -f k8s/redis.yaml
        
        # Deploy new version
        envsubst < k8s/deployment.yaml | kubectl apply -f -
        kubectl apply -f k8s/hpa.yaml
        
        # Wait for rollout
        kubectl rollout status deployment/unicode-utils-api -n unicode-utils --timeout=600s
        
        # Run production health checks
        kubectl run prod-health-check --rm -i --restart=Never --image=curlimages/curl -- \
          curl -f http://unicode-utils-service.unicode-utils.svc.cluster.local/health
          
        # Update ingress only after successful deployment
        kubectl apply -f k8s/ingress.yaml
        kubectl apply -f k8s/istio/
        
        # Deploy monitoring stack
        kubectl apply -f k8s/monitoring/
        
        echo `

**data/languages/chinese.yaml**:
  - `Diacritic ambiguity: Lü/Lu/Lv/Lyu all used for 吕 in pinyin. Diacritic lost in many databases; confusion with Lu, Qiang. See also `

**data/languages/korean.yaml**:
  - `Probability, statistics; female mathematician; Helen/Harriet are common diaspora forms. H.R. Kim ambiguous in databases.`
  - `Probability, combinatorics. Jin-Ho/Jinho is one of the most common male forenames. Initials J.H. Kim lead to mass-collisions in all bibliographic databases.`
  - `Extremely common US/CA/AU diaspora cluster. Hundreds of mathematicians, physicists, engineers in Western databases with identical spelling.`
  - `Probability, combinatorics. Lim/Rim/Lin romanisations; J.H. Lim is a very ambiguous block in both domestic and diaspora databases.`

**data/languages/vietnamese.yaml**:
  - `Fields Medalist, all diacritics, Paris/Vietnam/US diaspora, initials collision in databases.`

**data/languages/indian.yaml**:
  - `Probability, statistics; Chakma tribal/NE Indian, high surname ambiguity in English databases.`
  - `Statistics, probability. Tripathy/Tripathi ambiguity in databases.`
  - `Statistics, combinatorics. Mukherjee/Mukhopadhyay/Mukerjee are commonly interchanged in databases; `

**data/languages/Iranian.yaml**:
  - `Probability, analysis. Rasouli/Rassouli/Rasuli all occur in English databases.`
  - `Probability, statistics. Many M. Jafari in Iranian/European databases.`
  - `Probability, combinatorics, statistics. Vakili/Vakily are both found in Western databases.`
  - `Mathematical logic, combinatorics. Sanei/Sanaei confusion, ambiguous in databases.`
  - `Algebra, geometry. Zadeh/Zadah, Khalilzada/Khalilzada all seen in databases.`

**data/languages/thai.yaml**:
  - `Probability, combinatorics. Surname/given order varies in foreign databases.`

**data/languages/backups/20250714_151600/chinese.yaml**:
  - `Diacritic ambiguity: Lü/Lu/Lv/Lyu all used for 吕 in pinyin. Diacritic lost in many databases; confusion with Lu, Qiang. See also `

**data/languages/backups/20250714_151600/korean.yaml**:
  - `Probability, statistics; female mathematician; Helen/Harriet are common diaspora forms. H.R. Kim ambiguous in databases.`
  - `Probability, combinatorics. Jin-Ho/Jinho is one of the most common male forenames. Initials J.H. Kim lead to mass-collisions in all bibliographic databases.`
  - `Extremely common US/CA/AU diaspora cluster. Hundreds of mathematicians, physicists, engineers in Western databases with identical spelling.`
  - `Probability, combinatorics. Lim/Rim/Lin romanisations; J.H. Lim is a very ambiguous block in both domestic and diaspora databases.`

**data/languages/backups/20250714_151600/vietnamese.yaml**:
  - `Fields Medalist, all diacritics, Paris/Vietnam/US diaspora, initials collision in databases.`

**data/languages/backups/20250714_151600/indian.yaml**:
  - `Probability, statistics; Chakma tribal/NE Indian, high surname ambiguity in English databases.`
  - `Statistics, probability. Tripathy/Tripathi ambiguity in databases.`
  - `Statistics, combinatorics. Mukherjee/Mukhopadhyay/Mukerjee are commonly interchanged in databases; `

**data/languages/backups/20250714_151600/thai.yaml**:
  - `Probability, combinatorics. Surname/given order varies in foreign databases.`

**data/languages/backups/20250714_152856/chinese.yaml**:
  - `Diacritic ambiguity: Lü/Lu/Lv/Lyu all used for 吕 in pinyin. Diacritic lost in many databases; confusion with
    Lu, Qiang. See also `

**data/languages/backups/20250714_152856/korean.yaml**:
  - `Probability, combinatorics. Lim/Rim/Lin romanisations; J.H. Lim is a very ambiguous block in both domestic and diaspora databases.`
  - `Extremely common US/CA/AU diaspora cluster. Hundreds of mathematicians, physicists, engineers in Western databases with identical spelling.`

**data/languages/backups/20250714_152856/vietnamese.yaml**:
  - `Fields Medalist, all diacritics, Paris/Vietnam/US diaspora, initials collision in databases.`

**data/languages/backups/20250714_152856/indian.yaml**:
  - `Probability, statistics; Chakma tribal/NE Indian, high surname ambiguity in English databases.`
  - `Statistics, probability. Tripathy/Tripathi ambiguity in databases.`
  - `Statistics, combinatorics. Mukherjee/Mukhopadhyay/Mukerjee are commonly interchanged in databases; `

**data/languages/backups/20250714_152856/thai.yaml**:
  - `Probability, combinatorics. Surname/given order varies in foreign databases.`

**data/languages/backups/20250714_153140/chinese.yaml**:
  - `Diacritic ambiguity: Lü/Lu/Lv/Lyu all used for 吕 in pinyin. Diacritic lost in many databases; confusion with
    Lu, Qiang. See also `

**data/languages/backups/20250714_153140/korean.yaml**:
  - ` spelling used in academic China and diaspora. D.H. Kang highly ambiguous.
  zbMATH: Kang, Dong-Hyun
Kang_Eunju:
  CanonicalLatin: Kang, Eun-Ju
  CanonicalWestern: Eun-Ju Kang
  CJK: 姜恩珠
  AllCommonVariants:
  - Kang Eun-Ju
  - Kang Eunjung
  - Kang Eun Ju
  - Eunjung Kang
  - Eun-Ju Kang
  - Eun Ju Kang
  - Kang, E.-J.
  - E.-J. Kang
  - E. Kang
  - 강은주
  - 姜恩珠
  MathSciNet: Kang, Eunju
  DiasporaFlags:
  - KR
  Comments: Probability, combinatorics. Female mathematician; Kang surname ambiguous with Kang/Khang in diaspora.
  zbMATH: Kang, Eunju
Kang_Hyun-Woo:
  CanonicalLatin: Kang, Hyun-Woo
  CanonicalWestern: Hyun-Woo Kang
  CJK: 姜賢佑
  AllCommonVariants:
  - Gang Hyun Woo
  - Gang Hyun-Woo
  - Gang Hyunwoo
  - Gang, H.-W.
  - H. Kang
  - H.-J. Kang
  - H.-W. Kang
  - Ho Jin Kang
  - Ho-Jin Kang
  - Hojin Kang
  - Hye Jung Kang
  - Hye-Jung Kang
  - Hyejung Kang
  - Hyun Woo Kang
  - Hyun-Woo Kang
  - Hyunwoo Kang
  - Kang Ho Jin
  - Kang Ho-Jin
  - Kang Hojin
  - Kang Hye Jung
  - Kang Hye-Jung
  - Kang Hyejung
  - Kang Hyun Woo
  - Kang Hyun-Woo
  - Kang Hyunwoo
  - Kang, H.-J.
  - Kang, H.-W.
  - 姜慧貞
  - 姜昊鎭
  - 姜炫宇
  - 姜賢佑
  - 강현우
  - 강혜정
  - 강호진
  MathSciNet: Kang, Hyun-Woo
  DiasporaFlags:
  - KR
  Comments: Probability, stochastic processes. Female mathematician. Kang/Kang (sometimes spelled Gang).
  zbMATH: Kang, Hyun-Woo
Kang_Sun-Young:
  CanonicalLatin: Kang, Sun-Young
  CanonicalWestern: Sun-Young Kang
  CJK: 姜善英
  AllCommonVariants:
  - Gang Su Min
  - Gang Su-Min
  - Gang Sumin
  - Gang Sun Young
  - Gang Sun-Young
  - Gang Sunyoung
  - Gang, S.-M.
  - Gang, S.-Y.
  - Kang Sang Min
  - Kang Sang Mook
  - Kang Sang-Min
  - Kang Sang-Mook
  - Kang Sangmin
  - Kang Sangmook
  - Kang Su Min
  - Kang Su-Min
  - Kang Sumin
  - Kang Sun Young
  - Kang Sun-Young
  - Kang Sunyoung
  - Kang, S.-M.
  - Kang, S.-Y.
  - S. Kang
  - S.-M. Kang
  - S.-Y. Kang
  - Sang Min Kang
  - Sang Mook Kang
  - Sang-Min Kang
  - Sang-Mook Kang
  - Sangmin Kang
  - Sangmook Kang
  - Su Min Kang
  - Su-Min Kang
  - Sumin Kang
  - Sun Young Kang
  - Sun-Young Kang
  - Sunyoung Kang
  - 姜善英
  - 姜相敏
  - 姜相黙
  - 姜秀敏
  - 강상묵
  - 강상민
  - 강선영
  - 강수민
  MathSciNet: Kang, Sun-Young
  DiasporaFlags:
  - JP
  - KR
  - US
  Comments: Probability, statistics. Female mathematician. Kang/Gang ambiguity (강/姜).
  zbMATH: Kang, Sun-Young
Kim_Bum-Soo:
  CanonicalLatin: Kim, Bum-Soo
  CanonicalWestern: Bum-Soo Kim
  CJK: 金範洙
  AllCommonVariants:
  - B. Kim
  - B. S. Kim
  - B.-J. Kim
  - B.-S. Kim
  - B.S. Kim
  - Baek Jin Kim
  - Baek-Jin Kim
  - Baekjin Kim
  - Ben Kim
  - Benjamin Kim
  - Bok Soon Kim
  - Bok-Soon Kim
  - Boksoon Kim
  - Bong Soo Kim
  - Bong-Soo Kim
  - Bongsoo Kim
  - Bum Soo Kim
  - Bum-Soo Kim
  - Bumsoo Kim
  - Kim Baek Jin
  - Kim Baek-Jin
  - Kim Baekjin
  - Kim Bok Soon
  - Kim Bok-Soon
  - Kim Boksoon
  - Kim Bong Soo
  - Kim Bong-Soo
  - Kim Bongsoo
  - Kim Bum Soo
  - Kim Bum-Soo
  - Kim Bumsoo
  - Kim, B.-J.
  - Kim, B.-S.
  - Kim, B.S.
  - 金伯鎭
  - 金奉洙
  - 金福順
  - 金範洙
  - 김백진
  - 김범수
  - 김복순
  - 김봉수
  MathSciNet: Kim, Bum-Soo
  DiasporaFlags:
  - JP
  - KR
  - US
  Comments: Probability, combinatorics. Ambiguous with Baekjin, Boksoon, Bongsoo; Ben/Benjamin Kim common in diaspora.
  zbMATH: Kim, Bum-Soo
Kim_Dong-Hyun:
  CanonicalLatin: Kim, Dong-Hyun
  CanonicalWestern: Dong-Hyun Kim
  CJK: 金東鉉
  AllCommonVariants:
  - D. H. Kim
  - D. Kim
  - D.-H. Kim
  - D.-W. Kim
  - D.H. Kim
  - Dae Hee Kim
  - Dae-Hee Kim
  - Daehee Kim
  - Daniel Kim
  - David Kim
  - Dong Hyun Kim
  - Dong Wook Kim
  - Dong-Hyun Kim
  - Dong-Wook Kim
  - Donghyun Kim
  - Dongwook Kim
  - Dylan Kim
  - Kim Dae Hee
  - Kim Dae-Hee
  - Kim Daehee
  - Kim Dong Hyun
  - Kim Dong Wook
  - Kim Dong-Hyun
  - Kim Dong-Wook
  - Kim Donghyun
  - Kim Dongwook
  - Kim, D.
  - Kim, D.-H.
  - Kim, D.-W.
  - Kim, D.H.
  - 金大熙
  - 金大爾
  - 金東旭
  - 金東鉉
  - 김대희
  - 김데이비드
  - 김동욱
  - 김동현
  MathSciNet: Kim, Dong-Hyun
  DiasporaFlags:
  - AU
  - CA
  - KR
  - UK
  - US
  Comments: Extremely common US/CA/AU diaspora cluster. Hundreds of mathematicians, physicists, engineers in Western databases
    with identical spelling.
  zbMATH: Kim, Dong-Hyun
Kim_Geunho:
  CanonicalLatin: Kim, Geun-Ho
  CanonicalWestern: Geun-Ho Kim
  CJK: 金根浩
  AllCommonVariants:
  - Kim Geunho
  - Kim Geun-Ho
  - Kim Geun Ho
  - Geunho Kim
  - Geun-Ho Kim
  - Geun Ho Kim
  - Kim, G.-H.
  - G.-H. Kim
  - G. Kim
  - 김근호
  - 金根浩
  MathSciNet: Kim, Geunho
  DiasporaFlags:
  - KR
  Comments: Probability, stochastic processes.
  zbMATH: Kim, Geunho
Kim_Hyeon-Su:
  CanonicalLatin: Kim, Hyeon-Su
  CanonicalWestern: Hyeon-Su Kim
  CJK: 金賢洙
  AllCommonVariants:
  - H. J. Kim
  - H. Kim
  - H. R. Kim
  - H. S. Kim
  - H. Y. Kim
  - H.-J. Kim
  - H.-R. Kim
  - H.-S. Kim
  - H.-Y. Kim
  - H.J. Kim
  - H.R. Kim
  - H.S. Kim
  - H.Y. Kim
  - Hae Young Kim
  - Hae-Young Kim
  - Haeyoung Kim
  - Hannah Kim
  - Harriet Kim
  - Hayley Kim
  - Hazel Kim
  - Heather Kim
  - Hee Sun Kim
  - Hee-Sun Kim
  - Heesun Kim
  - Heidi Kim
  - Helen Kim
  - Henry Kim
  - Ho Jin Kim
  - Ho Yong Kim
  - Ho-Jin Kim
  - Ho-Yong Kim
  - Hojin Kim
  - Howard Kim
  - Hoyong Kim
  - Hye Ran Kim
  - Hye Rin Kim
  - Hye-Ran Kim
  - Hye-Rin Kim
  - Hyeon Su Kim
  - Hyeon-Su Kim
  - Hyeonsu Kim
  - Hyeran Kim
  - Hyerin Kim
  - Hyun Jeong Kim
  - Hyun Joo Kim
  - Hyun Su Kim
  - Hyun-Jeong Kim
  - Hyun-Joo Kim
  - Hyun-Su Kim
  - Hyung Ju Kim
  - Hyung Jun Kim
  - Hyung-Ju Kim
  - Hyung-Jun Kim
  - Hyungju Kim
  - Hyungjun Kim
  - Hyunjeong Kim
  - Hyunjoo Kim
  - Hyunsu Kim
  - Kim Hae Young
  - Kim Hae-Young
  - Kim Haeyoung
  - Kim Hee Sun
  - Kim Hee-Sun
  - Kim Heesun
  - Kim Ho Jin
  - Kim Ho Yong
  - Kim Ho-Jin
  - Kim Ho-Yong
  - Kim Hojin
  - Kim Hoyong
  - Kim Hye Ran
  - Kim Hye Rin
  - Kim Hye-Ran
  - Kim Hye-Rin
  - Kim Hyeon Su
  - Kim Hyeon-Su
  - Kim Hyeonsu
  - Kim Hyeran
  - Kim Hyerin
  - Kim Hyun Jeong
  - Kim Hyun Joo
  - Kim Hyun-Jeong
  - Kim Hyun-Joo
  - Kim Hyun-Su
  - Kim Hyung Ju
  - Kim Hyung Jun
  - Kim Hyung-Ju
  - Kim Hyung-Jun
  - Kim Hyungju
  - Kim Hyungjun
  - Kim Hyunjoo
  - Kim Hyunsu
  - Kim, H.-J.
  - Kim, H.-R.
  - Kim, H.-S.
  - Kim, H.-Y.
  - Kim, H.J.
  - Kim, H.R.
  - Kim, H.S.
  - Kim, H.Y.
  - 金姬善
  - 金惠潾
  - 金惠蘭
  - 金昊容
  - 金昊珍
  - 金海榮
  - 金炫廷
  - 金炫珠
  - 金炯俊
  - 金炯周
  - 金賢洙
  - 金賢珠
  - 김해영
  - 김현수
  - 김현정
  - 김현주
  - 김형주
  - 김형준
  - 김혜란
  - 김혜린
  - 김호용
  - 김호진
  - 김희선
  MathSciNet: Kim, Hyeon-Su
  DiasporaFlags:
  - CA
  - KR
  - US
  Comments: Probability, statistics, female mathematician. Hyun-Joo/Hyun-Ju romanisation ambiguous. Hannah/Helen common in
    English publications.
  zbMATH: Kim, Hyeon-Su
Kim_Jae-Hoon:
  CanonicalLatin: Kim, Jae-Hoon
  CanonicalWestern: Jae-Hoon Kim
  CJK: 金在勳
  AllCommonVariants:
  - Gene Kim
  - J. H. Kim
  - J. Kim
  - J. S. Kim
  - J. Sim
  - J. Y. Kim
  - J.-H. Kim
  - J.-M. Kim
  - J.-S. Kim
  - J.-W. Kim
  - J.-W. Sim
  - J.-Y. Kim
  - J.H. Kim
  - J.S. Kim
  - J.Y. Kim
  - Jae Hoon Kim
  - Jae Kim
  - Jae Wook Kim
  - Jae Wook Sim
  - Jae-Hoon Kim
  - Jae-Wook Kim
  - Jae-Wook Sim
  - Jaehoon Kim
  - Jaewook Kim
  - Jaewook Sim
  - Jaeyoung Kim
  - James Kim
  - Janet Kim
  - Jay Kim
  - Jean Kim
  - Jenny Kim
  - Jessica Kim
  - Ji Hyun Kim
  - Ji Kim
  - Ji Yeon Kim
  - Ji Young Kim
  - Ji-Hyun Kim
  - Ji-Yeon Kim
  - Ji-Young Kim
  - Jihyun Kim
  - Jim Kim
  - Jin Ho Kim
  - Jin Kim
  - Jin-Ho Kim
  - Jinho Kim
  - Jiyeon Kim
  - Jiyoung Kim
  - Joan Kim
  - Jonathan Kim
  - Jong Kim
  - Jong Min Kim
  - Jong Seong Kim
  - Jong-Min Kim
  - Jong-Seong Kim
  - Jongmin Kim
  - Jongseong Kim
  - Joon Kim
  - Julia Kim
  - June Kim
  - Jung Hyun Kim
  - Jung Kim
  - Jung Sook Kim
  - Jung-Hyun Kim
  - Jung-Sook Kim
  - Junghyun Kim
  - Jungsook Kim
  - Kim J.
  - Kim Jae Hoon
  - Kim Jae Wook
  - Kim Jae-Hoon
  - Kim Jae-Wook
  - Kim Jaehoon
  - Kim Jaewook
  - Kim Ji Hyun
  - Kim Ji Yeon
  - Kim Ji Young
  - Kim Ji-Hyun
  - Kim Ji-Yeon
  - Kim Ji-Young
  - Kim Jihyun
  - Kim Jin Ho
  - Kim Jin-Ho
  - Kim Jinho
  - Kim Jiyeon
  - Kim Jiyoung
  - Kim Jong Min
  - Kim Jong Seong
  - Kim Jong-Min
  - Kim Jong-Seong
  - Kim Jongmin
  - Kim Jongseong
  - Kim Jung Hyun
  - Kim Jung Sook
  - Kim Jung-Hyun
  - Kim Jung-Sook
  - Kim Junghyun
  - Kim Jungsook
  - Kim, J.
  - Kim, J.-H.
  - Kim, J.-M.
  - Kim, J.-S.
  - Kim, J.-W.
  - Kim, J.-Y.
  - Kim, J.H.
  - Kim, J.S.
  - Kim, J.Y.
  - Shim Jae Wook
  - Shim Jae-Wook
  - Shim Jaewook
  - Shim, J.-W.
  - Sim Jae Wook
  - Sim Jae-Wook
  - Sim Jaewook
  - Sim, J.-W.
  - 沈載旭
  - 金在勳
  - 金廷鉉
  - 金智姸
  - 金智賢
  - 金知英
  - 金貞淑
  - 金載旭
  - 金鍾成
  - 金鍾旼
  - 金鎭鎬
  - 김*
  - 김재욱
  - 김재훈
  - 김정숙
  - 김정현
  - 김종민
  - 김종성
  - 김지연
  - 김지영
  - 김지현
  - 김진호
  - 심재욱
  MathSciNet: Kim, Jaehoon
  DiasporaFlags:
  - AU
  - CA
  - KR
  - US
  Comments: Probability, combinatorics; Jae-Hoon is the most common forename among male Kim mathematicians; initials J.H.
    Kim have many coexisting entries in MathSciNet, arXiv, and DBLP. Westernised variants (James, Jay) frequent in US/UK publishing.
  zbMATH: Kim, Jaehoon
Kim_Kyudong:
  CanonicalLatin: Kim, Kyu-Dong
  CanonicalWestern: Kyu-Dong Kim
  CJK: 金圭東
  AllCommonVariants:
  - Kim Kyudong
  - Kim Kyu-Dong
  - Kim Kyu Dong
  - Kyudong Kim
  - Kyu-Dong Kim
  - Kyu Dong Kim
  - Kim, K.-D.
  - K.-D. Kim
  - K. Kim
  - 김규동
  - 金圭東
  MathSciNet: Kim, Kyudong
  DiasporaFlags:
  - KR
  Comments: Probability, stochastic analysis.
  zbMATH: Kim, Kyudong
Kim_Min-Jeong:
  CanonicalLatin: Kim, Min-Jeong
  CanonicalWestern: Min-Jeong Kim
  CJK: 金玟廷
  AllCommonVariants:
  - Kim Mi Sook
  - Kim Mi Young
  - Kim Mi-Sook
  - Kim Mi-Young
  - Kim Min Jeong
  - Kim Min Sik
  - Kim Min-Jeong
  - Kim Min-Sik
  - Kim Minjeong
  - Kim Minsik
  - Kim Misook
  - Kim Miyoung
  - Kim, M.-J.
  - Kim, M.-S.
  - Kim, M.-Y.
  - Kim, M.J.
  - Kim, M.S.
  - Kim, M.Y.
  - M. J. Kim
  - M. Kim
  - M. S. Kim
  - M. Y. Kim
  - M.-J. Kim
  - M.-S. Kim
  - M.-Y. Kim
  - M.J. Kim
  - M.S. Kim
  - M.Y. Kim
  - Mi Sook Kim
  - Mi Young Kim
  - Mi-Sook Kim
  - Mi-Young Kim
  - Mimi Kim
  - Min Jeong Kim
  - Min Sik Kim
  - Min-Jeong Kim
  - Min-Sik Kim
  - Mina Kim
  - Minjeong Kim
  - Minnie Kim
  - Minsik Kim
  - Misook Kim
  - Miyoung Kim
  - 金玟廷
  - 金珉植
  - 金美淑
  - 金美英
  - 김미숙
  - 김미영
  - 김민식
  - 김민정
  MathSciNet: Kim, Min-Jeong
  DiasporaFlags:
  - CA
  - KR
  - US
  Comments: Probability, combinatorics. Major female cluster; all initials M.J. Kim are highly ambiguous; Mina and Minnie
    are common Westernised forenames.
  zbMATH: Kim, Min-Jeong
Kim_Sung-Hoon:
  CanonicalLatin: Kim, Sung-Hoon
  CanonicalWestern: Sung-Hoon Kim
  CJK: 金成勳
  AllCommonVariants:
  - Kim Sang Hoon
  - Kim Sang Il
  - Kim Sang-Hoon
  - Kim Sang-Il
  - Kim Sanghoon
  - Kim Sangil
  - Kim Seon Hee
  - Kim Seon-Hee
  - Kim Seonhee
  - Kim Soo Kyung
  - Kim Soo Min
  - Kim Soo-Kyung
  - Kim Soo-Min
  - Kim Sook Young
  - Kim Sook-Young
  - Kim Sookyoung
  - Kim Sookyung
  - Kim Soomin
  - Kim Su Hyeon
  - Kim Su-Hyeon
  - Kim SuHyeon
  - Kim Sun Young
  - Kim Sun-Young
  - Kim Sung Eun
  - Kim Sung Hoon
  - Kim Sung Jin
  - Kim Sung-Eun
  - Kim Sung-Hoon
  - Kim Sung-Jin
  - Kim Sungeun
  - Kim Sunghoon
  - Kim Sungjin
  - Kim Sunyoung
  - Kim, S.-E.
  - Kim, S.-H.
  - Kim, S.-I.
  - Kim, S.-J.
  - Kim, S.-K.
  - Kim, S.-M.
  - Kim, S.-Y.
  - Kim, S.H.
  - Kim, S.J.
  - Kim, S.K.
  - Kim, S.M.
  - Kim, S.Y.
  - S. H. Kim
  - S. J. Kim
  - S. K. Kim
  - S. Kim
  - S. M. Kim
  - S. Y. Kim
  - S.-E. Kim
  - S.-H. Kim
  - S.-I. Kim
  - S.-J. Kim
  - S.-K. Kim
  - S.-M. Kim
  - S.-Y. Kim
  - S.H. Kim
  - S.J. Kim
  - S.K. Kim
  - S.M. Kim
  - S.Y. Kim
  - Sam Kim
  - Samuel Kim
  - Sang Hoon Kim
  - Sang Il Kim
  - Sang-Hoon Kim
  - Sang-Il Kim
  - Sanghoon Kim
  - Sangil Kim
  - Seon Hee Kim
  - Seon-Hee Kim
  - Seonhee Kim
  - Shane Kim
  - Shawn Kim
  - Simon Kim
  - Simone Kim
  - Sonia Kim
  - Sonya Kim
  - Soo Kyung Kim
  - Soo Min Kim
  - Soo-Kyung Kim
  - Soo-Min Kim
  - Soo-Young Kim
  - Sook Young Kim
  - Sook-Young Kim
  - Sookyoung Kim
  - Sookyung Kim
  - Soomin Kim
  - Sophia Kim
  - Su Hyeon Kim
  - Su-Hyeon Kim
  - SuHyeon Kim
  - Sun Young Kim
  - Sun-Young Kim
  - Sung Eun Kim
  - Sung Hoon Kim
  - Sung Jin Kim
  - Sung-Eun Kim
  - Sung-Hoon Kim
  - Sung-Jin Kim
  - Sungeun Kim
  - Sunghoon Kim
  - Sungjin Kim
  - Sunyoung Kim
  - Susan Kim
  - Suyoung Kim
  - 金善英
  - 金宣姬
  - 金成勳
  - 金成恩
  - 金成鎭
  - 金淑英
  - 金相勳
  - 金相日
  - 金秀卿
  - 金秀敏
  - 金秀鉉
  - 김상일
  - 김상훈
  - 김선영
  - 김선희
  - 김성은
  - 김성진
  - 김성훈
  - 김수경
  - 김수민
  - 김수현
  - 김숙영
  MathSciNet: Kim, Sunghoon
  DiasporaFlags:
  - CA
  - KR
  - US
  Comments: Probability, analysis. S.H. Kim is an extremely common initial cluster. Samuel/Sam/Shawn Kim are frequently encountered
    in the US/UK/AU diaspora.
  zbMATH: Kim, Sunghoon
Kim_Young-Jin:
  CanonicalLatin: Kim, Young-Jin
  CanonicalWestern: Young-Jin Kim
  CJK: 金英鎭
  AllCommonVariants:
  - Kevin Kim
  - Kim Ye Seul
  - Kim Ye-Seul
  - Kim Yeseul
  - Kim Yong Jin
  - Kim Yong-Jin
  - Kim Yongjin
  - Kim Yoon Sook
  - Kim Yoon-Sook
  - Kim Yoonsook
  - Kim Young Hoon
  - Kim Young Ja
  - Kim Young Jin
  - Kim Young Soo
  - Kim Young Tae
  - Kim Young-Hoon
  - Kim Young-Ja
  - Kim Young-Jin
  - Kim Young-Soo
  - Kim Young-Tae
  - Kim Younghoon
  - Kim Youngja
  - Kim Youngjin
  - Kim Youngsoo
  - Kim Youngtae
  - Kim, Y.-H.
  - Kim, Y.-J.
  - Kim, Y.-S.
  - Kim, Y.-T.
  - Kim, Y.J.
  - Kim, Y.S.
  - Y. J. Kim
  - Y. Kim
  - Y. S. Kim
  - Y.-H. Kim
  - Y.-J. Kim
  - Y.-S. Kim
  - Y.-T. Kim
  - Y.J. Kim
  - Y.S. Kim
  - Ye Seul Kim
  - Ye-Seul Kim
  - Yeseul Kim
  - Yohan Kim
  - Yong Jin Kim
  - Yong-Jin Kim
  - Yongjin Kim
  - Yoon Sook Kim
  - Yoon-Sook Kim
  - Yoonsook Kim
  - Yosef Kim
  - Young Hoon Kim
  - Young Ja Kim
  - Young Jin Kim
  - Young Kim
  - Young Soo Kim
  - Young Tae Kim
  - Young-Hoon Kim
  - Young-Ja Kim
  - Young-Jin Kim
  - Young-Soo Kim
  - Young-Tae Kim
  - Younghoon Kim
  - Youngja Kim
  - Youngjin Kim
  - Youngsoo Kim
  - Youngtae Kim
  - Yuna Kim
  - Yvonne Kim
  - 金允淑
  - 金容鎭
  - 金榮勳
  - 金榮台
  - 金榮洙
  - 金英子
  - 金英鎭
  - 金藝瑟
  - 김영수
  - 김영자
  - 김영진
  - 김영태
  - 김영훈
  - 김예슬
  - 김용진
  - 김윤숙
  MathSciNet: Kim, Young-Jin
  DiasporaFlags:
  - CA
  - KR
  - US
  Comments: Probability, stochastic analysis; `
  - ` is also a globally recognised sports celebrity—maximal ambiguity in databases.
  zbMATH: Park, ChanHo
Park_Hee-Jung:
  CanonicalLatin: Park, Hee-Jung
  CanonicalWestern: Hee-Jung Park
  CJK: 朴熙貞
  AllCommonVariants:
  - Bak Hee-Jung
  - H. J. Park
  - H. Park
  - H.-J. Park
  - H.-N. Park
  - H.-S. Park
  - Han Na Park
  - Han-Na Park
  - Hanna Park
  - Hee Jung Park
  - Hee-Jung Bak
  - Hee-Jung Pak
  - Hee-Jung Park
  - Heejung Park
  - Hyun Jung Park
  - Hyun Soo Park
  - Hyun-Jung Park
  - Hyun-Soo Park
  - Hyunjung Park
  - Hyunsoo Park
  - Pak Hee-Jung
  - Park Han Na
  - Park Han-Na
  - Park Hanna
  - Park Hee Jung
  - Park Hee-Jung
  - Park Heejung
  - Park Hyun Jung
  - Park Hyun Soo
  - Park Hyun-Jung
  - Park Hyun-Soo
  - Park Hyunjung
  - Park Hyunsoo
  - Park, H.-J.
  - Park, H.-N.
  - Park, H.-S.
  - 朴炫廷
  - 朴炫洙
  - 朴熙貞
  - 朴韓娜
  - 박한나
  - 박현수
  - 박현정
  - 박희정
  MathSciNet: Park, Hee-Jung
  DiasporaFlags:
  - KR
  - US
  Comments: Probability, statistics, female mathematician. H.J. Park ambiguous with initials for both male and female mathematicians.
  zbMATH: Park, Hee-Jung
Park_Ji-Hye:
  CanonicalLatin: Park, Ji-Hye
  CanonicalWestern: Ji-Hye Park
  CJK: 朴智惠
  AllCommonVariants:
  - Bak Ji-Hye
  - J. H. Park
  - J. Park
  - J.-H. Park
  - J.-Y. Park
  - Jae Yong Park
  - Jae-Yong Park
  - Jaeyong Park
  - Ji Hye Park
  - Ji-Hye Bak
  - Ji-Hye Pak
  - Ji-Hye Park
  - Jihye Park
  - Jung Yun Park
  - Jung-Yun Park
  - Jungyun Park
  - Pak Ji-Hye
  - Park Jae Yong
  - Park Jae-Yong
  - Park Jaeyong
  - Park Ji Hye
  - Park Ji-Hye
  - Park Jihye
  - Park Jung Yun
  - Park Jung-Yun
  - Park Jungyun
  - Park, J.-H.
  - Park, J.-Y.
  - 朴智惠
  - 朴貞允
  - 朴載用
  - 박재용
  - 박정윤
  - 박지혜
  MathSciNet: Park, Ji-Hye
  DiasporaFlags:
  - KR
  Comments: Probability, combinatorics, female mathematician. Ji-Hye common modern forename.
  zbMATH: Park, Ji-Hye
Park_Miok:
  CanonicalLatin: Park, Mi-Ok
  CanonicalWestern: Mi-Ok Park
  CJK: 朴美玉
  AllCommonVariants:
  - Park Miok
  - Park Mi-Ok
  - Park Mi Ok
  - Miok Park
  - Mi-Ok Park
  - Mi Ok Park
  - Park, M.-O.
  - M.-O. Park
  - M. Park
  - 박미옥
  - 朴美玉
  MathSciNet: Park, Miok
  DiasporaFlags:
  - KR
  Comments: Probability, statistics. Female mathematician.
  zbMATH: Park, Miok
Park_Youngsoo:
  CanonicalLatin: Park, Young-Soo
  CanonicalWestern: Young-Soo Park
  CJK: 朴榮洙
  AllCommonVariants:
  - B. Park
  - B.-S. Park
  - Bong Soo Park
  - Bong-Soo Park
  - Bongsoo Park
  - Park Bong Soo
  - Park Bong-Soo
  - Park Bongsoo
  - Park Young Soo
  - Park Young-Soo
  - Park Youngsoo
  - Park, B.-S.
  - Park, Y.-S.
  - Y. Park
  - Y.-S. Park
  - Young Soo Park
  - Young-Soo Park
  - Youngsoo Park
  - 朴奉洙
  - 朴榮洙
  - 박봉수
  - 박영수
  MathSciNet: Park, Youngsoo
  DiasporaFlags:
  - KR
  Comments: Probability, random processes.
  zbMATH: Park, Youngsoo
Pyo_Jae-Hoon:
  CanonicalLatin: Pyo, Jae-Hoon
  CanonicalWestern: Jae-Hoon Pyo
  CJK: 表載勳
  AllCommonVariants:
  - Pyo Jae-Hoon
  - Pyo Jaehoon
  - Pyo Jae Hoon
  - Jae-Hoon Pyo
  - Jaehoon Pyo
  - Jae Hoon Pyo
  - Pyo, J.-H.
  - J.-H. Pyo
  - J. Pyo
  - 표재훈
  - 表載勳
  MathSciNet: Pyo, Jae-Hoon
  DiasporaFlags:
  - KR
  Comments: Probability, combinatorics. Rare surname (표/表).
  zbMATH: Pyo, Jae-Hoon
Rhee_Dong-Won:
  CanonicalLatin: Rhee, Dong-Won
  CanonicalWestern: Dong-Won Rhee
  CJK: 李東源
  AllCommonVariants:
  - D. Rhee
  - D.-S. Rhee
  - D.-W. Rhee
  - Dong Sung Rhee
  - Dong Won Rhee
  - Dong-Sung Rhee
  - Dong-Won Lee
  - Dong-Won Rhee
  - Dong-Won Ri
  - Dong-Won Yi
  - Dongsung Rhee
  - Dongwon Rhee
  - Lee Dong-Won
  - Rhee Dong Sung
  - Rhee Dong Won
  - Rhee Dong-Sung
  - Rhee Dong-Won
  - Rhee Dongsung
  - Rhee Dongwon
  - Rhee, D.-S.
  - Rhee, D.-W.
  - Ri Dong-Won
  - Yi Dong Sung
  - Yi Dong-Sung
  - Yi Dong-Won
  - Yi Dongsung
  - Yi, D.-S.
  - 李東源
  - 李東聖
  - 이동성
  - 이동원
  MathSciNet: Rhee, Dong-Won
  DiasporaFlags:
  - KR
  - US
  Comments: Probability, random graphs. Diaspora, North/South Korean romanisations, all alternates for `

**data/languages/backups/20250714_153140/vietnamese.yaml**:
  - `
  zbMATH: Le, Van Thanh
Nguyễn_Bảo_Châu:
  CanonicalLatin: Nguyễn, Bảo Châu
  CanonicalWestern: Bảo Châu Nguyễn
  AllCommonVariants:
  - Nguyen Bao Chau
  - Nguyễn Bảo Châu
  - Nguyen, Bao Chau
  - Nguyen, B.C.
  - Bao Chau Nguyen
  - Bảo Châu Nguyễn
  - Nguyen B.C.
  - N.B.C. Nguyen
  MathSciNet: Nguyen, Bao Chau
  DiasporaFlags:
  - VN
  - FR
  - US
  Comments: Fields Medalist, all diacritics, Paris/Vietnam/US diaspora, initials collision in databases.
  Han_Nom: `

**data/languages/backups/20250714_153140/indian.yaml**:
  - `Probability, statistics; Chakma tribal/NE Indian, high surname ambiguity in English databases.`
  - `Statistics, probability. Tripathy/Tripathi ambiguity in databases.`
  - `Statistics, combinatorics. Mukherjee/Mukhopadhyay/Mukerjee are commonly interchanged in databases; `

**data/languages/backups/20250714_152721/chinese.yaml**:
  - `Diacritic ambiguity: Lü/Lu/Lv/Lyu all used for 吕 in pinyin. Diacritic lost in many databases; confusion with Lu, Qiang. See also `

**data/languages/backups/20250714_152721/korean.yaml**:
  - `Probability, combinatorics. Lim/Rim/Lin romanisations; J.H. Lim is a very ambiguous block in both domestic and diaspora databases.`
  - `Extremely common US/CA/AU diaspora cluster. Hundreds of mathematicians, physicists, engineers in Western databases with identical spelling.`

**data/languages/backups/20250714_152721/vietnamese.yaml**:
  - `Fields Medalist, all diacritics, Paris/Vietnam/US diaspora, initials collision in databases.`

**data/languages/backups/20250714_152721/indian.yaml**:
  - `Probability, statistics; Chakma tribal/NE Indian, high surname ambiguity in English databases.`
  - `Statistics, probability. Tripathy/Tripathi ambiguity in databases.`
  - `Statistics, combinatorics. Mukherjee/Mukhopadhyay/Mukerjee are commonly interchanged in databases; `

**data/languages/backups/20250714_152721/thai.yaml**:
  - `Probability, combinatorics. Surname/given order varies in foreign databases.`

**docker-compose.external.yml**:
  - `//localhost:8070/api/version`
  - `http://localhost:8070/api/version`
  - `/opt/grobid/grobid-home/config`

**.venv/lib/python3.12/site-packages/playwright/driver/package/protocol.yml**:
  - `
      parameters:
        name: string
        location:
          type: object?
          properties:
            file: string
            line: number?
            column: number?

    tracingGroupEnd:
      title: Group end

    tracingStopChunk:
      internal: true
      parameters:
        mode:
          type: enum
          literals:
          - archive
          - discard
          - entries
      returns:
        # The artifact may be missing if the browser closes while tracing is being stopped.
        # Or it can be missing if client-side compression is taking place.
        artifact: Artifact?
        # For local mode, these are all entries.
        entries:
          type: array?
          items: NameValue

    tracingStop:
      internal: true


Artifact:
  type: interface

  initializer:
    absolutePath: string

  commands:

    pathAfterFinished:
      internal: true
      returns:
        value: string

    # Blocks path/failure/delete/context.close until saved to the local |path|.
    saveAs:
      internal: true
      parameters:
        path: string

    # Blocks path/failure/delete/context.close until the stream is closed.
    saveAsStream:
      internal: true
      returns:
        stream: Stream

    failure:
      internal: true
      returns:
        error: string?

    stream:
      internal: true
      returns:
        stream: Stream

    cancel:
      internal: true

    delete:
      internal: true


Stream:
  type: interface

  commands:

    read:
      internal: true
      parameters:
        size: number?
      returns:
        binary: binary

    close:
      internal: true


WritableStream:
  type: interface

  commands:

    write:
      internal: true
      parameters:
        binary: binary

    close:
      internal: true


CDPSession:
  type: interface

  commands:

    send:
      internal: true
      parameters:
        method: string
        params: json?
      returns:
        result: json

    detach:
      internal: true

  events:

    event:
      parameters:
        method: string
        params: json?


Electron:
  type: interface

  commands:

    launch:
      title: Launch electron
      parameters:
        executablePath: string?
        args:
          type: array?
          items: string
        cwd: string?
        env:
          type: array?
          items: NameValue
        timeout: number
        acceptDownloads:
          type: enum?
          literals:
          - accept
          - deny
          - internal-browser-default
        bypassCSP: boolean?
        colorScheme:
          type: enum?
          literals:
          - dark
          - light
          - no-preference
          - no-override
        extraHTTPHeaders:
          type: array?
          items: NameValue
        geolocation:
          type: object?
          properties:
            longitude: number
            latitude: number
            accuracy: number?
        httpCredentials:
          type: object?
          properties:
            username: string
            password: string
            origin: string?
        ignoreHTTPSErrors: boolean?
        locale: string?
        offline: boolean?
        recordVideo:
          type: object?
          properties:
            dir: string
            size:
              type: object?
              properties:
                width: number
                height: number
        strictSelectors: boolean?
        timezoneId: string?
        tracesDir: string?
        selectorEngines:
          type: array?
          items: SelectorEngine
        testIdAttributeName: string?

      returns:
        electronApplication: ElectronApplication


ElectronApplication:
  type: interface

  extends: EventTarget

  initializer:
    context: BrowserContext

  commands:

    browserWindow:
      internal: true
      parameters:
        page: Page
      returns:
        handle: JSHandle

    evaluateExpression:
      title: Evaluate
      parameters:
        expression: string
        isFunction: boolean?
        arg: SerializedArgument
      returns:
        value: SerializedValue

    evaluateExpressionHandle:
      title: Evaluate
      parameters:
        expression: string
        isFunction: boolean?
        arg: SerializedArgument
      returns:
        handle: JSHandle

    updateSubscription:
      internal: true
      parameters:
        event:
          type: enum
          literals:
          - console
        enabled: boolean

  events:
    close:
    console:
      parameters:
        $mixin: ConsoleMessage

Android:
  type: interface

  commands:

    devices:
      internal: true
      parameters:
        host: string?
        port: number?
        omitDriverInstall: boolean?
      returns:
        devices:
          type: array
          items: AndroidDevice

AndroidSocket:
  type: interface

  commands:
    write:
      internal: true
      parameters:
        data: binary

    close:
      internal: true

  events:
    data:
      parameters:
        data: binary
    close:

AndroidDevice:
  type: interface

  extends: EventTarget

  initializer:
    model: string
    serial: string

  commands:
    wait:
      hidden: Wait
      parameters:
        androidSelector: AndroidSelector
        state:
          type: enum?
          literals:
          - gone
        timeout: number

    fill:
      title: Fill `

**.github/workflows/update-badges.yml**:
  - `![Architectural Health](https://img.shields.io/badge/architectural%20health-{health_score}%2F100-{health_color})`
  - `//img.shields.io/badge/architectural%20health-{health_score}%2F100-{health_color})',`
  - `${{ steps.metrics.outputs.health_score }}/100`
  - `
          # Architectural Status Shield
          
          ```
          ┌─────────────────────────────────────┐
          │   ARCHITECTURAL HEALTH MONITOR      │
          ├─────────────────────────────────────┤
          │ Health Score: ${{ steps.metrics.outputs.health_score }}/100              │
          │ Violations:   ${{ steps.metrics.outputs.violations }}                │
          │ Largest File: ${{ steps.metrics.outputs.largest_file }} lines       │
          │ Status:       🔴 Critical           │
          └─────────────────────────────────────┘
          ```
          
          Last Updated: $(date -u +`
  - `🤖 Update architectural health badges
            
            - Health Score: ${{ steps.metrics.outputs.health_score }}/100
            - Violations: ${{ steps.metrics.outputs.violations }}
            - Largest File: ${{ steps.metrics.outputs.largest_file }} lines
            
            Generated by GitHub Actions`
  - ` >> $GITHUB_OUTPUT
      
      - name: Create badge JSON files
        run: |
          mkdir -p .github/badges
          
          # Health score badge
          cat > .github/badges/health-score.json << EOF
          {
            `

**.github/workflows/pr-architectural-checks.yml**:
  - `)) {
                fileViolationDetails = `
            <details>
            <summary>⚠️ Violations in Changed Files</summary>
            
            \`\`\`
            ${violations.substring(0, 3000)}
            \`\`\`
            
            </details>`;
              }
            } catch (e) {
              // No violations file
            }
            
            // Format score change
            const scoreChangeFormatted = scoreChange > 0 ? `+${scoreChange}` : scoreChange;
            const violationChangeFormatted = violationChange > 0 ? `+${violationChange}` : violationChange;
            
            const comment = `## ${impactEmoji} Architectural Impact Analysis
            
            This PR`
  - ` > file_violations.txt
            cat changed_files.txt | xargs python tools/file_size_check.py >> file_violations.txt 2>&1 || true
            
            # Check forbidden patterns
            echo -e `
  - ` >> file_violations.txt
            cat changed_files.txt | xargs python tools/forbidden_pattern_check.py >> file_violations.txt 2>&1 || true
            
            # Check single responsibility
            echo -e `
  - `)
            );
            
            if (botComment) {
              // Update existing comment
              await github.rest.issues.updateComment({
                owner: context.repo.owner,
                repo: context.repo.repo,
                comment_id: botComment.id,
                body: comment
              });
            } else {
              // Create new comment
              await github.rest.issues.createComment({
                owner: context.repo.owner,
                repo: context.repo.repo,
                issue_number: context.issue.number,
                body: comment
              });
            }
      
      - name: Set PR status
        if: always()
        uses: actions/github-script@v6
        with:
          script: |
            const scoreChange = parseFloat(`
  - ` >> file_violations.txt
            cat changed_files.txt | xargs python tools/secure_config_check.py >> file_violations.txt 2>&1 || true
            
            # Count total violations
            violation_count=$(grep -c `
  - `}
            
            ---
            💡 Run \`pre-commit run --all-files\` locally to check for violations before pushing.`;
            
            // Find existing comment
            const { data: comments } = await github.rest.issues.listComments({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: context.issue.number
            });
            
            const botComment = comments.find(comment => 
              comment.user.type === `
  - ` >> file_violations.txt
            cat changed_files.txt | xargs python tools/single_responsibility_check.py >> file_violations.txt 2>&1 || true
            
            # Check secure config
            echo -e `
  - `);
            
            // Get analysis results
            const baseScore = `

**.github/workflows/architectural-health.yml**:
  - `${healthScore}/100`
  - `
            }[status];
            
            // Create comment
            const comment = `## ${statusEmoji} Architectural Health Check
            
            **Health Score**: ${healthScore}/100
            **Status**: ${status.toUpperCase()}
            
            <details>
            <summary>📊 Analysis Details</summary>
            
            \`\`\`
            ${analysisOutput.substring(0, 2000)}
            \`\`\`
            
            </details>
            
            ---
            📚 [View Implementation Roadmap](../blob/main/IMPLEMENTATION_ROADMAP.md) | 🔍 [View Full Report](../actions/runs/${{ github.run_id }})`;
            
            // Post comment
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: comment
            });
      
      - name: Create Health Badge
        if: always()
        run: |
          health_score=${{ steps.arch-analysis.outputs.health_score }}
          
          # Determine badge color based on score
          if (( $(echo `
  - ` | head -20 | \
            xargs python tools/secure_config_check.py || true
      
      - name: Generate Violation Summary
        if: always()
        run: |
          echo `
  - `) as f:
                  reader = csv.reader(f)
                  data = list(reader)
              
              if len(data) > 1:
                  scores = [float(row[1]) for row in data]
                  latest = scores[-1]
                  previous = scores[-2] if len(scores) > 1 else latest
                  avg_7d = sum(scores[-7:]) / len(scores[-7:]) if len(scores) >= 7 else latest
                  
                  print(f`
  - ` | head -20 | \
            xargs python tools/forbidden_pattern_check.py || true
          
          # Configuration security
          echo `
  - `;
            }
            
            // Extract key metrics
            const healthScore = `
  - `
          python tools/file_size_check.py --show-all . || true
          
          # Forbidden patterns
          echo `
  - ` \
            --data `

**.github/workflows/architectural-reports.yml**:
  - ` \
              --data `
  - `)
          
          ## 🎯 Current Status
          
          ![Health Score](https://img.shields.io/badge/health-0.0%2F100-red)
          ![Violations](https://img.shields.io/badge/violations-1753-red)
          ![Trend](https://img.shields.io/badge/trend-stable-yellow)
          
          ## 📈 Key Metrics
          
          | Metric | Current | Target | Status |
          |--------|---------|--------|--------|
          | Health Score | 0.0 | 80.0 | 🔴 Critical |
          | Total Violations | 1,753 | <50 | 🔴 Critical |
          | Largest File | 4,779 lines | <500 | 🔴 Critical |
          | Files >500 lines | 27 | 0 | 🔴 Critical |
          
          ## 🏆 Top Priorities
          
          1. **Decompose monolithic files** - Starting with filename_checker.py (4,779 lines)
          2. **Eliminate forbidden patterns** - 1,497 instances of hardcoded values
          3. **Enforce single responsibility** - 103 files with multiple concerns
          4. **Fix dependency violations** - 110 architectural boundary violations
          
          ## 📅 Week-over-Week Progress
          
          | Week | Health Score | Violations | Progress |
          |------|--------------|------------|----------|
          | Current | 0.0 | 1,753 | Baseline |
          | Target (Week 2) | 10.0 | 1,500 | -14% violations |
          | Target (Week 4) | 25.0 | 1,000 | -43% violations |
          | Target (Week 8) | 50.0 | 500 | -71% violations |
          | Target (Week 16) | 80.0 | <50 | -97% violations |
          
          ## 📋 Action Items
          
          - [ ] Complete Phase 1: Architectural fitness functions
          - [ ] Begin Phase 2: Monolithic file decomposition
          - [ ] Implement secure configuration migration
          - [ ] Standardize error handling patterns
          
          ---
          
          View detailed report: [architectural_analysis_report.md](./architectural_analysis_report.md)
          View trends: [health_trends.png](./health_trends.png)
          EOF
      
      - name: Upload reports
        uses: actions/upload-artifact@v3
        with:
          name: architectural-reports-${{ github.run_number }}
          path: reports/
          retention-days: 90
      
      - name: Create release with report
        if: github.event.schedule == `
  - `;
            
            // Create release
            const release = await github.rest.repos.createRelease({
              owner: context.repo.owner,
              repo: context.repo.repo,
              tag_name: `architectural-report-${date}`,
              name: `Architectural Health Report - ${date}`,
              body: `## 📊 ${reportType.charAt(0).toUpperCase() + reportType.slice(1)} Architectural Health Report
              
              This automated report provides insights into the architectural health of the codebase.
              
              ### 📈 Summary
              - Health Score: 0.0/100
              - Total Violations: 1,753
              - Trend: Establishing baseline
              
              ### 📎 Attachments
              - Full analysis report
              - Trend visualizations
              - Detailed metrics
              
              View the [Implementation Roadmap](./IMPLEMENTATION_ROADMAP.md) for improvement plans.`,
              draft: false,
              prerelease: false
            });
            
            console.log(`Created release: ${release.data.html_url}`);
      
      - name: Send report notification
        if: always()
        run: |
          echo `

**modules/unicode_utils_v2/docker-compose.yml**:
  - `
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./database/init.sql:/docker-entrypoint-initdb.d/init.sql
    networks:
      - unicode-network
    restart: unless-stopped
    healthcheck:
      test: [`
  - `/app/data`
  - `
    environment:
      - UNICODE_UTILS_ENV=production
      - DATABASE_URL=postgresql://unicode_user:unicode_pass@postgres:5432/unicode_db
      - REDIS_URL=redis://redis:6379/0
      - WORKERS=4
    depends_on:
      - postgres
      - redis
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    networks:
      - unicode-network
    restart: unless-stopped
    healthcheck:
      test: [`
  - `
    command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    networks:
      - unicode-network
    restart: unless-stopped
    healthcheck:
      test: [`
  - `/var/lib/postgresql/data`
  - `/etc/grafana/provisioning/datasources`
  - `
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - `
  - `
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
    depends_on:
      - unicode-api
    networks:
      - unicode-network
    restart: unless-stopped

  # Monitoring - Prometheus
  prometheus:
    image: prom/prometheus:latest
    container_name: unicode-prometheus
    ports:
      - `

**modules/unicode_utils_v2/k8s/deployment.yml**:
  - `/app/data`

**modules/unicode_utils_v2/.github/workflows/ci.yml**:
  - `
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -e .[test,performance]
    
    - name: Run performance tests
      run: |
        pytest tests/test_performance.py -v --benchmark-only

  build:
    runs-on: ubuntu-latest
    needs: [test, quality]
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: `
  - `
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -e .[dev]
    
    - name: Run black
      run: black --check unicode_utils tests
    
    - name: Run flake8
      run: flake8 unicode_utils tests
    
    - name: Run mypy
      run: mypy unicode_utils
    
    - name: Run isort
      run: isort --check-only unicode_utils tests

  performance:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: `
  - `
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        flags: unittests
        name: codecov-umbrella

  quality:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: `

**architecture_validation_report.json**:
  - `\u26a0\ufe0f  Unexpected file in tests: .DS_Store`
  - `\u26a0\ufe0f  Unexpected file in tests: test_mathematician_name_validator.py`
  - `\u26a0\ufe0f  Unexpected file in tests: test_auth_manager.py.bak`
  - `\u26a0\ufe0f  Unexpected file in tests: test_filename_checker.py`
  - `\u26a0\ufe0f  Unexpected file in tests: test_pdf_parser.py.bak`
  - `\u26a0\ufe0f  Unexpected file in tests: test_main_like.py`
  - `\u26a0\ufe0f  Unexpected file in tests: test_metadata_fetcher.py`
  - `\u26a0\ufe0f  Unexpected file in tests: test_unicode_fix.py`
  - `\u26a0\ufe0f  Unexpected file in tests: test_utils.py`
  - `\u26a0\ufe0f  Unexpected file in tests: pytest_config.txt`
  - `\u26a0\ufe0f  Unexpected file in tests: test_basic_validation.py`
  - `\u26a0\ufe0f  Unexpected file in tests: test_downloader.py`
  - `\u26a0\ufe0f  Unexpected file in tests: test_pdf_parser.py`
  - `\u26a0\ufe0f  Unexpected file in tests: test_my_spellchecker.py`
  - `\u26a0\ufe0f  Unexpected file in tests: test_scanner.py`
  - `\u26a0\ufe0f  Unexpected file in tests: test_specific_files.py`
  - `\u26a0\ufe0f  Unexpected file in tests: test_paper_validator.py`
  - `\u26a0\ufe0f  Unexpected file in tests: test_math_detector.py`
  - `\u26a0\ufe0f  Unexpected file in tests: test_minimal.py`
  - `\u26a0\ufe0f  Unexpected file in tests: test_main.py`
  - `\u26a0\ufe0f  Unexpected file in tests: test_security.py`
  - `\u26a0\ufe0f  Unexpected file in tests: test_ito_possessive.py`
  - `\u26a0\ufe0f  Unexpected file in tests: test_auth_manager.py`
  - `\u26a0\ufe0f  Unexpected file in tests: test_reporter.py`
  - `\u26a0\ufe0f  Unexpected file in tests: pytest.ini`
  - `\u26a0\ufe0f  Unexpected file in tests: test_on_files.py`
  - `\u26a0\ufe0f  Unexpected file in tests: test_duplicate_detector.py`
  - `\u26a0\ufe0f  Unexpected file in tests: test_publisher_strategy.py`

**.claude/settings.local.json**:
  - `)\n\n# Test complete integration with all enhancements\nresults = mf.fetch_metadata_all_sources(\n    `
  - `\n)\n\nif results:\n    meta = results[0]\n    \n    # Check all enhanced metadata fields\n    enhanced_fields = [\n        `
  - `)\n    \n    # Test flattened output\n    flattened = mf.flatten_metadata_dict(meta)\n    flattened_fields = [f for f in enhanced_fields if f in flattened and flattened[f] != `
  - `)\n\n# Test complete metadata → download pipeline\nwith tempfile.TemporaryDirectory() as tmp_dir:\n    print(f`
  - `}\n    ]\n}\n\ncan_handle = strategy.can_handle(oa_metadata)\nurls = strategy.get_download_urls(oa_metadata)\n\nprint(f`
  - `\n)\n\nif results:\n    meta = results[0]\n    \n    # Check all claimed metadata fields\n    enhanced_fields = [\n        `
  - ` python tools/file_size_check.py non_existent_file.py)`
  - `Bash(CI=true python3 -m pytest tests/test_downloader.py -v)`
  - `\n    }\n    \n    # Test acquisition\n    attempts = engine.acquire_paper(metadata, tmp_dir)\n    successful = engine.get_successful_download(attempts)\n    \n    print(f`
  - `)\n    \n    # Test acquire_paper_by_metadata\n    file_path, attempts = dl.acquire_paper_by_metadata(\n        `
  - `Flattened metadata fields: {len(flattened_fields)}/{len(enhanced_fields)} present`
  - `)\n\ninst_strategy = dl.InstitutionalStrategy()\n\n# Test DOI metadata\ndoi_metadata = {`
  - `)\n    \n    # Test with DOI that should have open access\n    file_path, attempts = dl.acquire_paper_by_metadata(\n        `
  - `Bash(timeout 300 python -m pytest tests/ --tb=no --maxfail=999999)`
  - `Bash(CI=true python3 -m pytest tests/test_metadata_fetcher.py -v --tb=short)`
  - `Subject classification: {passed}/{len(test_cases)} tests passed`
  - `)\n\ntry:\n    from core.dependency_injection import setup_default_services\n    print(`
  - `Bash(PYTHONPATH=. python3 tests/test_utils.py)`
  - `Bash(CI=true python3 -m pytest tests/test_downloader.py -v --tb=short)`
  - `)\n\n# Test OpenAccessStrategy\nstrategy = dl.OpenAccessStrategy()\n\n# Test metadata that should have open access\noa_metadata = {\n    `
  - `)\n\n# Test with real metadata (but use temp directory)\nwith tempfile.TemporaryDirectory() as tmp_dir:\n    metadata = {\n        `
  - `Enhanced metadata fields: {present_fields}/{len(enhanced_fields)} populated`
  - `)\n\n# Test non-OA metadata\nnon_oa_metadata = {`
  - `}\ncan_handle_doi = inst_strategy.can_handle(doi_metadata)\nurls_doi = inst_strategy.get_download_urls(doi_metadata)\n\nprint(f`
  - `)\n\n# Test empty metadata\nempty_metadata = {}\ncan_handle_empty = inst_strategy.can_handle(empty_metadata)\nprint(f`
  - `//localhost:8070/api/isalive'',`
  - `Bash(CI=true python3 -m pytest tests/test_metadata_fetcher.py::test_extract_arxiv_info -v)`
  - `Bash(CI=true python3 -m pytest tests/ -v --tb=short)`
  - `)\n\n# Test with a mathematical paper\nresults = mf.fetch_metadata_all_sources(\n    `
  - `http://localhost:8070/api/isalive`
  - `Bash(PYTHONPATH=. python -m pytest tests/test_utils.py::test_load_yaml_and_wordlist -v)`
  - `)\n    print()\n    \n    # Test the flatten function\n    flattened = mf.flatten_metadata_dict(meta)\n    print(`
  - `Bash(CI=true python3 -m pytest tests/test_metadata_fetcher.py::test_enrich_metadata_with_subjects -v)`
  - `)\ntry:\n    from core.dependency_injection import DIContainer\n    print(`
  - `Bash(CI=true python3 -m pytest tests/test_metadata_fetcher.py::test_classify_mathematical_subject -v)`
  - `Bash(CI=true python3 -m pytest tests/test_metadata_fetcher.py -v)`
  - `: False}\ncan_handle_non_oa = strategy.can_handle(non_oa_metadata)\nprint(f`
  - `Bash(PYTHONPATH=. python3 tests/test_filename_checker.py)`
  - `)\n\ntry:\n    from core.dependency_injection import get_container\n    print(`

**.metadata_cache/62ffd3f39d5eacd2e48f075322200f363ba0f4265ca1c7b6f335ca10b207e644.json**:
  - `The training dataset encompasses two components: the first is the open-source UCSF-PDGM dataset, while the second is derived from MRI scans focused on brain tumors, conducted between December 2016 and March 2020 in the Department of Radiology at Shandong Provincial Hospital, China. These scans employed SCALE-PWI to produce quantitative CBV maps. The overall generation process for the latter dataset, intended for model training, adheres to a structured timeline (see details in the Methods section). It commences with a T2WI lasting 1 minute and 10 seconds, followed by precontrast-T1WI spanning 50 seconds. Next, a T2-FLAIR imaging is performed for 2 minutes and 30 seconds, succeeded by an ADC mapping that takes 1 minute and 17 seconds. Subsequently, the SCALE-PWI protocol involves three stages: Single-slice T1 Mapping (40 seconds), DSC MRI lasting 60 seconds, and a repeat of Single-slice T1 Mapping. A 46-second delay is observed after the initiation of these three steps, preceding the administration of a contrast agent. Following the SCALE-PWI stages, the protocol proceeds with a postcontrast T1WI lasting 50 seconds, culminating in a 3D T-MPRAGE scan spanning 5 minutes. The training dataset comprises 505 image sets originating from 256 patients, encompassing multiple test results per individual. The test set, meanwhile, consists of 216 image data sets from 206 patients, specifically including subtypes such as glioblastoma, brain metastasis, radionecrosis, and recurrence for validation purposes. The study was granted approval by the local ethics committee in Shandong Provincial Hospital (Issued No. 2019\u2013272), and all experiments adhered strictly to the principles outlined in the Declaration of Helsinki. Due to the retrospective nature of the study, the requirement for informed consent was waived.`

**.metadata_cache/2090c5d2f4429d6fcc57554f74f2fd625b72b00ff4768af4763ae04a8e3be145.json**:
  - `Provisions and economic capital for credit losses\u2020`

**.metadata_cache/7b8bee19b3a48ad1a71f81b3b5073f72bfe9e0a353402c94b2c10f6ece242ba2.json**:
  - `Provisions and economic capital for credit losses\u2020`

**.metadata_cache/94b56113d0a38827670000f94db9ddae84e0caa8ea4035fc77bd74cc29af9f7d.json**:
  - `10.1109/ithings-greencom-cpscom-smartdata-cybermatics55523.2022.00063`

**.metadata_cache/a49b41f45fb7c5aa26b2ea9f91fa7c99f0a468c38ff4657e6bce150407776a04.json**:
  - `Optimal dividend strategies in a Cramer\u2013Lundberg model with capital injections and administration costs`

**.metadata_cache/e1480ef26e3563a6ef6a59ff9a6f7f09259a9c5570906922de9d1899126f68b8.json**:
  - `s policy depends {\\it{essentially}} on the occurrence of . The hedging problems, in many directions, for this claim led to the question of studying the linear reflected-backward-stochastic differential equations (RBSDE hereafter), \\begin{equation*} \\begin{split} &dY_t=f(t)d(t\\wedge\\tau)+Z_tdW_{t\\wedge{\\tau}}+dM_t-dK_t,\\quad Y_{\\tau}=\\xi,\\\\ & Y\\geq S\\quad\\mbox{on}\\quad \\Lbrack0,\\tau\\Lbrack,\\quad \\displaystyle\\int_0^{\\tau}(Y_{s-}-S_{s-})dK_s=0\\quad P\\mbox{-a.s.}.\\end{split} \\end{equation*} This is the objective of this paper. For this RBSDE and without any further assumption on that might neglect any risk intrinsic to its stochasticity, we answer the following: a) What are the sufficient minimal conditions on the data that guarantee the existence of the solution to this RBSDE? b) How can we estimate the solution in norm using ? c) Is there an -RBSDE that is intimately related to the current one and how their solutions are related to each other? This latter question has practical and theoretical leitmotivs.`

**.metadata_cache/bcddbbed5e17aac6e7b64f84ed105b45b67438d26427248ff8e4ab73c73ad220.json**:
  - `Optimal dividend strategies in a Cramer\u2013Lundberg model with capital injections and administration costs`

**.metadata_cache/91ffd4c886f4c8b7b7e695a57c05396c280aec7faea4e6f3437a38a724c198ca.json**:
  - `Solutions for nonlinear Fokker\u2013Planck equations with measures as initial data and McKean-Vlasov equations`

**.metadata_cache/cddf1af40c90b171e2ff94ce5bfdbe55f8673be514fb65afef41daf880ea106e.json**:
  - `Solutions for nonlinear Fokker\u2013Planck equations with measures as initial data and McKean-Vlasov equations`

**.metadata_cache/ab0eac49b436f15f2367ec5743c65419a52b571bf543ae648b778e030163fdfc.json**:
  - `10.1109/ithings-greencom-cpscom-smartdata-cybermatics55523.2022.00063`

**.metadata_cache/ae0ca6ef4663e2c86979eccf186f8caa38f959e3cb7f9c293248f6af7572fa4e.json**:
  - `We investigate two-barriers-reflected backward stochastic differential equations with data from rank-based stochastic differential equation. More specifically, we focus on the solution of backward stochastic differential equations restricted to two prescribed upper-boundary and lower-boundary processes. We rigorously show that this solution gives a probabilistic expression to the viscosity solution of some obstacle problems for the corresponding parabolic partial differential equations. As an application, the pricing problem of an \u2026`

**.metadata_cache/7dd1440037e39a92efdc61e449dd77700f5159883678d0dc89e3a59017bb93fa.json**:
  - `Provisions and economic capital for credit losses\u2020`

**archive/consolidated/debug/test_results.json**:
  - `.......................                                                  [100%]\n\ud83c\udf89 All extreme tests passed! --auto-fix-authors is working correctly.\n23 passed in 0.23s\n`
  - `.......                                                                  [100%]\n\ud83c\udf89 All extreme tests passed! --auto-fix-authors is working correctly.\n7 passed in 0.63s\n`

**config/grobid/resources-registry.json**:
  - `data/models/ELMo/en/`
  - `data/models/ELMo/en/vocab.txt`
  - `data/models/ELMo/fr/`
  - `data/db`
  - `data/download`
  - `data/models/ELMo/fr/vocab.txt`

**.venv/lib/python3.12/site-packages/en_core_web_sm-3.7.1.dist-info/direct_url.json**:
  - `//github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.1/en_core_web_sm-3.7.1-py3-none-any.whl`
  - `https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.1/en_core_web_sm-3.7.1-py3-none-any.whl`

**.venv/lib/python3.12/site-packages/playwright/driver/package/api.json**:
  - `])\n```\n\n```py\nfrom playwright.sync_api import expect\n\n# ✓ Contains the right items in the right order\nexpect(page.locator(\`
  - `data_transfer = frame.evaluate_handle(\`
  - `: data_transfer})\n```\n\n```py\ndata_transfer = page.evaluate_handle(\`
  - `//nodejs.org/api/fs.html#fs_class_fs_readstream)↵or`
  - `));\n      }\n      browser.close();\n    }\n  }\n}\n```\n\n```py\nimport asyncio\nfrom playwright.async_api import async_playwright, Playwright\n\nasync def run(playwright: Playwright):\n    chromium = playwright.chromium\n    browser = await chromium.launch()\n    page = await browser.new_page()\n    for current_url in [\`
  - `If `true`, Playwright does not pass its own configurations args and only uses the ones from `args`. Dangerous\noption; use with care.`
  - `])\n```\n\n```py\nfrom playwright.sync_api import expect\n\n# ✓ Has the right items in the right order\nexpect(page.locator(\`
  - `//cs.chromium.org/chromium/src/third_party/icu/source/data/misc/metaZones.txt?rcl=faee8bc70570192d82d2978a71e2a615788597d1)↵for`
  - `Makes the assertion check for the opposite condition. For example, this code tests that the response status is not\nsuccessful:\n\n```js\nawait expect(response).not.toBeOK();\n```\n\n```java\nassertThat(response).not().isOK();\n```\n`
  - `//chromedevtools.github.io/devtools-protocol/).\n-`
  - `https://example.com/api/findBook`
  - `);\nawait browser.CloseAsync();\n```\n\nIt is possible to examine the request to decide the route action. For example, mocking all requests that contain\nsome post data, and leaving all other requests as is:\n\n```js\nawait context.route(`
  - `Path to a [HAR](http://www.softwareishard.com/blog/har-12-spec) file with prerecorded network data. If `path` is a\nrelative path, then it is resolved relative to the current working directory.`
  - `Terminates this instance of Playwright in case it was created bypassing the Python context manager. This is useful\nin REPL applications.\n\n```py\nfrom playwright.sync_api import sync_playwright\n\nplaywright = sync_playwright().start()\n\nbrowser = playwright.chromium.launch()\npage = browser.new_page()\npage.goto(\`
  - `//example.com/api/getText',`
  - `data_transfer = await frame.evaluate_handle(\`
  - `config`](https://support.mozilla.org/en-US/kb/about-config-editor-firefox).\n\nYou`
  - `https://example.com/api/getText`
  - `)\n    await browser.close()\n\nasync def main():\n    async with async_playwright() as playwright:\n        await run(playwright)\nasyncio.run(main())\n```\n\n```py\nfrom playwright.sync_api import sync_playwright, Playwright\n\ndef run(playwright: Playwright):\n    firefox = playwright.firefox\n    browser = firefox.launch()\n    page = browser.new_page()\n    page.goto(\`
  - `, { dataTransfer });\n```\n\n```java\nJSHandle dataTransfer = page.evaluateHandle(\`
  - `)\n# Make sure at least some part of element intersects viewport.\nawait expect(locator).to_be_in_viewport()\n# Make sure element is fully outside of viewport.\nawait expect(locator).not_to_be_in_viewport()\n# Make sure that at least half of the element intersects viewport.\nawait expect(locator).to_be_in_viewport(ratio=0.5)\n```\n\n```py\nfrom playwright.sync_api import expect\n\nlocator = page.get_by_role(\`
  - `))\n```\n\n```py\nfrom playwright.sync_api import expect\n\nlocator = page.locator(\`
  - `)\n    await browser.close()\n\nasync def main():\n    async with async_playwright() as playwright:\n        await run(playwright)\n\nasyncio.run(main())\n```\n\n```py\nfrom playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError\n\nwith sync_playwright() as p:\n    browser = p.chromium.launch()\n    page = browser.new_page()\n    try:\n      page.locator(\`
  - `)\n    # other actions...\n    await browser.close()\n\nasync def main():\n    async with async_playwright() as playwright:\n        await run(playwright)\nasyncio.run(main())\n```\n\n```py\nfrom playwright.sync_api import sync_playwright, Playwright\n\ndef run(playwright: Playwright):\n    chromium = playwright.chromium\n    browser = chromium.launch()\n    page = browser.new_page()\n    page.goto(\`
  - `Documentation on DevTools Protocol can be found here:↵[DevTools Protocol Viewer](https://chromedevtools.github.io/devtools-protocol/).`
  - `<button data-testid=\`
  - `    # api_request_context = await playwright.request.new_context(base_url=\`
  - `**NOTE** This API controls\n[Chromium Tracing](https://www.chromium.org/developers/how-tos/trace-event-profiling-tool) which is a low-level\nchromium-specific debugging tool. API to control [Playwright Tracing](../trace-viewer) could be found\n[here](./class-tracing).\n\nReturns the buffer with trace data.`
  - `)));\n      browser.close();\n    }\n  }\n}\n```\n\n```py\nimport asyncio\nfrom playwright.async_api import async_playwright, Playwright\n\nasync def run(playwright: Playwright):\n    webkit = playwright.webkit\n    browser = await webkit.launch()\n    context = await browser.new_context()\n    page = await context.new_page()\n    await page.goto(\`
  - `));\n  }\n}\n```\n\n```py\nimport re\nfrom playwright.async_api import Page, expect\n\nasync def test_navigates_to_login_page(page: Page) -> None:\n    # ..\n    await page.get_by_text(\`
  - `);\n      // other actions...\n      browser.close();\n    }\n  }\n}\n```\n\n```py\nimport asyncio\nfrom playwright.async_api import async_playwright, Playwright\n\nasync def run(playwright: Playwright):\n    chromium = playwright.chromium # or \`
  - `//playwright.dev/docs/api/class-testoptions#test-options-trace)`
  - `//chromedevtools.github.io/devtools-protocol/).`
  - `Provides an object that will be serialized as html form using `multipart/form-data` encoding and sent as this\nrequest body. If this parameter is specified `content-type` header will be set to `multipart/form-data` unless\nexplicitly provided. File values can be passed as file-like object containing file name, mime-type and its content.`
  - `) });\n```\n\n```py\nimport re\nfrom playwright.async_api import expect\n\nlocator = page.locator(\`
  - `});\n```\n\n```py\nfrom playwright.async_api import expect\n\nlocator = page.locator(\`
  - `)\n\nasync def main():\n    async with async_playwright() as playwright:\n        await run(playwright)\nasyncio.run(main())\n```\n\n```py\nfrom playwright.sync_api import sync_playwright, Playwright\n\ndef run(playwright: Playwright):\n    firefox = playwright.firefox\n    browser = firefox.launch()\n    page = browser.new_page()\n    page.goto(\`
  - `Dimensions of the recorded videos. If not specified the size will be equal to `viewport` scaled down to fit into\n800x800. If `viewport` is not configured explicitly the video size defaults to 800x450. Actual picture of each page\nwill be scaled down if necessary to fit the specified size.`
  - `,\n  }\n});\n```\n\n```java\nMap<String, Object> data = new HashMap();\ndata.put(\`
  - `Sends HTTP(S) [GET](https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods/GET) request and returns its\nresponse. The method will populate request cookies from the context and update context cookies from the response.\nThe method will automatically follow redirects.\n\n**Usage**\n\nRequest parameters can be configured with `params` option, they will be serialized into the URL search parameters:\n\n```js\n// Passing params as object\nawait request.get(`
  - `);\n});\n```\n\n```py\nfrom playwright.async_api import Page, expect\n\nasync def test_status_becomes_submitted(page: Page) -> None:\n    # ..\n    await page.locator(\`
  - `Provides an object that will be serialized as html form using `multipart/form-data` encoding and sent as↵this request body. If this parameter is specified `content-type` header will be set to `multipart/form-data`↵unless explicitly provided. File values can be passed as file-like object containing file name, mime-type and its content.`
  - `);\n    assertThat(response).isOK();\n  }\n}\n```\n\n```py\nfrom playwright.async_api import Page, expect\n\nasync def test_navigates_to_login_page(page: Page) -> None:\n    # ..\n    response = await page.request.get(`
  - `)\n\n\n    # Create a repository.\n    response = api_request_context.post(\n        \`
  - `, {\n  data: {\n    title: `
  - `,\n  data: {\n    title: `
  - `Provides an object that will be serialized as html form using `multipart/form-data` encoding and sent as this\nrequest body. If this parameter is specified `content-type` header will be set to `multipart/form-data` unless\nexplicitly provided. File values can be passed either as\n[`fs.ReadStream`](https://nodejs.org/api/fs.html#fs_class_fs_readstream) or as file-like object containing file\nname, mime-type and its content.`
  - `, { dataTransfer });\n```\n\n```java\n// Note you can only create DataTransfer in Chromium and Firefox\nJSHandle dataTransfer = frame.evaluateHandle(\`
  - `Maximum time to wait for in milliseconds. Defaults to `0` - no timeout. The default value can be changed via\n`actionTimeout` option in the config, or by using the [`method: BrowserContext.setDefaultTimeout`] or\n[`method: Page.setDefaultTimeout`] methods.`
  - `If `true`, Playwright does not pass its own configurations args and only uses the ones from `args`. Dangerous\noption; use with care. Defaults to `false`.`
  - `);\n  // other actions...\n  await browser.close();\n})();\n```\n\n```py\nimport asyncio\nfrom playwright.async_api import async_playwright, Playwright\n\nasync def run(playwright: Playwright):\n    webkit = playwright.webkit\n    iphone = playwright.devices[\`
  - `Firefox user preferences. Learn more about the Firefox user preferences at↵[`about:config`](https://support.mozilla.org/en-US/kb/about-config-editor-firefox).`
  - `//example.com/api/uploadForm',`
  - `data:text/html,<script>throw new Error(`
  - `> Stock browsers like Google Chrome and Microsoft Edge are suitable for tests that require proprietary media codecs for video playback. See [this article](https://www.howtogeek.com/202825/what%E2%80%99s-the-difference-between-chromium-and-chrome/) for other differences between Chromium and Chrome.↵[This article](https://chromium.googlesource.com/chromium/src/+/lkgr/docs/chromium_browser_vs_google_chrome.md)↵describes some differences for Linux users.`
  - `, new() { DataObject = data });\n```\n\nTo send form data to the server use `form` option. Its value will be encoded into the request body with\n`application/x-www-form-urlencoded` encoding (see below how to use `multipart/form-data` form encoding to send\nfiles):\n\n```js\nawait request.post(`
  - `Locate element by the test id.\n\n**Usage**\n\nConsider the following DOM structure.\n\n```html\n<button data-testid=\`
  - `);\n```\n\n**Details**\n\nThe snippet above dispatches the `click` event on the element. Regardless of the visibility state of the element,\n`click` is dispatched. This is equivalent to calling\n[element.click()](https://developer.mozilla.org/en-US/docs/Web/API/HTMLElement/click).\n\nUnder the hood, it creates an instance of an event based on the given `type`, initializes it with `eventInit`\nproperties and dispatches it on the element. Events are `composed`, `cancelable` and bubble by default.\n\nSince `eventInit` is event-specific, please refer to the events documentation for the lists of initial properties:\n- [DeviceMotionEvent](https://developer.mozilla.org/en-US/docs/Web/API/DeviceMotionEvent/DeviceMotionEvent)\n- [DeviceOrientationEvent](https://developer.mozilla.org/en-US/docs/Web/API/DeviceOrientationEvent/DeviceOrientationEvent)\n- [DragEvent](https://developer.mozilla.org/en-US/docs/Web/API/DragEvent/DragEvent)\n- [Event](https://developer.mozilla.org/en-US/docs/Web/API/Event/Event)\n- [FocusEvent](https://developer.mozilla.org/en-US/docs/Web/API/FocusEvent/FocusEvent)\n- [KeyboardEvent](https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent/KeyboardEvent)\n- [MouseEvent](https://developer.mozilla.org/en-US/docs/Web/API/MouseEvent/MouseEvent)\n- [PointerEvent](https://developer.mozilla.org/en-US/docs/Web/API/PointerEvent/PointerEvent)\n- [TouchEvent](https://developer.mozilla.org/en-US/docs/Web/API/TouchEvent/TouchEvent)\n- [WheelEvent](https://developer.mozilla.org/en-US/docs/Web/API/WheelEvent/WheelEvent)\n\nYou can also specify `JSHandle` as the property value if you want live objects to be passed into the event:\n\n```js\nconst dataTransfer = await page.evaluateHandle(() => new DataTransfer());\nawait locator.dispatchEvent(`
  - `https://dog.ceo/api/breeds/list/all`
  - `The `FormData` is used create form data that is sent via `APIRequestContext`.\n\n```java\nimport com.microsoft.playwright.options.FormData;\n// ...\nFormData form = FormData.create()\n    .set(\`
  - `);\n```\n\nUnder the hood, it creates an instance of an event based on the given `type`, initializes it with `eventInit`\nproperties and dispatches it on the element. Events are `composed`, `cancelable` and bubble by default.\n\nSince `eventInit` is event-specific, please refer to the events documentation for the lists of initial properties:\n- [DeviceMotionEvent](https://developer.mozilla.org/en-US/docs/Web/API/DeviceMotionEvent/DeviceMotionEvent)\n- [DeviceOrientationEvent](https://developer.mozilla.org/en-US/docs/Web/API/DeviceOrientationEvent/DeviceOrientationEvent)\n- [DragEvent](https://developer.mozilla.org/en-US/docs/Web/API/DragEvent/DragEvent)\n- [Event](https://developer.mozilla.org/en-US/docs/Web/API/Event/Event)\n- [FocusEvent](https://developer.mozilla.org/en-US/docs/Web/API/FocusEvent/FocusEvent)\n- [KeyboardEvent](https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent/KeyboardEvent)\n- [MouseEvent](https://developer.mozilla.org/en-US/docs/Web/API/MouseEvent/MouseEvent)\n- [PointerEvent](https://developer.mozilla.org/en-US/docs/Web/API/PointerEvent/PointerEvent)\n- [TouchEvent](https://developer.mozilla.org/en-US/docs/Web/API/TouchEvent/TouchEvent)\n- [WheelEvent](https://developer.mozilla.org/en-US/docs/Web/API/WheelEvent/WheelEvent)\n\nYou can also specify `JSHandle` as the property value if you want live objects to be passed into the event:\n\n```js\n// Note you can only create DataTransfer in Chromium and Firefox\nconst dataTransfer = await frame.evaluateHandle(() => new DataTransfer());\nawait frame.dispatchEvent(`
  - `Asserts that the target element matches the given [accessibility snapshot](../aria-snapshots.md).\n\nSnapshot is stored in a separate `.aria.yml` file in a location configured by\n`expect.toMatchAriaSnapshot.pathTemplate` and/or `snapshotPathTemplate` properties in the configuration file.\n\n**Usage**\n\n```js\nawait expect(page.locator(`
  - `Form data to be serialized as html form using `application/x-www-form-urlencoded` encoding and sent as this request\nbody.`
  - `The `WebSocket` class represents WebSocket connections within a page. It provides the ability to inspect and\nmanipulate the data being transmitted and received.\n\nIf you want to intercept or modify WebSocket frames, consider using `WebSocketRoute`.`
  - `] == REPO\n\n    # Delete a repository.\n    response = api_request_context.delete(\n        f\`
  - `//nodejs.org/api/fs.html#fs_class_fs_readstream)`
  - `, arg);\n```\n\n```py\n# note you can only create data_transfer in chromium and firefox\ndata_transfer = await page.evaluate_handle(\`
  - `: data_transfer })\n```\n\n```py\n# note you can only create data_transfer in chromium and firefox\ndata_transfer = frame.evaluate_handle(\`
  - `: data_transfer })\n```\n\n```csharp\nvar dataTransfer = await page.EvaluateHandleAsync(\`
  - `);\n```\n\n```py\nfrom playwright.async_api import expect\n\nlocator = page.locator(\`
  - `t record test assertions (like `expect` calls). We recommend [enabling tracing through Playwright Test configuration](https://playwright.dev/docs/api/class-testoptions#test-options-trace), which includes those assertions and provides a more complete trace for debugging test failures.`
  - `JSHandle dataTransfer = frame.evaluateHandle(\`
  - `You can also send files as fields of an html form. The data will be encoded using [`multipart/form-data`](https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods/POST):`
  - `The `GenericAssertions` class provides assertion methods that can be used to make assertions about any values in\nthe tests. A new instance of `GenericAssertions` is created by calling\n[`method: PlaywrightAssertions.expectGeneric`]:\n\n```js\nimport { test, expect } from `
  - `, arg);\n```\n\n```py\ndata_transfer = await page.evaluate_handle(\`
  - `//nodejs.org/api/events.html#events_class_eventemitter)`
  - `)\n```\n\n```py\nfrom playwright.sync_api import expect\n\nlocator = page.get_by_role(\`
  - `Emulates consistent viewport for each page. Defaults to an 1280x720 viewport. Use `ViewportSize.NoViewport` to\ndisable the consistent viewport emulation. Learn more about [viewport emulation](../emulation.md#viewport).\n\n**NOTE** The `ViewportSize.NoViewport` value opts out from the default presets, makes viewport depend on the host\nwindow size defined by the operating system. It makes the execution of the tests non-deterministic.\n`
  - `https://example.com/api/uploadTeamList\`
  - ` in route.request.post_data):\n    route.fulfill(body=\`
  - `)\nawait expect(locator).to_be_hidden()\n```\n\n```py\nfrom playwright.sync_api import expect\n\nlocator = page.locator(`
  - `data_transfer = page.evaluate_handle(\`
  - `))\n```\n\n```py\nimport re\nfrom playwright.sync_api import expect\n\nlocator = page.locator(\`
  - `https://example.com/api/createBook`
  - `)\nawait expect(locator).to_be_disabled()\n```\n\n```py\nfrom playwright.sync_api import expect\n\nlocator = page.locator(\`
  - `Maximum operation time in milliseconds. Defaults to `0` - no timeout. The default value can be changed via\n`navigationTimeout` option in the config, or by using the [`method: BrowserContext.setDefaultNavigationTimeout`],\n[`method: BrowserContext.setDefaultTimeout`], [`method: Page.setDefaultNavigationTimeout`] or\n[`method: Page.setDefaultTimeout`] methods.`
  - `))\n```\n\n```py\nimport re\nfrom playwright.sync_api import expect\n\n# ...\nexpect(page).to_have_title(re.compile(r\`
  - `);\n```\n\n```py\nimport re\nfrom playwright.async_api import expect\n\n# ...\nawait expect(page).to_have_url(re.compile(\`
  - `Form data to be serialized as html form using `multipart/form-data` encoding and sent as this request body.`
  - `//example.com/api/uploadScript'\`
  - `The `RequestOptions` allows to create form data to be sent via `APIRequestContext`. Playwright will automatically\ndetermine content type of the request.\n\n```java\ncontext.request().post(\n  \`
  - `)\n```\n\n```py\nfrom playwright.sync_api import expect\n\nlocator = page.locator(\`
  - `)\n```\n\n```py\nfrom playwright.sync_api import Page, expect\n\ndef test_status_becomes_submitted(page: Page) -> None:\n    # ..\n    page.get_by_role(\`
  - `// Pass file path to the form data constructor:`
  - `);\n     browser.close();\n   }\n }\n}\n```\n\n```py\nimport asyncio\nfrom playwright.async_api import async_playwright, Playwright\n\nasync def run(playwright: Playwright):\n    firefox = playwright.firefox\n    browser = await firefox.launch()\n    page = await browser.new_page()\n    await page.goto(\`
  - `Provides `FormData` object that will be serialized as html form using `multipart/form-data` encoding and sent as\nthis request body. If this parameter is specified `content-type` header will be set to `multipart/form-data` unless\nexplicitly provided.`
  - `\n}\napi_request_context.get(\`
  - `)\n    await expect(response).to_be_ok()\n```\n\n```py\nfrom playwright.sync_api import Page, expect\n\ndef test_navigates_to_login_page(page: Page) -> None:\n    # ..\n    response = page.request.get(`
  - `)\n\n    # Create a repository.\n    response = await api_request_context.post(\n        \`
  - `));\n```\n\n```py\nimport re\nfrom playwright.async_api import expect\n\nlocator = page.locator(\`
  - `, true);\n```\n\n```py\nfrom playwright.async_api import expect\n\nlocator = page.locator(\`
  - `Snapshot is stored in a separate `.aria.yml` file in a location configured by `expect.toMatchAriaSnapshot.pathTemplate` and/or `snapshotPathTemplate` properties in the configuration file.`
  - `Waits for event to fire and passes its value into the predicate function. Returns when the predicate returns truthy\nvalue. Will throw an error if the application is closed before the event is fired. Returns the event data value.\n\n**Usage**\n\n```js\nconst windowPromise = electronApp.waitForEvent(`
  - `)).isEnabled();\n```\n\n```py\nfrom playwright.async_api import expect\n\nlocator = page.locator(\`
  - `)\n```\n\n```py\nfrom playwright.sync_api import Page, expect\n\ndef test_status_becomes_submitted(page: Page) -> None:\n    # ..\n    page.locator(\`
  - `))\n```\n\n```py\nimport re\nfrom playwright.sync_api import expect\n\nlocator = page.locator(`
  - `, dataTransfer);\nframe.dispatchEvent(\`
  - `);\n  }\n  await browser.close();\n})();\n```\n\n```py\nimport asyncio\nfrom playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError, Playwright\n\nasync def run(playwright: Playwright):\n    browser = await playwright.chromium.launch()\n    page = await browser.new_page()\n    try:\n      await page.locator(\`
  - `)).isHidden();\n```\n\n```py\nfrom playwright.async_api import expect\n\nlocator = page.locator(`
  - `)\n    await browser.close()\n\nasync def main():\n    async with async_playwright() as playwright:\n        await run(playwright)\nasyncio.run(main())\n```\n\n```py\nfrom playwright.sync_api import sync_playwright, Playwright\n\ndef run(playwright: Playwright):\n    webkit = playwright.webkit\n    browser = webkit.launch()\n    context = browser.new_context()\n    page = context.new_page()\n    page.goto(\`
  - `https://example.com/api/uploadForm`
  - `, RequestOptions.create().setData(data));\n```\n\n```python\ndata = {\n    \`
  - `);\n```\n\n```py\nfrom playwright.async_api import expect\n\nlocator = page.get_by_role(\`
  - `Whether to run browser in headless mode. More details for\n[Chromium](https://developers.google.com/web/updates/2017/04/headless-chrome) and\n[Firefox](https://hacks.mozilla.org/2017/12/using-headless-mode-in-firefox/). Defaults to `true` unless the\n`devtools` option is `true`.`
  - `, dataTransfer }\n});\n```\n`
  - `Ensures the response status code is within `200..299` range.\n\n**Usage**\n\n```js\nawait expect(response).toBeOK();\n```\n\n```java\nassertThat(response).isOK();\n```\n\n```py\nfrom playwright.async_api import expect\n\n# ...\nawait expect(response).to_be_ok()\n```\n\n```py\nimport re\nfrom playwright.sync_api import expect\n\n# ...\nexpect(response).to_be_ok()\n```\n`
  - `api_request_context.post(\`
  - `)).isEmpty();\n```\n\n```py\nfrom playwright.async_api import expect\n\nlocator = page.locator(\`
  - `Maximum time to wait for in milliseconds. Defaults to `0` - no timeout. The default value can be changed via\n`actionTimeout` option in the config, or by using the [`method: BrowserContext.setDefaultTimeout`] method.`
  - `//api.github.com\`
  - `Path to a User Data Directory, which stores browser session data like cookies and local storage. Pass an empty\nstring to create a temporary directory.\n\nMore details for\n[Chromium](https://chromium.googlesource.com/chromium/src/+/master/docs/user_data_dir.md#introduction) and\n[Firefox](https://wiki.mozilla.org/Firefox/CommandLineOptions#User_profile). Chromium`
  - `: data_transfer})\n```\n\n```py\n# note you can only create data_transfer in chromium and firefox\ndata_transfer = page.evaluate_handle(\`
  - `)));\n```\n\nYou can also send files as fields of an html form. The data will be encoded using\n[`multipart/form-data`](https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods/POST):\n\n```java\nPath path = Paths.get(\`
  - `//example.com/api/findBook\`
  - `api_request_context.get(\`
  - `);\n      browser.close();\n    }\n  }\n}\n```\n\n```py\nimport asyncio\nfrom playwright.async_api import async_playwright, Playwright\n\nasync def run(playwright: Playwright):\n    webkit = playwright.webkit\n    browser = await webkit.launch()\n    page = await browser.new_page()\n    await page.evaluate(\`
  - `,\n        },\n        data={\`
  - `);\n    }\n  }\n}\n```\n\n```py\nimport asyncio\nfrom playwright.async_api import async_playwright, Playwright\n\nasync def run(playwright: Playwright):\n    firefox = playwright.firefox\n    browser = await firefox.launch()\n    page = await browser.new_page()\n    await page.goto(\`
  - `//example.com/api/createBook\`
  - `, data=data)\n```\n\n```csharp\nvar data = new Dictionary<string, object>() {\n  { \`
  - `)\n    await browser.close()\n\nasync def main():\n    async with async_playwright() as playwright:\n        await run(playwright)\nasyncio.run(main())\n```\n\n```py\nfrom playwright.sync_api import sync_playwright, Playwright\n\ndef run(playwright: Playwright):\n    webkit = playwright.webkit\n    browser = webkit.launch()\n    page = browser.new_page()\n    page.evaluate(\`
  - `Allows to set post data of the request. If the data parameter is an object, it will be serialized to json string\nand `content-type` header will be set to `application/json` if not explicitly set. Otherwise the `content-type`\nheader will be set to `application/octet-stream` if not explicitly set.`
  - `Keyboard provides an api for managing a virtual keyboard. The high level api is [`method: Keyboard.type`], which takes↵raw characters and generates proper `keydown`, `keypress`/`input`, and `keyup` events on your page.`
  - `You probably want to [enable tracing in your config file](https://playwright.dev/docs/api/class-testoptions#test-options-trace) instead of using `context.tracing`.`
  - `Waits for event to fire and passes its value into the predicate function. Returns when the predicate returns truthy\nvalue. Will throw an error if the page is closed before the event is fired. Returns the event data value.\n\n**Usage**\n\n```js\n// Start waiting for download before clicking. Note no await.\nconst downloadPromise = page.waitForEvent(`
  - ``APIResponse` class represents responses returned by [`method: APIRequestContext.get`] and similar methods.\n\n```py\nimport asyncio\nfrom playwright.async_api import async_playwright, Playwright\n\nasync def run(playwright: Playwright):\n    context = await playwright.request.new_context()\n    response = await context.get(\`
  - `);\n```\n\nUnder the hood, it creates an instance of an event based on the given `type`, initializes it with `eventInit`\nproperties and dispatches it on the element. Events are `composed`, `cancelable` and bubble by default.\n\nSince `eventInit` is event-specific, please refer to the events documentation for the lists of initial properties:\n- [DeviceMotionEvent](https://developer.mozilla.org/en-US/docs/Web/API/DeviceMotionEvent/DeviceMotionEvent)\n- [DeviceOrientationEvent](https://developer.mozilla.org/en-US/docs/Web/API/DeviceOrientationEvent/DeviceOrientationEvent)\n- [DragEvent](https://developer.mozilla.org/en-US/docs/Web/API/DragEvent/DragEvent)\n- [Event](https://developer.mozilla.org/en-US/docs/Web/API/Event/Event)\n- [FocusEvent](https://developer.mozilla.org/en-US/docs/Web/API/FocusEvent/FocusEvent)\n- [KeyboardEvent](https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent/KeyboardEvent)\n- [MouseEvent](https://developer.mozilla.org/en-US/docs/Web/API/MouseEvent/MouseEvent)\n- [PointerEvent](https://developer.mozilla.org/en-US/docs/Web/API/PointerEvent/PointerEvent)\n- [TouchEvent](https://developer.mozilla.org/en-US/docs/Web/API/TouchEvent/TouchEvent)\n- [WheelEvent](https://developer.mozilla.org/en-US/docs/Web/API/WheelEvent/WheelEvent)\n\nYou can also specify `JSHandle` as the property value if you want live objects to be passed into the event:\n\n```js\n// Note you can only create DataTransfer in Chromium and Firefox\nconst dataTransfer = await page.evaluateHandle(() => new DataTransfer());\nawait elementHandle.dispatchEvent(`
  - `, dataTransfer);\nlocator.dispatchEvent(\`
  - `).count()\n    print(button_count)\n    await browser.close()\n\nasync def main():\n    async with async_playwright() as playwright:\n        await run(playwright)\n\nasyncio.run(main())\n```\n\n```py\nfrom playwright.sync_api import sync_playwright, Playwright\n\ndef run(playwright: Playwright):\n    tag_selector = \`
  - `var dataTransfer = await frame.EvaluateHandleAsync(\`
  - `)))\n    await browser.close()\n\nasync def main():\n    async with async_playwright() as playwright:\n        await run(playwright)\nasyncio.run(main())\n```\n\n```py\nfrom playwright.sync_api import sync_playwright, Playwright\n\ndef run(playwright: Playwright):\n    chromium = playwright.chromium\n    browser = chromium.launch()\n    page = browser.new_page()\n    for current_url in [\`
  - `Waits for event to fire and passes its value into the predicate function. Returns when the predicate returns truthy\nvalue. Will throw an error if the context closes before the event is fired. Returns the event data value.\n\n**Usage**\n\n```js\nconst pagePromise = context.waitForEvent(`
  - `));\n```\n\n**Uploading html form data**\n\n`FormData` class can be used to send a form to the server, by default the request will use\n`application/x-www-form-urlencoded` encoding:\n\n```java\ncontext.request().post(\`
  - `)\n    api_request_context = context.request\n    page = await context.new_page()\n\n    # Alternatively you can create a APIRequestContext manually without having a browser context attached:\n    # api_request_context = await playwright.request.new_context(base_url=\`
  - `).count();\nbrowser.close();\n```\n\n```py\nimport asyncio\nfrom playwright.async_api import async_playwright, Playwright\n\nasync def run(playwright: Playwright):\n    tag_selector = \`
  - `)\nawait expect(locator).to_be_focused()\n```\n\n```py\nfrom playwright.sync_api import expect\n\nlocator = page.get_by_role(\`
  - `);\n// Make sure at least some part of element intersects viewport.\nawait expect(locator).toBeInViewport();\n// Make sure element is fully outside of viewport.\nawait expect(locator).not.toBeInViewport();\n// Make sure that at least half of the element intersects viewport.\nawait expect(locator).toBeInViewport({ ratio: 0.5 });\n```\n\n```java\nLocator locator = page.getByRole(AriaRole.BUTTON);\n// Make sure at least some part of element intersects viewport.\nassertThat(locator).isInViewport();\n// Make sure element is fully outside of viewport.\nassertThat(locator).not().isInViewport();\n// Make sure that at least half of the element intersects viewport.\nassertThat(locator).isInViewport(new LocatorAssertions.IsInViewportOptions().setRatio(0.5));\n```\n\n```csharp\nvar locator = Page.GetByRole(AriaRole.Button);\n// Make sure at least some part of element intersects viewport.\nawait Expect(locator).ToBeInViewportAsync();\n// Make sure element is fully outside of viewport.\nawait Expect(locator).Not.ToBeInViewportAsync();\n// Make sure that at least half of the element intersects viewport.\nawait Expect(locator).ToBeInViewportAsync(new() { Ratio = 0.5 });\n```\n\n```py\nfrom playwright.async_api import expect\n\nlocator = page.get_by_role(\`
  - `});\n```\n\n```py\nfrom playwright.async_api import expect\n\n# ✓ Contains the right items in the right order\nawait expect(page.locator(\`
  - `, arg);\n```\n\n```py\n# note you can only create data_transfer in chromium and firefox\ndata_transfer = await frame.evaluate_handle(\`
  - `s native↵[`EventEmitter`](https://nodejs.org/api/events.html#events_class_eventemitter) methods, such as `on`, `once` or↵`removeListener`.`
  - `The `APIResponseAssertions` class provides assertion methods that can be used to make assertions about the\n`APIResponse` in the tests.\n\n```js\nimport { test, expect } from `
  - `)\nawait expect(locator).to_be_checked()\n```\n\n```py\nfrom playwright.sync_api import expect\n\nlocator = page.get_by_label(\`
  - `);\n```\n\nUnder the hood, it creates an instance of an event based on the given `type`, initializes it with `eventInit`\nproperties and dispatches it on the element. Events are `composed`, `cancelable` and bubble by default.\n\nSince `eventInit` is event-specific, please refer to the events documentation for the lists of initial properties:\n- [DeviceMotionEvent](https://developer.mozilla.org/en-US/docs/Web/API/DeviceMotionEvent/DeviceMotionEvent)\n- [DeviceOrientationEvent](https://developer.mozilla.org/en-US/docs/Web/API/DeviceOrientationEvent/DeviceOrientationEvent)\n- [DragEvent](https://developer.mozilla.org/en-US/docs/Web/API/DragEvent/DragEvent)\n- [Event](https://developer.mozilla.org/en-US/docs/Web/API/Event/Event)\n- [FocusEvent](https://developer.mozilla.org/en-US/docs/Web/API/FocusEvent/FocusEvent)\n- [KeyboardEvent](https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent/KeyboardEvent)\n- [MouseEvent](https://developer.mozilla.org/en-US/docs/Web/API/MouseEvent/MouseEvent)\n- [PointerEvent](https://developer.mozilla.org/en-US/docs/Web/API/PointerEvent/PointerEvent)\n- [TouchEvent](https://developer.mozilla.org/en-US/docs/Web/API/TouchEvent/TouchEvent)\n- [WheelEvent](https://developer.mozilla.org/en-US/docs/Web/API/WheelEvent/WheelEvent)\n\nYou can also specify `JSHandle` as the property value if you want live objects to be passed into the event:\n\n```js\n// Note you can only create DataTransfer in Chromium and Firefox\nconst dataTransfer = await page.evaluateHandle(() => new DataTransfer());\nawait page.dispatchEvent(`
  - `))\n```\n\n```py\nimport re\nfrom playwright.sync_api import expect\n\n# ...\nexpect(page).to_have_url(re.compile(\`
  - `//playwright.dev/docs/api/class-testoptions#test-options-trace),\nwhich`
  - `The common way to send file(s) in the body of a request is to upload them as form fields with `multipart/form-data` encoding. Use `FormData` to construct request body and pass it to the request as `multipart` parameter:`
  - `More details for↵[Chromium](https://chromium.googlesource.com/chromium/src/+/master/docs/user_data_dir.md#introduction) and↵[Firefox](https://wiki.mozilla.org/Firefox/CommandLineOptions#User_profile). Chromium`
  - `        data={\`
  - `A CDP websocket endpoint or http url to connect to. For example `http://localhost:9222/` or\n`ws://127.0.0.1:9222/devtools/browser/387adf4c-243f-4051-a181-46798f4a46f4`.`
  - `, new() { Form = formData });\n```\n\nThe common way to send file(s) in the body of a request is to upload them as form fields with `multipart/form-data`\nencoding. Use `FormData` to construct request body and pass it to the request as `multipart` parameter:\n\n```js\nconst form = new FormData();\nform.set(`
  - `Whether to run browser in headless mode. More details for↵[Chromium](https://developers.google.com/web/updates/2017/04/headless-chrome) and↵[Firefox](https://hacks.mozilla.org/2017/12/using-headless-mode-in-firefox/). Defaults to `true` unless the↵`devtools` option is `true`.`
  - `An acceptable ratio of pixels that are different to the total amount of pixels, between `0` and `1`. Default is\nconfigurable with `TestConfig.expect`. Unset by default.`
  - `))\n```\n\n```py\nimport re\nfrom playwright.sync_api import Page, expect\n\ndef test_navigates_to_login_page(page: Page) -> None:\n    # ..\n    page.get_by_text(\`
  - `//example.com/api/findBook',`
  - `);\nawait expect(locator).toBeFocused();\n```\n\n```java\nassertThat(page.getByRole(AriaRole.TEXTBOX)).isFocused();\n```\n\n```py\nfrom playwright.async_api import expect\n\nlocator = page.get_by_role(\`
  - `The `CDPSession` instances are used to talk raw Chrome Devtools Protocol:\n- protocol methods can be called with `session.send` method.\n- protocol events can be subscribed to with `session.on` method.\n\nUseful links:\n- Documentation on DevTools Protocol can be found here:\n  [DevTools Protocol Viewer](https://chromedevtools.github.io/devtools-protocol/).\n- Getting Started with DevTools Protocol:\n  https://github.com/aslushnikov/getting-started-with-cdp/blob/master/README.md\n\n```js\nconst client = await page.context().newCDPSession(page);\nawait client.send(`
  - `//example.com/api/createBook',`
  - `https://example.com/api/uploadScript\`
  - `] == REPO\n\n    # Delete a repository.\n    response = await api_request_context.delete(\n        f\`
  - `Optional dimensions of the recorded videos. If not specified the size will be equal to `viewport` scaled down to\nfit into 800x800. If `viewport` is not configured explicitly the video size defaults to 800x450. Actual picture of\neach page will be scaled down if necessary to fit the specified size.`
  - `\n    json_data = await response.json()\n    assert json_data[\`
  - `)])\n```\n\n```py\nimport re\nfrom playwright.sync_api import expect\n\nlocator = page.locator(\`
  - `Start tracing.\n\n**NOTE** You probably want to\n[enable tracing in your config file](https://playwright.dev/docs/api/class-testoptions#test-options-trace) instead\nof using `Tracing.start`.\n\nThe `context.tracing` API captures browser operations and network activity, but it doesn`
  - `, True)\n```\n\n```py\nfrom playwright.sync_api import expect\n\nlocator = page.locator(\`
  - `)\nawait expect(locator).to_have_count(3)\n```\n\n```py\nfrom playwright.sync_api import expect\n\nlocator = page.locator(\`
  - `// Set custom test id attribute from @playwright/test config:`
  - `)\nawait expect(locator).to_be_empty()\n```\n\n```py\nfrom playwright.sync_api import expect\n\nlocator = page.locator(\`
  - `An acceptable perceived color difference in the [YIQ color space](https://en.wikipedia.org/wiki/YIQ) between the\nsame pixel in compared images, between zero (strict) and one (lax), default is configurable with\n`TestConfig.expect`. Defaults to `0.2`.`
  - `/api/**`
  - `Path to a [HAR](http://www.softwareishard.com/blog/har-12-spec) file with prerecorded network data. If `path` is a relative path, then it is resolved relative to the current working directory.`
  - `, dataTransfer);\nelementHandle.dispatchEvent(\`
  - `api_request_context.fetch(\`
  - `To send form data to the server use `form` option. Its value will be encoded into the request body with `application/x-www-form-urlencoded` encoding (see below how to use `multipart/form-data` form encoding to send files):`
  - `//playwright.dev/docs/api/class-testoptions#test-options-trace),`
  - `API for collecting and saving Playwright traces. Playwright traces can be opened in\n[Trace Viewer](../trace-viewer.md) after Playwright script runs.\n\n**NOTE** You probably want to\n[enable tracing in your config file](https://playwright.dev/docs/api/class-testoptions#test-options-trace) instead\nof using `context.tracing`.\n\nThe `context.tracing` API captures browser operations and network activity, but it doesn`
  - `);\n```\n\n```py\nimport re\nfrom playwright.async_api import expect\n\nlocator = page.locator(`
  - `: data_transfer})\n```\n\n```csharp\nvar dataTransfer = await page.EvaluateHandleAsync(\`
  - `, RegexOptions.IgnoreCase)\n    })\n    .ClickAsync();\n```\n\n**Details**\n\nRole selector **does not replace** accessibility audits and conformance tests, but rather gives early feedback\nabout the ARIA guidelines.\n\nMany html elements have an implicitly [defined role](https://w3c.github.io/html-aam/#html-element-role-mappings)\nthat is recognized by the role selector. You can find all the\n[supported roles here](https://www.w3.org/TR/wai-aria-1.2/#role_definitions). ARIA guidelines **do not recommend**\nduplicating implicit roles and attributes by setting `role` and/or `aria-*` attributes to default values.`
  - `data.put(\`
  - `The common way to send file(s) in the body of a request is to upload them as form fields with `multipart/form-data` encoding, by specifiying the `multipart` parameter:`
  - `/api/v1`
  - `)\nawait expect(locator).to_be_editable()\n```\n\n```py\nfrom playwright.sync_api import expect\n\nlocator = page.get_by_role(\`
  - `Allows to set post data of the request. If the data parameter is an object, it will be serialized to json string↵and `content-type` header will be set to `application/json` if not explicitly set. Otherwise the `content-type` header will be↵set to `application/octet-stream` if not explicitly set.`
  - `Use [debugging tools](../debug.md) instead.`
  - `)\n    # other actions...\n    await browser.close()\n\nasync def main():\n    async with async_playwright() as playwright:\n        await run(playwright)\nasyncio.run(main())\n```\n\n```py\nfrom playwright.sync_api import sync_playwright, Playwright\n\ndef run(playwright: Playwright):\n    chromium = playwright.chromium # or \`
  - `//example.com/api/uploadTeamList\`
  - `The `LocatorAssertions` class provides assertion methods that can be used to make assertions about the `Locator`\nstate in the tests.\n\n```js\nimport { test, expect } from `
  - `Provides an object that will be serialized as html form using `multipart/form-data` encoding and sent as↵this request body. If this parameter is specified `content-type` header will be set to `multipart/form-data`↵unless explicitly provided. File values can be passed either as [`fs.ReadStream`](https://nodejs.org/api/fs.html#fs_class_fs_readstream)↵or as file-like object containing file name, mime-type and its content.`
  - `Keyboard provides an api for managing a virtual keyboard. The high level api is [`method: Keyboard.type`], which\ntakes raw characters and generates proper `keydown`, `keypress`/`input`, and `keyup` events on your page.\n\nFor finer control, you can use [`method: Keyboard.down`], [`method: Keyboard.up`], and\n[`method: Keyboard.insertText`] to manually fire events as if they were generated from a real keyboard.\n\nAn example of holding down `Shift` in order to select and delete some text:\n\n```js\nawait page.keyboard.type(`
  - `);\n      // other actions...\n      browser.close();\n    }\n  }\n}\n```\n\n```py\nimport asyncio\nfrom playwright.async_api import async_playwright, Playwright\n\nasync def run(playwright: Playwright):\n    chromium = playwright.chromium\n    browser = await chromium.launch()\n    page = await browser.new_page()\n    await page.goto(\`
  - `Emulates consistent viewport for each page. Defaults to an 1280x720 viewport. Use `null` to disable the consistent\nviewport emulation. Learn more about [viewport emulation](../emulation#viewport).\n\n**NOTE** The `null` value opts out from the default presets, makes viewport depend on the host window size defined\nby the operating system. It makes the execution of the tests non-deterministic.\n`
  - `).ClickAsync();\n```\n\n**Details**\n\nBy default, the `data-testid` attribute is used as a test id. Use [`method: Selectors.setTestIdAttribute`] to\nconfigure a different test id attribute if necessary.\n\n```js\n// Set custom test id attribute from @playwright/test config:\nimport { defineConfig } from `
  - `A CDP websocket endpoint or http url to connect to. For example `http://localhost:9222/` or `ws://127.0.0.1:9222/devtools/browser/387adf4c-243f-4051-a181-46798f4a46f4`.`
  - `If `true`, Playwright does not pass its own configurations args and only uses the ones from `args`. If an array is\ngiven, then filters out the given default arguments. Dangerous option; use with care. Defaults to `false`.`
  - `: data_transfer })\n```\n\n```py\n# note you can only create data_transfer in chromium and firefox\ndata_transfer = page.evaluate_handle(\`
  - `//example.com/api/getText\`
  - `//127.0.0.1:9222/devtools/browser/387adf4c-243f-4051-a181-46798f4a46f4`.`
  - `//chromium.googlesource.com/chromium/src/+/master/docs/user_data_dir.md#introduction)`
  - ` in route.request.post_data):\n    await route.fulfill(body=\`
  - `);\n  }\n}\n```\n\n```py\nfrom playwright.async_api import Page, expect\n\nasync def test_status_becomes_submitted(page: Page) -> None:\n    # ..\n    await page.get_by_role(\`
  - `Provides `FormData` object that will be serialized as html form using `multipart/form-data` encoding and sent as↵this request body. If this parameter is specified `content-type` header will be set to `multipart/form-data`↵unless explicitly provided.`
  - `).setData(data));\n```\n\n```python\ndata = {\n    \`
  - `, new { dataTransfer });\n```\n`
  - `);\nawait expect(locator).toBeEditable();\n```\n\n```java\nassertThat(page.getByRole(AriaRole.TEXTBOX)).isEditable();\n```\n\n```py\nfrom playwright.async_api import expect\n\nlocator = page.get_by_role(\`
  - `data:text/html,<script>throw new Error(\`
  - `,\n}\napi_request_context.fetch(\`
  - `)\nawait expect(locator).to_be_enabled()\n```\n\n```py\nfrom playwright.sync_api import expect\n\nlocator = page.locator(\`
  - `//cs.chromium.org/chromium/src/third_party/icu/source/data/misc/metaZones.txt?rcl=faee8bc70570192d82d2978a71e2a615788597d1)\nfor`
  - `, DataObject = data });\n```\n\nThe common way to send file(s) in the body of a request is to upload them as form fields with `multipart/form-data`\nencoding, by specifiying the `multipart` parameter:\n\n```js\nconst form = new FormData();\nform.set(`
  - `` - A connection timed out as a result of not receiving an ACK for data sent.\n- ``
  - `);\n```\n\n```py\nimport re\nfrom playwright.async_api import expect\n\n# ...\nawait expect(page).to_have_title(re.compile(r\`
  - `This API is used for the Web API testing. You can use it to trigger API endpoints, configure micro-services,\nprepare environment or the service to your e2e test.\n\nEach Playwright browser context has associated with it `APIRequestContext` instance which shares cookie storage\nwith the browser context and can be accessed via [`property: BrowserContext.request`] or\n[`property: Page.request`]. It is also possible to create a new APIRequestContext instance manually by calling\n[`method: APIRequest.newContext`].\n\n**Cookie management**\n\n`APIRequestContext` returned by [`property: BrowserContext.request`] and [`property: Page.request`] shares cookie\nstorage with the corresponding `BrowserContext`. Each API request will have `Cookie` header populated with the\nvalues from the browser context. If the API response contains `Set-Cookie` header it will automatically update\n`BrowserContext` cookies and requests made from the page will pick them up. This means that if you log in using\nthis API, your e2e test will be logged in and vice versa.\n\nIf you want API requests to not interfere with the browser cookies you should create a new `APIRequestContext` by\ncalling [`method: APIRequest.newContext`]. Such `APIRequestContext` object will have its own isolated cookie\nstorage.\n\n```py\nimport os\nimport asyncio\nfrom playwright.async_api import async_playwright, Playwright\n\nREPO = \`
  - `));\n```\n\n```py\nfrom playwright.async_api import expect\n\nlocator = page.locator(\`
  - `: data_transfer })\n```\n\n```csharp\n// Note you can only create DataTransfer in Chromium and Firefox\nvar dataTransfer = await frame.EvaluateHandleAsync(\`
  - `Form data to be serialized as html form using `multipart/form-data` encoding and sent as↵this request body.`
  - `t write any browsing data to disk.\n\n```js\n// Create a new incognito browser context\nconst context = await browser.newContext();\n// Create a new page inside context.\nconst page = await context.newPage();\nawait page.goto(`
  - `);\ndata.put(\`
  - `//dog.ceo/api/breeds/list/all\`
  - `)\n    # other actions...\n    await browser.close()\n\nasync def main():\n    async with async_playwright() as playwright:\n        await run(playwright)\nasyncio.run(main())\n```\n\n```py\nfrom playwright.sync_api import sync_playwright, Playwright\n\ndef run(playwright: Playwright):\n    webkit = playwright.webkit\n    iphone = playwright.devices[\`
  - `Install fake implementations for the following time-related functions:\n- `Date`\n- `setTimeout`\n- `clearTimeout`\n- `setInterval`\n- `clearInterval`\n- `requestAnimationFrame`\n- `cancelAnimationFrame`\n- `requestIdleCallback`\n- `cancelIdleCallback`\n- `performance`\n\nFake timers are used to manually control the flow of time in tests. They allow you to advance time, fire timers,\nand control the behavior of time-dependent functions. See [`method: Clock.runFor`] and\n[`method: Clock.fastForward`] for more information.`
  - `);\n```\n\nIt is possible to examine the request to decide the route action. For example, mocking all requests that contain\nsome post data, and leaving all other requests as is:\n\n```js\nawait page.route(`
  - `You probably want to [enable tracing in your config file](https://playwright.dev/docs/api/class-testoptions#test-options-trace) instead of using `Tracing.start`.`
  - `, dataTransfer);\npage.dispatchEvent(\`
  - `    assert json_data[\`
  - `,\n}\napi_request_context.post(\`
  - `)).isChecked();\n```\n\n```py\nfrom playwright.async_api import expect\n\nlocator = page.get_by_label(\`
  - `\n\nasync def main():\n    async with async_playwright() as playwright:\n        await run(playwright)\n\nasyncio.run(main())\n```\n\n```py\nimport os\nfrom playwright.sync_api import sync_playwright\n\nREPO = \`
  - `//example.com/api/uploadScript\`
  - `s metaZones.txt](https://cs.chromium.org/chromium/src/third_party/icu/source/data/misc/metaZones.txt?rcl=faee8bc70570192d82d2978a71e2a615788597d1)↵for a list of supported timezone IDs. Defaults to the system timezone.`
  - `});\n```\n\n```py\nfrom playwright.async_api import expect\n\n# ✓ Has the right items in the right order\nawait expect(page.locator(\`
  - `Form data to be serialized as html form using `application/x-www-form-urlencoded` encoding and sent as↵this request body.`
  - `, { dataTransfer });\n```\n\n```java\n// Note you can only create DataTransfer in Chromium and Firefox\nJSHandle dataTransfer = page.evaluateHandle(\`
  - `)).hasCount(3);\n```\n\n```py\nfrom playwright.async_api import expect\n\nlocator = page.locator(\`
  - `)\n    api_request_context = context.request\n    page = context.new_page()\n\n    # Alternatively you can create a APIRequestContext manually without having a browser context attached:\n    # api_request_context = p.request.new_context(base_url=\`
  - ` }\n});\n```\n\n> **Chromium-only** Playwright can also be used to control the Google Chrome or Microsoft Edge browsers, but it\nworks best with the version of Chromium it is bundled with. There is no guarantee it will work with any other\nversion. Use `executablePath` option with extreme caution.\n>\n> If Google Chrome (rather than Chromium) is preferred, a\n[Chrome Canary](https://www.google.com/chrome/browser/canary.html) or\n[Dev Channel](https://www.chromium.org/getting-involved/dev-channel) build is suggested.\n>\n> Stock browsers like Google Chrome and Microsoft Edge are suitable for tests that require proprietary media codecs\nfor video playback. See\n[this article](https://www.howtogeek.com/202825/what%E2%80%99s-the-difference-between-chromium-and-chrome/) for\nother differences between Chromium and Chrome.\n[This article](https://chromium.googlesource.com/chromium/src/+/lkgr/docs/chromium_browser_vs_google_chrome.md)\ndescribes some differences for Linux users.`
  - `//dog.ceo/api/breeds/list/all',`
  - `https://example.com/api/uploadScript`
  - `Firefox user preferences. Learn more about the Firefox user preferences at\n[`about:config`](https://support.mozilla.org/en-US/kb/about-config-editor-firefox).\n\nYou can also provide a path to a custom [`policies.json` file](https://mozilla.github.io/policy-templates/) via\n`PLAYWRIGHT_FIREFOX_POLICIES_JSON` environment variable.`
  - `Maximum time in milliseconds. Defaults to `0` - no timeout. The default value can be changed via `actionTimeout`\noption in the config, or by using the [`method: BrowserContext.setDefaultTimeout`] or\n[`method: Page.setDefaultTimeout`] methods.`
  - `The `PageAssertions` class provides assertion methods that can be used to make assertions about the `Page` state in\nthe tests.\n\n```js\nimport { test, expect } from `
  - `config`](https://support.mozilla.org/en-US/kb/about-config-editor-firefox).`
  - `JSHandle dataTransfer = page.evaluateHandle(\`
  - `An acceptable amount of pixels that could be different. Default is configurable with `TestConfig.expect`. Unset by\ndefault.`
  - `\n\n\nasync def main():\n    async with async_playwright() as playwright:\n        await run(playwright)\n\nasyncio.run(main())\n```\n\n```py\nfrom playwright.sync_api import sync_playwright\n\nwith sync_playwright() as p:\n    context = playwright.request.new_context()\n    response = context.get(\`
  - `data_transfer = await page.evaluate_handle(\`
  - `var dataTransfer = await page.EvaluateHandleAsync(\`
  - `An acceptable perceived color difference in the [YIQ color space](https://en.wikipedia.org/wiki/YIQ)↵between the same pixel in compared images, between zero (strict) and one (lax), default is configurable with↵`TestConfig.expect`. Defaults to `0.2`.`
  - `Waits for event to fire and passes its value into the predicate function. Returns when the predicate returns truthy\nvalue. Will throw an error if the webSocket is closed before the event is fired. Returns the event data value.`
  - `Provides an object that will be serialized as html form using `multipart/form-data` encoding and sent as this\nrequest body. If this parameter is specified `content-type` header will be set to `multipart/form-data` unless\nexplicitly provided. File values can be passed as file-like object containing file name, mime-type and its content.\n\nAn instance of `FormData` can be created via [`method: APIRequestContext.createFormData`].`
  - `    # api_request_context = p.request.new_context(base_url=\`
  - `])\n```\n\n```py\nfrom playwright.sync_api import expect\n\nlocator = page.locator(\`
  - `)).isDisabled();\n```\n\n```py\nfrom playwright.async_api import expect\n\nlocator = page.locator(\`
  - `'/api/v1'`

**.venv/lib/python3.12/site-packages/playwright/driver/package/package.json**:
  - `./lib/server/utils/image_tools/stats`
  - `./lib/server/utils/image_tools/colorUtils.js`
  - `./lib/server/utils/image_tools/compare.js`
  - `./lib/server/utils/image_tools/stats.js`
  - `./lib/server/utils/image_tools/imageChannel`
  - `./lib/server/utils/image_tools/imageChannel.js`
  - `./lib/server/utils/image_tools/colorUtils`
  - `./lib/server/utils/image_tools/compare`

**.venv/lib/python3.12/site-packages/setuptools/config/setuptools.schema.json**:
  - `https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html`
  - `<https://setuptools.pypa.io/en/latest/references/keywords.html>`_`
  - `<https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html#dynamic-metadata>`_.`
  - `//setuptools.pypa.io/en/latest/userguide/package_discovery.html`
  - `<https://setuptools.pypa.io/en/latest/userguide/package_discovery.html>`_.`
  - `//setuptools.pypa.io/en/latest/userguide/datafiles.html>`_.`
  - `//setuptools.pypa.io/en/latest/references/keywords.html>`_`
  - `//setuptools.pypa.io/en/latest/userguide/package_discovery.html>`_.`
  - `//setuptools.pypa.io/en/latest/userguide/pyproject_config.html#setuptools-specific-configuration>`_`
  - `https://setuptools.pypa.io/en/latest/userguide/package_discovery.html`
  - `//setuptools.pypa.io/en/latest/userguide/pyproject_config.html#dynamic-metadata>`_.`
  - `//setuptools.pypa.io/en/latest/userguide/pyproject_config.html`
  - `<https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html#setuptools-specific-configuration>`_`
  - `<https://setuptools.pypa.io/en/latest/userguide/datafiles.html>`_.`

**.venv/lib/python3.12/site-packages/setuptools/config/distutils.schema.json**:
  - `https://setuptools.pypa.io/en/latest/deprecated/distutils/configfile.html`
  - `//setuptools.pypa.io/en/latest/deprecated/distutils/configfile.html`
  - `<https://setuptools.pypa.io/en/latest/deprecated/distutils/configfile.html>`_.`
  - `//setuptools.pypa.io/en/latest/deprecated/distutils/configfile.html>`_.`

**modules/unicode_utils_v2/transparent_mining_20250711_081235.json**:
  - `Phoenix (/ˈfiːnɪks/ FEE-niks) is the capital and most populous city of the U.S. state of Arizona. With over 1.6 million residents at the 2020 census,`

**modules/unicode_utils_v2/real_frequency_mining_20250710_140406.json**:
  - `Phoenix (/ˈfiːnɪks/ FEE-niks) is the capital and most populous city of the U.S. state of Arizona. With over 1.6 million residents at the 2020 census,`

**modules/unicode_utils_v2/real_frequency_mining_20250710_141758.json**:
  - `Phoenix (/ˈfiːnɪks/ FEE-niks) is the capital and most populous city of the U.S. state of Arizona. With over 1.6 million residents at the 2020 census,`

**modules/unicode_utils_v2/real_frequency_mining_20250710_132318.json**:
  - `Phoenix (/ˈfiːnɪks/ FEE-niks) is the capital and most populous city of the U.S. state of Arizona. With over 1.6 million residents at the 2020 census,`

**modules/unicode_utils_v2/real_frequency_mining_20250710_134239.json**:
  - `Phoenix (/ˈfiːnɪks/ FEE-niks) is the capital and most populous city of the U.S. state of Arizona. With over 1.6 million residents at the 2020 census,`

**modules/unicode_utils_v2/real_frequency_mining_20250710_142152.json**:
  - `Phoenix (/ˈfiːnɪks/ FEE-niks) is the capital and most populous city of the U.S. state of Arizona. With over 1.6 million residents at the 2020 census,`

**modules/unicode_utils_v2/config/api_configuration.json**:
  - `//export.arxiv.org/api`
  - `//www.cnrtl.fr/api/`
  - `https://www.googleapis.com/books/v1`
  - `https://en.wikipedia.org/w/api.php`
  - `//newsapi.org/v2`
  - `//api.europeana.eu`
  - `https://api.github.com`
  - `http://export.arxiv.org/api`
  - `https://www.cnrtl.fr/api/`
  - `//www.goethe.de/api/corpus/`
  - `https://api.europeana.eu`
  - `//en.wikipedia.org/w/api.php`
  - `//www.googleapis.com/books/v1`
  - `//ruscorpora.ru/api/`
  - `//api.github.com`
  - `https://www.goethe.de/api/corpus/`
  - `https://ruscorpora.ru/api/`
  - `https://newsapi.org/v2`

**modules/unicode_utils_v2/.claude/settings.local.json**:
  - `Bash(# Remove corresponding test files for deleted modules\nrm tests/unit/test_advanced_unicode_features.py\necho \`
  - `Bash(# Move JSON results to data/results/\nmv *_results_*.json data/results/ 2>/dev/null || true\nmv *_ligatures.json data/results/ 2>/dev/null || true\nmv *.json data/results/ 2>/dev/null || true\n\n# Move database files to data/databases/\nmv *.db data/databases/ 2>/dev/null || true\nmv mining_session_*.db data/databases/ 2>/dev/null || true\nmv orchestrator_*.db data/databases/ 2>/dev/null || true\n\n# Move session files to data/sessions/\nmv session_report_*.json data/sessions/ 2>/dev/null || true\n\n# Move coverage reports to data/coverage/\nmv htmlcov/* data/coverage/ 2>/dev/null || true\nmv coverage.xml data/coverage/ 2>/dev/null || true\n\n# Move corpus cache to data/cache/\nmv corpus_cache/* data/cache/ 2>/dev/null || true)`
  - `Bash(# Remove test files that depend on deleted modules\nrm tests/unit/test_language_consolidated.py\necho \`
  - `# Contributing to Unicode Utils\n\n## Development Setup\n\n1. Clone the repository\n2. Install dependencies: \\`pip install -r requirements.txt\\`\n3. Run tests: \\`python -m pytest tests/\\`\n\n## Code Style\n\n- Follow PEP 8\n- Use type hints\n- Write comprehensive tests\n\n## Submitting Changes\n\n1. Create a feature branch\n2. Make your changes\n3. Run tests\n4. Submit a pull request\`
  - `)\n\nasyncio.run(test_real_apis())\n\`
  - ` -delete\nrm -rf checkpoints/\nrm -rf corpus_cache/\nrm -rf mining_sessions/\nrm -rf data/sessions/\nrm -rf data/databases/\nrm -rf data/cache/\necho \`
  - `Bash(# Clean up massive results directories\nrm -rf data/results/\nrm -rf scripts/results/\nrm -rf scripts/reports/\n# Remove redundant mining scripts\nrm -rf scripts/strategies/\necho \`
  - `Bash(# Delete duplicate API server (keep the one in api/ directory)\nrm -f api_server.py api_server_simple.py simple_auth_test.py 2>/dev/null || true\n\n# Delete redundant files\nrm -f unicode_constants.py 2>/dev/null || true  # Duplicate of unicode_utils/constants.py)`
  - `Bash(# Delete the massive archive of outdated files\nrm -rf archive/\n# Delete redundant deployment configs\nrm -rf deploy/\nrm -rf infrastructure/\n# Clean up coverage reports\nrm -rf htmlcov/\nrm -rf data/coverage/\nrm coverage.xml\necho \`
  - ` tests/unit/test_ligature_engine_enhanced.py\necho \`
  - `Bash(# Move all excessive documentation to archive\nmv COMPREHENSIVE_*.md archive/ 2>/dev/null || true\nmv DETAILED_*.md archive/ 2>/dev/null || true\nmv EXECUTIVE_*.md archive/ 2>/dev/null || true\nmv FINAL_*.md archive/ 2>/dev/null || true\nmv HARSH_*.md archive/ 2>/dev/null || true\nmv REALISTIC_*.md archive/ 2>/dev/null || true\nmv REFACTORING_*.md archive/ 2>/dev/null || true\nmv TEST_*.md archive/ 2>/dev/null || true\nmv UPGRADE_*.md archive/ 2>/dev/null || true\nmv PROJECT_REORGANIZATION_PLAN.md archive/ 2>/dev/null || true\nmv ligature_mining_report.md archive/ 2>/dev/null || true\n\n# Move session and checkpoint directories to data/\nmv mining_sessions/* data/sessions/ 2>/dev/null || true\nmv checkpoints/* data/sessions/ 2>/dev/null || true\nrmdir mining_sessions checkpoints 2>/dev/null || true)`
  - `Bash(# Remove the redundant hell_level tests (3.7MB as per audit)\nrm -rf tests/hell_level/ 2>/dev/null || true)`
  - `)\n    try:\n        news_api = NewsAPIIntegration()\n        result = await news_api.get_top_headlines(page_size=3)\n        await news_api.close()\n        print(f`
  - `t core functionality\nrm unicode_utils/corpus_integration.py\nrm unicode_utils/corpus_sources.py\nrm unicode_utils/error_handling.py\nrm unicode_utils/language_detection.py\nrm unicode_utils/advanced_unicode_features.py\necho \`

**modules/unicode_utils_v2/htmlcov/status.json**:
  - `unicode_utils/extended_unicode_data.py`
  - `unicode_utils/core.py`
  - `unicode_utils/config.py`
  - `unicode_utils/real_ligature_data.py`
  - `unicode_utils/api_client.py`
  - `unicode_utils/language_data.py`
  - `unicode_utils/logging_config.py`

**modules/unicode_utils_v2/scripts/strategies/enhanced_api_config.json**:
  - `https://www.jstor.org/api/`
  - `//www.goethe.de/api/corpus/`
  - `//corpus.rae.es/crea/api/`
  - `https://corpora.unibo.it/coris/api/`
  - `//gallica.bnf.fr/api/`
  - `//www.frantext.fr/api/`
  - `//www.dwds.de/api/`
  - `https://www.cnrtl.fr/api/`
  - `https://www.frantext.fr/api/`
  - `//www.perseus.tufts.edu/api/`
  - `https://ruscorpora.ru/api/`
  - `https://www.googleapis.com/books/v1/`
  - `https://www.clul.ulisboa.pt/cordial/api/`
  - `https://archive.org/api/`
  - `//babel.hathitrust.org/api/`
  - `https://gallica.bnf.fr/api/`
  - `https://corpus.rae.es/corde/api/`
  - `//ruscorpora.ru/api/`
  - `https://corpus.rae.es/crea/api/`
  - `//www.jstor.org/api/`
  - `https://www.dwds.de/api/`
  - `//www.googleapis.com/books/v1/`
  - `//www.cnrtl.fr/api/`
  - `//www.ids-mannheim.de/dereko/api/`
  - `//corpora.unibo.it/coris/api/`
  - `//www.clul.ulisboa.pt/cordial/api/`
  - `https://babel.hathitrust.org/api/`
  - `//corpus.rae.es/corde/api/`
  - `https://www.ids-mannheim.de/dereko/api/`
  - `https://www.perseus.tufts.edu/api/`
  - `https://www.goethe.de/api/corpus/`
  - `//archive.org/api/`

**modules/unicode_utils_v2/scripts/strategies/mining_languages.json**:
  - `https://www.larousse.fr/api/`
  - `//dicionario.priberam.org/api/`
  - `https://www.bncf.firenze.sbn.it/api/`
  - `//www.bncf.firenze.sbn.it/api/`
  - `//www.goethe.de/api/`
  - `https://www.vandale.nl/api/`
  - `//www.deutschestextarchiv.de/api/`
  - `https://www.academia.org.br/api/`
  - `https://www.goethe.de/api/`
  - `https://datos.bne.es/api/`
  - `//cvc.cervantes.es/api/`
  - `//www.treccani.it/api/`
  - `//www.vandale.nl/api/`
  - `//www.kb.nl/api/`
  - `//gallica.bnf.fr/api/`
  - `//www.dwds.de/api/`
  - `https://www.vaticanlibrary.va/api/`
  - `//www.vaticanlibrary.va/api/`
  - `https://dicionario.priberam.org/api/`
  - `https://dle.rae.es/data/`
  - `https://gallica.bnf.fr/api/`
  - `https://www.treccani.it/api/`
  - `https://www.dwds.de/api/`
  - `https://www.kb.nl/api/`
  - `//www.academia.org.br/api/`
  - `https://www.deutschestextarchiv.de/api/`
  - `//dle.rae.es/data/`
  - `https://cvc.cervantes.es/api/`
  - `https://data.bnf.fr/api/`
  - `//www.larousse.fr/api/`
  - `//datos.bne.es/api/`
  - `//data.bnf.fr/api/`

**pyproject.toml**:
  - `tests/*`
  - `*/tests/*`

**modules/unicode_utils_v2/pyproject.toml**:
  - `
[tox]
envlist = py38,py39,py310,py311,py312,lint,type,docs
isolated_build = true
skip_missing_interpreters = true

[testenv]
deps =
    pytest>=7.0
    pytest-cov>=4.0
    hypothesis>=6.0
commands =
    pytest {posargs}

[testenv:lint]
deps =
    black>=23.0
    isort>=5.0
    flake8>=6.0
commands =
    black --check unicode_utils tests
    isort --check unicode_utils tests
    flake8 unicode_utils tests

[testenv:type]
deps =
    mypy>=1.0
commands =
    mypy unicode_utils

[testenv:docs]
deps =
    sphinx>=6.0
    sphinx-rtd-theme>=1.0
    sphinx-autodoc-typehints>=1.0
    myst-parser>=1.0
changedir = docs
commands =
    sphinx-build -W -b html . _build/html
`
  - `*/tests/*`

**modules/unicode_utils_v2/config/tox.ini**:
  - `*/tests/*`


### 📊 IMPORT FREQUENCY ANALYSIS
Most frequently imported modules that will be affected:



## REMEDIATION PLAN

### 1. **Import Path Updates Required**
All Python files importing from moved modules will need import statements updated:

```python
# BEFORE (broken after reorganization)
from core.models import Document
from utils.text import normalize
from config import settings

# AFTER (fixed for new structure)  
from src.core.models import Document
from src.utils.text import normalize
from config.environments import settings
```

### 2. **Configuration File Updates**
Update hardcoded paths in configuration files:
- Docker files: Update COPY and WORKDIR paths
- CI/CD pipelines: Update test and build paths  
- Configuration files: Update data and log file paths

### 3. **Test Path Updates**
All test files will need updated import paths and test data paths.

### 4. **Documentation Updates**
Update any documentation referencing file paths or module imports.

## AUTOMATED FIXES

### Import Statement Replacements
```bash
# Core module imports
find src/ -name "*.py" -exec sed -i 's/from core\./from src.core./g' {} \;
find src/ -name "*.py" -exec sed -i 's/import core\./import src.core./g' {} \;

# Utils imports  
find src/ -name "*.py" -exec sed -i 's/from utils\./from src.utils./g' {} \;
find src/ -name "*.py" -exec sed -i 's/import utils\./import src.utils./g' {} \;

# API imports
find src/ -name "*.py" -exec sed -i 's/from api\./from src.api./g' {} \;
find src/ -name "*.py" -exec sed -i 's/import api\./import src.api./g' {} \;
```

## TESTING STRATEGY

1. **Pre-reorganization**: Run full test suite to establish baseline
2. **Post-reorganization**: Fix imports systematically
3. **Incremental testing**: Test each module as imports are fixed
4. **Full regression**: Run complete test suite after all fixes

## RISK MITIGATION

- **Full backup**: Complete project backup before starting
- **Incremental approach**: Fix one module at a time
- **Automated testing**: Run tests after each fix
- **Rollback plan**: Keep backup accessible for quick rollback

## ESTIMATED EFFORT

- **Import fixes**: 592 files × 5 minutes = 2960 minutes
- **Config updates**: 86 files × 10 minutes = 860 minutes  
- **Testing**: 2 hours comprehensive testing
- **Total**: ~65 hours

## RECOMMENDATION

✅ **PROCEED WITH REORGANIZATION**

The benefits of a clean, professional structure far outweigh the temporary import fix effort. 
Most issues are automatically fixable with find/replace operations.


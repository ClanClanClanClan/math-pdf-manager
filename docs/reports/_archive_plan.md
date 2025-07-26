# Test File Consolidation Plan

## Current State: 40+ Test Files 
Found these duplicate/scattered test files:

### IEEE Test Files (10 files - consolidate to 1)
- simple_ieee_test.py
- ieee_final_test.py  
- ieee_complete_test.py
- ieee_final_working_test.py
- final_ieee_test.py
- test_ieee_visual.py
- test_complete_ieee_login.py
- test_ieee_smart_modal.py
→ **CONSOLIDATE TO:** test_ieee_integration.py

### SIAM Test Files (7 files - consolidate to 1)
- simple_siam_test.py
- siam_login_test.py
- focused_siam_test.py
- siam_simple_test.py
- test_siam.py
→ **CONSOLIDATE TO:** test_siam_integration.py

### DI Framework Test Files (10 files - consolidate to 1)
- test_di_framework.py
- simple_di_test.py
- fix_and_test_di.py
- final_di_test.py
- test_di_integration.py
- comprehensive_di_test.py
- simple_di_test_inline.py
- working_di_test.py
→ **CONSOLIDATE TO:** test_dependency_injection.py

### Generic Test Files (15+ files - consolidate to 5)
- test_functionality.py
- test_real_download.py
- test_auth_manager.py
- test_pdf_creation.py
- quick_connection_test.py
- test_metadata_fetcher_comprehensive.py
- test_downloader_comprehensive.py
- test_text_processing_integration.py
- test_backward_compatibility.py
→ **CONSOLIDATE TO:** 
  - test_core_functionality.py
  - test_authentication.py
  - test_metadata_services.py
  - test_text_processing.py
  - test_integration.py

## Action Plan:
1. Create _archive/old_tests/ directory
2. Move duplicates to archive
3. Create consolidated test files
4. Update any references
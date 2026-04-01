# 🗺️ Complete Functionality Mapping

## Critical Working Implementations

### ✅ **100% Working Production Code**

#### **VPN Connection**
- `bulletproof_vpn_connect.py` - **BEST**: Visual recognition, multiple click methods
- `secure_vpn_credentials.py` - **REQUIRED**: Secure password storage in macOS Keychain
- `complete_auto_vpn_pdf.py` - Integrated VPN + PDF system

#### **Publisher Implementations**
- `src/publishers/ieee_publisher.py` - **100% working** IEEE with institutional login
- `src/publishers/siam_publisher.py` - **100% working** SIAM with SSO
- `src/publishers/arxiv_client.py` - **100% working** ArXiv direct API

#### **Core Infrastructure**
- `src/core/dependency_injection/` - Entire DI framework **CRITICAL**
- `src/validators/optimized_filename_validator.py` - Security-critical validation
- `src/downloader/browser_publisher_downloaders.py` - Core browser automation

### 🔧 **Partially Working / Experimental**

#### **Wiley Implementations** (Multiple approaches)
1. `working_wiley_downloader.py` - Browser-based, works sometimes
2. `eth_api_wiley_downloader.py` - API approach with ETH key
3. `final_working_wiley.py` - Latest attempt
4. `wiley_subscription_with_vpn.py` - VPN-based approach

#### **VPN Connection Attempts**
- `cisco_connect_fixed.py` - Attempted fix for Connect button
- `vpn_keyboard_connect.py` - Keyboard navigation approach
- `ultrathink_auto_connect.py` - Multiple detection methods
- `ultimate_auto_vpn.py` - Aggressive clicking everywhere

### 📊 **Test Scripts by Category**

#### **Publisher Tests** (Move to tests/integration/publishers/)
- `test_ieee_*.py` - IEEE testing scripts
- `test_siam_*.py` - SIAM testing scripts
- `test_wiley_*.py` - Wiley testing scripts
- `test_springer_*.py` - Springer tests

#### **VPN Tests** (Move to tests/integration/vpn/)
- `test_vpn_*.py` - VPN connection tests
- `vpn_*.py` - Various VPN experiments

#### **API Tests** (Move to tests/integration/api/)
- `test_eth_api_*.py` - ETH API tests
- `test_api_*.py` - General API tests

### 🛠️ **Utility Scripts**

#### **DOI and Metadata**
- `find_real_dois.py` - Find real DOIs for testing
- `check_ultimate_progress.py` - Progress checking utility
- `debug_downloads.py` - Debug download issues

#### **Analysis Tools**
- `detailed_failure_analysis.py` - Analyze download failures
- `comprehensive_publisher_test.py` - Test all publishers

### 📁 **Data Files to Preserve**

#### **Configuration**
- `config/config.yaml` - Main configuration
- `config/credentials.enc` - Encrypted credentials
- `journal_stats.json` - Journal success statistics

#### **Validation Data**
- `data/known_authors_1.txt` - 600+ mathematician names
- `data/languages/*.yaml` - Language-specific rules
- `data/multiword_familynames.txt` - Name validation data

### 🚨 **Critical Dependencies**

#### **Import Relationships**
```python
# These imports must be updated when moving files:
from secure_vpn_credentials import get_vpn_password
from bulletproof_vpn_connect import BulletproofVPNConnect
from src.publishers import ieee_publisher, siam_publisher
from src.core.dependency_injection import get_container
```

#### **File Dependencies**
- VPN scripts depend on `secure_vpn_credentials.py`
- Publisher scripts depend on `src/downloader/`
- Tests depend on fixtures in `data/`

### 🎯 **Functionality Priority**

1. **MUST PRESERVE** (Production Critical):
   - IEEE downloader (100% working)
   - SIAM downloader (100% working)
   - VPN credential storage
   - Core DI framework
   - Validation system

2. **SHOULD PRESERVE** (Useful but not critical):
   - Wiley download attempts
   - VPN connection experiments
   - DOI finding utilities
   - Debug tools

3. **CAN ARCHIVE** (Historical/Redundant):
   - Old test attempts
   - Duplicate implementations
   - Debug screenshots
   - Temporary files

### 📝 **Script Classification**

#### **Production Ready** ✅
```
bulletproof_vpn_connect.py          - Production VPN
secure_vpn_credentials.py           - Production credentials
src/publishers/ieee_publisher.py    - Production IEEE
src/publishers/siam_publisher.py    - Production SIAM
src/core/*                         - All core modules
src/validators/*                   - All validators
```

#### **Experimental** 🧪
```
ultrathink_*.py                    - Experimental approaches
test_*.py                          - Test scripts
*_debug.py                         - Debug utilities
cisco_*.py                         - VPN experiments
```

#### **Utilities** 🔧
```
find_real_dois.py                  - Useful utility
check_ultimate_progress.py         - Progress checker
debug_downloads.py                 - Debug helper
```

### 🔄 **Migration Checklist**

- [ ] Backup everything first
- [ ] Move production scripts to `scripts/`
- [ ] Move experimental to `experiments/`
- [ ] Update all imports
- [ ] Test IEEE downloader still works
- [ ] Test SIAM downloader still works
- [ ] Test VPN credential storage
- [ ] Verify 813+ tests still pass
- [ ] Document any breaking changes

### ⚠️ **Known Issues to Address**

1. **Import paths** will need updating after moving files
2. **Hardcoded paths** in some scripts need to be relative
3. **Test fixtures** may need path adjustments
4. **Config file** references need updating

### 🎉 **Expected Outcome**

After reorganization:
- Clear separation of production vs experimental
- Easy to find working implementations
- Well-documented code structure
- All functionality preserved
- Better maintainability
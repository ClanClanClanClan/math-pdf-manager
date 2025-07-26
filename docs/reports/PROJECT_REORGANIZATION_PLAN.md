# Math-PDF Manager Project Reorganization Plan

## Current Issues

### Size Issues
- **Total Size**: 8.9GB (excessive for Python project)
- **tools/grobid**: 4.5GB (full Java application) 
- **modules/pdf-meta-llm**: 2.4GB (AI models)
- **tools/LanguageTool**: 390MB (Java application)

### Structural Issues
- `modules/unicode_utils 2` - Space in name breaks imports
- Multiple archive directories: `_archive/`, `archive/`, `_deprecated/`
- Tests scattered across multiple locations
- Mixed Python/Java code
- Unclear module boundaries

## Reorganization Strategy

### Phase 1: External Dependencies (URGENT - Saves 5GB+)
1. **Move tools/grobid to external service**
   ```bash
   # Create docker-compose service instead
   mv tools/grobid /tmp/grobid_external
   # Create tools/grobid_service.py wrapper
   ```

2. **Extract large AI models**
   ```bash
   # Move to separate model repository
   mv modules/pdf-meta-llm/models /tmp/ai_models
   # Create model download script
   ```

3. **External LanguageTool**
   ```bash
   # Use pip package or external service
   mv tools/LanguageTool /tmp/languagetool_external
   ```

### Phase 2: Module Restructuring
```
math_pdf_manager/
├── src/                          # Main source code
│   ├── core/                     # Core functionality
│   │   ├── models/              # Data models
│   │   ├── services/            # Business logic
│   │   ├── exceptions/          # Custom exceptions
│   │   └── config/             # Configuration
│   ├── pdf_processing/         # PDF-specific logic
│   ├── metadata/               # Metadata extraction
│   ├── auth/                   # Authentication
│   ├── validation/             # Validation logic
│   └── cli/                    # Command line interface
├── tests/                      # All tests centralized
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── docs/                       # Documentation only
├── scripts/                    # Utility scripts
├── config/                     # Configuration files
├── tools/                      # Small utilities only
└── examples/                   # Usage examples
```

### Phase 3: Clean Archive Strategy
1. **Consolidate archives**
   ```bash
   mkdir -p archive/deprecated
   mv _archive/* archive/deprecated/
   mv archive/* archive/deprecated/ 
   ```

2. **Remove true duplicates**
   - Run duplicate detection
   - Keep only latest versions
   - Archive old implementations

### Phase 4: Test Consolidation
```
tests/
├── unit/
│   ├── core/
│   ├── pdf_processing/
│   ├── metadata/
│   └── auth/
├── integration/
├── performance/
└── security/
```

## Implementation Commands

### Step 1: Backup Critical Data
```bash
cp -r tools/grobid/grobid-home/config /tmp/grobid_config_backup
cp -r modules/pdf-meta-llm/config /tmp/ai_config_backup
```

### Step 2: Create External Service Configs
```bash
# Create docker-compose.yml for external services
cat > docker-compose.external.yml << EOF
version: '3.8'
services:
  grobid:
    image: lfoppiano/grobid:0.8.0
    ports:
      - "8070:8070"
  
  languagetool:
    image: erikvl87/languagetool
    ports:
      - "8081:8010"
EOF
```

### Step 3: Safe Module Moves
```bash
# Fix unicode_utils name
mv "modules/unicode_utils 2" modules/unicode_utils_v2

# Create new structure
mkdir -p src/{core,pdf_processing,metadata,auth,validation,cli}
mkdir -p tests/{unit,integration,e2e,performance,security}
```

### Step 4: Test Before Major Changes
```bash
# Run all tests to ensure nothing breaks
python -m pytest tests/ -v
```

## Expected Results

### Size Reduction
- **Before**: 8.9GB
- **After**: ~500MB-1GB (professional Python project size)
- **External services**: 5GB+ moved to containers

### Structure Benefits
- Clear module boundaries
- Professional layout
- Easy testing
- Better imports
- Reduced complexity

## Risk Mitigation

1. **Full backup before starting**
2. **Incremental moves with testing**
3. **Keep configuration files**
4. **Document external service setup**
5. **Maintain functionality through wrapper classes**

## Success Criteria

- [ ] Project size < 1GB
- [ ] All tests passing
- [ ] Clear module structure
- [ ] No broken imports
- [ ] External services documented
- [ ] Professional appearance
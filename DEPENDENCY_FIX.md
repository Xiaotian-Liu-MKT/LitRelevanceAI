# Fixing the httpx/OpenAI SDK Compatibility Issue

## Problem

If you encounter this error when running the application:

```
TypeError: Client.__init__() got an unexpected keyword argument 'proxies'
```

This is caused by a version incompatibility between the OpenAI SDK and the httpx library.

## Root Cause

- **httpx 0.28.0+** changed their API, removing the `proxies` parameter in favor of `proxy` (singular)
- **OpenAI SDK < 1.14.0** was using the old `proxies` parameter
- When these incompatible versions are installed together, the error occurs

## Solution

### Quick Fix (Recommended)

Reinstall the package with the correct dependency versions:

```bash
# Navigate to the project directory
cd /path/to/LitRelevanceAI

# Uninstall old versions (if any)
pip uninstall -y openai httpx

# Reinstall with the updated dependencies
pip install -e .
```

This will install:
- `openai >= 1.14.0` (compatible with modern httpx)
- `httpx >= 0.27, < 0.28` (keeps the `proxies` keyword supported)

### Manual Fix (Alternative)

If you prefer to manually control versions:

```bash
pip install "openai>=1.14.0" "httpx>=0.27,<0.28"
```

### Verification

After reinstalling, verify the versions:

```bash
python -c "import openai; import httpx; print(f'OpenAI: {openai.__version__}, httpx: {httpx.__version__}')"
```

You should see:
- OpenAI version 1.14.0 or higher
- httpx version 0.27.x (anything below 0.28)

### Testing the Fix

Try running the GUI again:

```bash
python run_gui.py
```

The AI assistant dialogs should now work without the `proxies` error.

## Technical Details

The issue occurs in `litrx/ai_client.py` when initializing the OpenAI client. The OpenAI SDK internally creates an httpx client, and the version mismatch causes the initialization to fail.

Our fix ensures that:
1. The OpenAI SDK is at least version 1.14.0 (which supports the new httpx API)
2. httpx stays on the 0.27.x line (providing the still-supported `proxies` keyword)

## Related Files Modified

- `pyproject.toml`: Updated dependency version constraints
  - Added `openai>=1.14.0` constraint
  - Added `httpx>=0.27,<0.28` constraint

## If the Problem Persists

1. **Clear pip cache**: `pip cache purge`
2. **Create a fresh virtual environment**:
   ```bash
   python -m venv venv_new
   source venv_new/bin/activate  # On Windows: venv_new\Scripts\activate
   pip install -e .
   ```
3. **Check for conflicting packages**: `pip list | grep -E "(openai|httpx)"`
4. **Report the issue**: Open a GitHub issue with your Python version, OS, and full error traceback

## Prevention

When updating dependencies in the future:
- Always check the CHANGELOG for breaking changes
- Test after updating `openai` or `httpx` packages
- Use version constraints in `pyproject.toml` to prevent incompatibilities

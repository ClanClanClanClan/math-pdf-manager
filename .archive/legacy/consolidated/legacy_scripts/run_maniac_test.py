#!/usr/bin/env python3
"""Execute MANIAC test directly"""

import sys
import os

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

print("🔥🔥🔥 EXECUTING MANIAC TEST 🔥🔥🔥")
print("=" * 80)

# Import and execute MANIAC test
try:
    import MANIAC_TEST_EXECUTION
    
    # Run the main function
    if hasattr(MANIAC_TEST_EXECUTION, 'main'):
        print("Running MANIAC_TEST_EXECUTION.main()...")
        success = MANIAC_TEST_EXECUTION.main()
        
        if success:
            print("\n🎉 MANIAC TEST EXECUTION: SUCCESS!")
        else:
            print("\n❌ MANIAC TEST EXECUTION: FAILED!")
            
    else:
        print("❌ No main function found in MANIAC_TEST_EXECUTION")
        
except Exception as e:
    print(f"❌ Error executing MANIAC test: {e}")
    import traceback
    traceback.print_exc()

print("\n🔥 MANIAC TEST EXECUTION COMPLETE 🔥")
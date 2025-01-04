Follow the Pre-test analysis first then write the tests
# Pre-Test Analysis
1. Identify the exact function/code to be tested
   - Copy the target code and read it line by line
   - Note all parameters, return types, and dependencies
   - Mark any async/await patterns
   - List all possible code paths
2. Analyze Infrastructure Requirements
   - Check if async testing is needed
   - Identify required mocks/fixtures
   - Note any special imports or setup needed
   - Check for immutable objects that need special handling
3. Create Test Foundation
   - Write basic fixture setup
   - Test the fixture with a simple case
   - Verify imports work
   - Run once to ensure test infrastructure works
4. Plan Test Cases
   - List happy path scenarios
   - List error cases from function's try/except blocks
   - Map each test to specific lines of code
   - Verify each case tests something unique
5. Write and Verify Incrementally
   - Write one test case
   - Run coverage to verify it hits expected lines
   - Fix any setup issues before continuing
   - Only proceed when each test works
6. Cross-Check Coverage
   - Run coverage report
   - Map uncovered lines to missing test cases
   - Verify edge cases are covered
   - Confirm error handling is tested
7. Final Verification
   - Run full test suite
   - Compare before/after coverage
   - Verify each test targets the intended function
   - Check for test isolation/independence
# Red Flags to Watch For
- Tests that don't increase coverage
- Overly complex test setups
- Tests targeting multiple functions
- Untested fixture setups
- Missing error cases
- Incomplete mock configurations
# Questions to Ask
- Am I actually testing the target function?
- Does each test serve a clear purpose?
- Are the mocks properly configured?
- Have I verified the test infrastructure works?
- Does the coverage report show improvement?
-------
Write pytest code for this function name it the name of the function and create a git commit:

FUNCTION:

FULL CODE:

===
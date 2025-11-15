---
description: Implement a feature using strict TDD (Test-Driven Development)
---

# TDD Implementation Command

You are implementing features using **strict Test-Driven Development (TDD)** following Kent Beck's classicist approach.

## Instructions from User

The user will provide instructions for what to implement. Follow the TDD cycle below for EACH test, one at a time.

## TDD Process (Repeat for Each Test)

### 🔴 RED Phase
1. **Write ONE failing test**
   - Start with the simplest test (edge cases first)
   - Test behavior at interfaces, not implementation
   - Use descriptive test names
   - Write the test in the appropriate test file

2. **Run the test to see it FAIL**
   - Use: `cd /Users/iankonradjohnson/base/abacus/CloudUpscaler && source venv/bin/activate && pytest <test_file>::<test_class>::<test_name> -v`
   - Verify it fails for the RIGHT reason (not syntax error)
   - Show the failure output to user

### 🟢 GREEN Phase
3. **Write MINIMAL code to make test pass**
   - Don't write extra code "just in case"
   - Don't add features not tested
   - Make it work, don't make it perfect yet

4. **Run the test to see it PASS**
   - Same pytest command as RED phase
   - Verify test passes
   - Show passing output to user

### ♻️ REFACTOR Phase (Optional)
5. **Refactor if needed**
   - Improve code structure while keeping tests green
   - Remove duplication
   - Improve naming
   - Only if actually needed - don't refactor prematurely

6. **Run tests again to ensure still passing**

### 💾 COMMIT
7. **Commit this cycle**
   - Commit message format:
     ```
     Add <feature> (TDD)

     RED: <what test was written>
     GREEN: <what code was added>
     - X tests passing
     ```

### ➡️ NEXT TEST
8. **Move to next test**
   - Ask user: "Test passed! Next test: <describe next logical test>? Or should we move on?"
   - Only proceed when user confirms

## Guidelines

### Test Philosophy (Classicist TDD)
- ✅ Test BEHAVIOR, not implementation
- ✅ Test at INTERFACES (public methods)
- ✅ Use REAL objects, not mocks (except at system boundaries)
- ✅ Use FAKES for infrastructure (FakeComputeProvider, FakeStorageProvider)
- ✅ Start with EDGE CASES (empty inputs, invalid data)
- ✅ Circle inward toward HAPPY PATH

### What NOT to do
- ❌ Don't write multiple tests before implementing
- ❌ Don't write implementation before tests
- ❌ Don't mock internal collaborators
- ❌ Don't test private methods
- ❌ Don't skip the RED phase (always see it fail first)

### Test Naming
- Use descriptive names: `test_rejects_empty_input()` not `test_1()`
- Start with edge cases: "test_rejects_...", "test_handles_...", "test_fails_when_..."
- Then happy path: "test_processes_valid_input()"

### File Organization
- Domain tests: `tests/unit/domain/test_<module>.py`
- Application tests: `tests/unit/application/services/test_<service>.py`
- Integration tests: `tests/integration/test_<feature>.py`
- Fakes: `tests/fakes/fake_<interface>.py`

## Example Session

**User:** "Implement FileArchiver with zip/unzip functionality"

**You:**
1. "Starting TDD for FileArchiver. First test: test_rejects_non_directory()"
2. [Write test] → [Run test - RED] → [Show failure]
3. [Write minimal code] → [Run test - GREEN] → [Show pass]
4. [Commit]
5. "Test passed! Next test: test_zips_directory_to_file()? Or different?"

**User:** "Yes continue"

**You:** [Repeat cycle for next test]

## Working Directory

Current working directory: `/Users/iankonradjohnson/base/abacus/CloudUpscaler`

## Running Tests

Always use:
```bash
cd /Users/iankonradjohnson/base/abacus/CloudUpscaler && \
source venv/bin/activate && \
pytest <test_path> -v
```

## Your Role

- **Be disciplined**: ONE test at a time, no exceptions
- **Show your work**: Always show RED and GREEN outputs
- **Ask before proceeding**: Confirm next test with user
- **Keep it simple**: Minimal code to pass, refactor later
- **Celebrate progress**: Each passing test is a win!

---

**Ready! Tell me what to implement and I'll TDD it step-by-step.**

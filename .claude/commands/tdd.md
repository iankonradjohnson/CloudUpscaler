---
description: Implement a feature using strict TDD (Test-Driven Development)
---

# TDD Implementation Command

You are implementing features using **strict Test-Driven Development (TDD)** following Kent Beck's classicist approach.

## Instructions from User

The user will provide instructions for what to implement.

### BEFORE Starting TDD

1. **Analyze the Architecture**
   - Read any architecture documents provided
   - Understand the complete system design
   - Identify all components and their dependencies

2. **Create Test Plan**
   - Identify dependency order (which classes depend on which)
   - Start with lowest-level dependencies FIRST
   - Work up the dependency tree
   - Example: If `Pipeline` depends on `FileArchiver`, build `FileArchiver` first

3. **Identify Test Boundaries**
   - Use REAL objects for all internal code
   - Use FAKES only at external system boundaries (APIs, databases, file systems)
   - Example: `Pipeline(FileArchiver(), StorageManager(FakeStorageProvider()), JobManager(FakeComputeProvider()))`
   - NOT: `Pipeline(MockFileArchiver(), MockStorageManager()...)` ❌

### Dependency-First Approach

**Build in this order:**
1. **Domain objects** (value objects, exceptions) - no dependencies
2. **Fakes** for external systems (FakeDatabase, FakeAPI) - system boundary
3. **Leaf services** (no complex dependencies)
4. **Mid-level services** (depend on leaf services)
5. **Orchestrators** (depend on everything)

**Example for CloudUpscaler:**
```
Level 1: JobStatus, UpscaleConfig (no dependencies)
Level 2: FakeComputeProvider, FakeStorageProvider (external boundaries)
Level 3: FileArchiver (no external dependencies)
Level 4: StorageManager(FakeStorageProvider), JobManager(FakeComputeProvider)
Level 5: UpscalePipeline(FileArchiver, StorageManager, JobManager, ...)
```

### Test Composition (Classicist Approach)

✅ **GOOD** - Real objects, fakes only at boundaries:
```python
def test_pipeline_works():
    # Real objects all the way down
    fake_storage = FakeStorageProvider()
    fake_compute = FakeComputeProvider()

    # Compose with real services
    archiver = FileArchiver()
    storage_mgr = StorageManager(fake_storage)  # Real service, fake provider
    job_mgr = JobManager(fake_compute)          # Real service, fake provider

    # Real orchestrator
    pipeline = UpscalePipeline(archiver, storage_mgr, job_mgr)

    # Test behavior
    result = pipeline.run_sync(input_dir, output_dir)
    assert result.is_successful()
```

❌ **BAD** - Mocking internal collaborators:
```python
def test_pipeline_works():
    mock_archiver = Mock()
    mock_storage = Mock()
    pipeline = UpscalePipeline(mock_archiver, mock_storage)
    # This locks in implementation details!
```

## TDD Workflow

### Step 0: Create Test Plan (Do This FIRST!)

Before writing ANY tests or code:

1. **Analyze the system**
   - Read architecture documents
   - Identify all components
   - Map dependencies between components

2. **Create TEST_PLAN.md**
   - List all components in dependency order
   - Identify what needs testing (behavior) vs what doesn't (data)
   - Determine where to use fakes (external boundaries only)
   - Plan test sequence: dependencies first, then dependents

3. **Get user approval**
   - Show the test plan to the user
   - Confirm the approach before coding

**Only after test plan is approved, proceed to Step 1.**

---

### Step 1-N: TDD Cycle (Repeat for Each Test)

Follow this cycle for EACH test, one at a time, in the order defined by your test plan.

---

## TDD Process (Repeat for Each Test)

---

## ⚠️ HARD RULE - READ THIS FIRST ⚠️

**BUSINESS LOGIC CODE (src/) CAN ONLY BE WRITTEN AFTER A TEST FORCES YOU TO WRITE IT!**

- ❌ Do NOT create classes "because the architecture doc mentions them"
- ❌ Do NOT create exceptions "because we'll need them later"
- ❌ Do NOT create interfaces "to match the design"
- ❌ Do NOT write ANY src/ code before writing a test that needs it

**The test comes FIRST. Always. No exceptions.**

If you find yourself writing src/ code without a failing test demanding it, **STOP IMMEDIATELY**.

---

### 🔴 RED Phase
1. **Write ONE failing test**
   - Start with the simplest test (edge cases first)
   - Test behavior at interfaces, not implementation
   - Use descriptive test names
   - Write the test in the appropriate test file
   - ⚠️ **ONE ASSERT PER TEST** (in general)
     - Each test should verify ONE behavior
     - Makes failures crystal clear
     - Example: `test_completed_is_terminal()` not `test_knows_all_terminal_states()`

2. **Run the test to see it FAIL**
   - Use: `cd /Users/iankonradjohnson/base/abacus/CloudUpscaler && source venv/bin/activate && pytest <test_file>::<test_class>::<test_name> -v`
   - Verify it fails for the RIGHT reason (not syntax error)
   - Show the failure output to user
   - **This failing test is your permission slip to write code**

### 🟢 GREEN Phase
3. **Write MINIMAL code to make test pass**
   - ⚠️ CRITICAL: Write ONLY the code needed for THIS ONE TEST
   - ❌ Do NOT add fields/methods/validation that aren't tested yet
   - ❌ Do NOT implement features "because we'll need them later"
   - ❌ Do NOT add code from the architecture doc that isn't tested yet
   - ✅ If test checks empty string validation → ONLY add that validation
   - ✅ If test checks one field → ONLY add that one field
   - ✅ Next test will drive the next piece of code
   - 💡 Example: Test checks `model_name` validation → Don't add `timeout_seconds` yet!

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
8. **Automatically move to next test**
   - Identify the next logical test based on the architecture/feature requirements
   - Continue the RED-GREEN-REFACTOR cycle
   - Keep going until the entire feature is complete

## Guidelines

### Test Philosophy (Classicist TDD - Kent Beck)
- ✅ Test BEHAVIOR, not implementation
- ✅ Test at INTERFACES (public methods)
- ✅ Use REAL objects, not mocks (except at system boundaries)
- ✅ Use FAKES for infrastructure (FakeComputeProvider, FakeStorageProvider)
- ✅ Start with EDGE CASES (empty inputs, invalid data)
- ✅ Circle inward toward HAPPY PATH

### What TO Test
- ✅ Business logic and validation rules
- ✅ Behavior at public interfaces
- ✅ Edge cases and error conditions
- ✅ Workflows and orchestration

### What NOT to Test (Kent Beck)
- ❌ Simple getters/setters
- ❌ Plain data structures (dataclasses with no logic)
- ❌ Field assignments (will be tested by code that uses them)
- ❌ Serialization methods if trivial (covered by integration tests)
- 💡 **Rule:** If it's just data access with no logic, skip it. Let integration tests cover it.

### What NOT to do
- ❌ Don't write multiple tests before implementing
- ❌ Don't write implementation before tests
- ❌ Don't add "extra" code that isn't tested (even if architecture doc shows it)
- ❌ Don't implement entire classes when test only checks one behavior
- ❌ Don't add methods/fields/validation not required by current test
- ❌ Don't mock internal collaborators
- ❌ Don't test private methods
- ❌ Don't skip the RED phase (always see it fail first)

### MINIMAL Code Examples

**BAD** (test only checks empty validation, but added everything):
```python
# Test: only checks model_name empty validation
@dataclass(frozen=True)
class UpscaleConfig:
    model_name: str = "net_g_1000000"
    target_dpi: Optional[int] = None  # ❌ NOT TESTED YET!
    tile_size: int = 0                # ❌ NOT TESTED YET!
    timeout_seconds: int = 3600       # ❌ NOT TESTED YET!

    def __post_init__(self):
        if not self.model_name:
            raise ValueError("model_name cannot be empty")
        if self.timeout_seconds < 60:  # ❌ NOT TESTED YET!
            raise ValueError("...")
```

**GOOD** (only what's needed for THIS test):
```python
# Test: only checks model_name empty validation
@dataclass(frozen=True)
class UpscaleConfig:
    model_name: str = "net_g_1000000"

    def __post_init__(self):
        if not self.model_name:
            raise ValueError("model_name cannot be empty")
# ✅ That's it! Next test will drive next feature
```

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
5. "✅ Test 1 passed! Moving to test 2: test_zips_directory_to_file()"
6. [Write test] → [Run test - RED] → [Show failure]
7. [Write minimal code] → [Run test - GREEN] → [Show pass]
8. [Commit]
9. Continue until FileArchiver is fully implemented...

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
- **Keep momentum**: Automatically proceed to next test after each success
- **Keep it simple**: Minimal code to pass, refactor later
- **Track progress**: Show test count and feature completion status

# Uncle "Bob's The Cycles of TDD"
When you first learn Test Driven Development, it sounds simple and easy. If you learned it in 1999, like I did, the rule was to simply write your unit tests first. Indeed, we called it Test First Design back then.

I sat with Kent Beck in 1999 and paired with him in order to learn. What he taught me to do was certainly test first; but it involved a more fine-grained process than I’d ever seen before. He would write one line of a failing test, and then write the corresponding line of production code to make it pass. Sometimes it was slightly more than one line; but the scale he used was was very close to line by line.

Second-by-Second nano-cycle: The Three Laws of TDD.
A few years later this fine granularity was codified into three rules: the so-called Three Laws of TDD.

You must write a failing test before you write any production code.
You must not write more of a test than is sufficient to fail, or fail to compile.
You must not write more production code than is sufficient to make the currently failing test pass.
I, and many others, have written about these three laws over the years. They now appear in many different styles, formats, and injunctive statements. But the goal is always to promote the line by line granularity that I experienced while working with Kent so long ago.

The three laws are the nano-cycle of TDD. You follow them on almost a second-by-second basis. You will likely iterate them a dozen or so times before you finish a single unit test.

Minute-by-Minute: micro-cycle: Red-Green-Refactor
If we pull back to the minute by minute scale we see the micro-cycle that experienced TDDers follow. The Red/Green/Refactor cycle.




This cycle is typically executed once for every complete unit test, or once every dozen or so cycles of the three laws. The rules of this cycle are simple.

Create a unit tests that fails
Write production code that makes that test pass.
Clean up the mess you just made.
The philosophy is based on the idea that our limited minds are not capable of pursuing the two simultaneous goals of all software systems: 1. Correct behavior. 2. Correct structure. So the RGR cycle tells us to first focus on making the software work correctly; and then, and only then, to focus on giving that working software a long-term survivable structure.

Again, many people have written about this cycle. Indeed the idea derives from Kent Beck’s original injunction:

Make it work. Make it right. Make it fast.

Another way to think about this idea is:

Getting software to work is only half of the job.

Customers value two things about software. The way it makes a machine behave; and the ease with which it can be changed. Compromise either of those two values and the software will diminish in real value to the customer.

Executing the Red/Green/Refactor cycle takes on the order of a minute or so. This is the granularity of refactoring. Refactoring is not something you do at the end of the project; it’s something you do on a minute-by-minute basis. There is no task on the project plan that says: Refactor. There is no time reserved at the end of the project, or the iteration, or the day, for refactoring. Refactoring is a continuous in-process activity, not something that is done late (and therefore optionally).

Decaminute-by-Decaminute: milli-cycle: Specific/Generic
At the 10 minute level we see the milli-cycle in operation. The Specific/Generic cycle.

As the tests get more specific, the code gets more generic.

As a test suite grows, it becomes ever more specific. i.e. it becomes an ever more detailed specification of behavior. Good software developers meet this increase in specification by increasing the generality of their code. To say this differently: Programmers make specific cases work by writing code that makes the general case work.

As a rule, the production code is getting more and more general if you can think of tests that you have not written; but that the production code will pass anyway. If the changes you make to the production code, pursuant to a test, make that test pass, but would not make other unwritten tests pass, then you are likely making the production code too specific.

It is often said that the fine grained structure of the three laws and the Red/Green/Refactor cycle lead to local-optimizations. Without the “big picture” the developer cannot imbue the software with the correct structure for the overall problem, and instead drives towards a structure that is good for the local case; but not for the general case.

The symptom of the local optimum is “Getting Stuck.” In order to make the next test pass you must write a large amount of code outside of the nano-cycle of the three laws, and even outside of the micro-cycle of RGR. In other words, you have gone down a path that forces you out of the TDD process.

Once you are stuck, the only solution is to backtrack up through the previous tests, deleting them, until you reach a test from which you can take a different fork in the road.

Why do you get stuck? Because you were not adding sufficient generality to the production code. You were making the tests too specific, to quickly. The solution is to backtrack and then add specificity to the tests more slowly, while adding generality to the production code more quickly. This frequently forces you to choose a different set of tests to follow.

To avoid getting stuck we evaluate our position every few minutes; looking for specificity in the production code. Have we taken shortcuts that make the production code resemble the tests in some way? Do the most recent changes to the production code fail to pass more tests than we have written?

This is the cycle in which we apply the Transformation Priority Premise. We look for the symptoms of over-specificity by checking the kinds of production code we have written.

Hour-by-Hour: Primary Cycle: Boundaries.
The final primary cycle of TDD is the cycle that ensures that all the other cycles are driving us towards a Clean Architecture. Ever hour or so we stop and check to see whether we have crossed, or are encroaching upon, a significant architectural boundary. Often these boundaries are difficult to see while in the throes of the nano- and micro-cycles. You can start to smell them at the decaminute level, but even then our gaze is still too narrowly focused.

So every hour or so we stop and look at the overall system. We hunt for boundaries that we want to control. We make decisions about where to draw those boundaries, and which side of those boundaries our current activities should be constrained to. And then we use those decisions to inform the nano-cycles, micro-cycles, and milli-cycles of the next hour or so – the primary cycle – of Test Driven Development.

---

**Ready! Tell me what to implement and I'll TDD it step-by-step.**



AI Test Automation Contracts (Source of Truth)

1) Gherkin feature rules
- Every Scenario must have exactly 3 step lines:
  - 1 Given
  - 1 When
  - 1 Then
- And/But are not allowed.
- Feature file must start with: Feature:
- No markdown fences ``` anywhere.

2) Step Definitions rules
- generated/steps/CancelOrderSteps.java must contain exactly:
  - 1 @Given
  - 1 @When
  - 1 @Then
- These 3 step methods are orchestration steps (business intent).
- Granular actions must be implemented as private helper methods (or via Page Objects).

3) Page Objects rules
- Page Objects live under generated/pages/
- No Cucumber annotations/imports in Page Objects.
- Public Page methods must be atomic and start with one of:
  click, select, enter, type, set, fill, open, navigate, goTo, wait, get, is, has, verify, assert
- No workflow-style public methods inside Page Objects.

4) CI Gate
- GitHub Actions runs validation only:
  python validate_artifacts.py
- LLM generation is NOT executed in GitHub Actions.

5) Architecture decision
- GitHub repo is the source of truth.
- GPU/RunPod is a disposable execution engine used only for generation.

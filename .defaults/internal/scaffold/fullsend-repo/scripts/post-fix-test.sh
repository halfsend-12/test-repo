#!/usr/bin/env bash
# post-fix-test.sh — Test the push retry logic from post-fix.sh.
#
# Extracts and tests the push-retry decision logic in isolation using shell
# functions. This avoids needing a full git repo or GitHub API access.
#
# Run from the repo root:
#   bash internal/scaffold/fullsend-repo/scripts/post-fix-test.sh

set -euo pipefail

FAILURES=0

# ---------------------------------------------------------------------------
# Test helper — reimplements the push retry logic from post-fix.sh section 5.
# Given a push exit code and output, returns the action.
# ---------------------------------------------------------------------------
decide_push_retry() {
  local push_rc="$1"
  local push_output="$2"

  if [ "${push_rc}" -eq 0 ]; then
    echo "success"
    return 0
  fi

  if echo "${push_output}" | grep -qi "non-fast-forward\|rejected\|fetch first"; then
    echo "retry:force-with-lease"
    return 0
  fi

  echo "fail:unexpected-error"
  return 0
}

run_push_retry_test() {
  local test_name="$1"
  local push_rc="$2"
  local push_output="$3"
  local expected_prefix="$4"

  local actual
  actual="$(decide_push_retry "${push_rc}" "${push_output}")"

  if [[ "${actual}" != ${expected_prefix}* ]]; then
    echo "FAIL: ${test_name}"
    echo "  push_rc:         '${push_rc}'"
    echo "  push_output:     '${push_output}'"
    echo "  expected prefix: '${expected_prefix}'"
    echo "  actual:          '${actual}'"
    FAILURES=$((FAILURES + 1))
    return
  fi

  echo "PASS: ${test_name}"
}

# --- Push retry test cases ---

# Successful push → no retry needed
run_push_retry_test "push-success" \
  "0" "Everything up-to-date" "success"

# Non-fast-forward error → retry with --force-with-lease
run_push_retry_test "push-non-fast-forward" \
  "1" "error: failed to push some refs: non-fast-forward" "retry:force-with-lease"

# Rejected error → retry with --force-with-lease
run_push_retry_test "push-rejected" \
  "1" "! [rejected] agent/42 -> agent/42 (fetch first)" "retry:force-with-lease"

# Unknown error → fail
run_push_retry_test "push-unexpected-error" \
  "1" "fatal: repository not found" "fail:unexpected-error"

# ---------------------------------------------------------------------------
# Test helper — reimplements the pre-commit auto-fix retry decision logic
# from post-fix.sh section 3. Given a pre-commit exit code and whether
# unstaged changes exist, returns the action the script would take.
# ---------------------------------------------------------------------------
decide_precommit_retry() {
  local precommit_rc="$1"          # 0 = passed, 1 = failed
  local has_unstaged="$2"          # "yes" or "no"
  local retry_precommit_rc="$3"    # 0 = passed on retry, 1 = still fails (ignored if no retry)
  local retry_has_unstaged="${4:-no}"  # "yes" if retry left unstaged changes

  if [ "${precommit_rc}" -eq 0 ]; then
    echo "pass:clean"
    return 0
  fi

  # Pre-commit failed — check for auto-fixed files
  if [ "${has_unstaged}" = "yes" ]; then
    if [ "${retry_precommit_rc}" -eq 0 ]; then
      if [ "${retry_has_unstaged}" = "yes" ]; then
        echo "blocked:retry-left-unstaged"
      else
        echo "pass:auto-fixed"
      fi
    else
      echo "blocked:retry-failed"
    fi
  else
    echo "blocked:no-auto-fix"
  fi
}

run_precommit_retry_test() {
  local test_name="$1"
  local precommit_rc="$2"
  local has_unstaged="$3"
  local retry_precommit_rc="$4"
  local expected="$5"
  local retry_has_unstaged="${6:-no}"

  local actual
  actual="$(decide_precommit_retry "${precommit_rc}" "${has_unstaged}" "${retry_precommit_rc}" "${retry_has_unstaged}")"

  if [ "${actual}" != "${expected}" ]; then
    echo "FAIL: ${test_name}"
    echo "  precommit_rc:         '${precommit_rc}'"
    echo "  has_unstaged:         '${has_unstaged}'"
    echo "  retry_precommit_rc:   '${retry_precommit_rc}'"
    echo "  retry_has_unstaged:   '${retry_has_unstaged}'"
    echo "  expected:             '${expected}'"
    echo "  actual:               '${actual}'"
    FAILURES=$((FAILURES + 1))
    return
  fi

  echo "PASS: ${test_name}"
}

# --- Pre-commit auto-fix retry test cases ---

# Pre-commit passes on first run → no retry needed
run_precommit_retry_test "precommit-passes-first-run" \
  "0" "no" "0" "pass:clean"

# Pre-commit fails, hooks auto-fixed files, retry succeeds
run_precommit_retry_test "precommit-auto-fix-retry-succeeds" \
  "1" "yes" "0" "pass:auto-fixed"

# Pre-commit fails, hooks auto-fixed files, retry still fails
run_precommit_retry_test "precommit-auto-fix-retry-fails" \
  "1" "yes" "1" "blocked:retry-failed"

# Pre-commit fails, no unstaged changes (genuine failure)
run_precommit_retry_test "precommit-genuine-failure" \
  "1" "no" "0" "blocked:no-auto-fix"

# Pre-commit passes but unstaged changes exist (e.g. hook wrote a log file)
run_precommit_retry_test "precommit-passes-with-unstaged" \
  "0" "yes" "0" "pass:clean"

# Pre-commit fails, auto-fix retry passes, but retry left unstaged changes
run_precommit_retry_test "precommit-retry-passes-but-left-unstaged" \
  "1" "yes" "0" "blocked:retry-left-unstaged" "yes"

# ---------------------------------------------------------------------------
# Test helper — reimplements the label re-trigger logic from post-fix.sh
# section 5 (#5188), exercising the actual remove-then-add call sequence
# against a stubbed `gh` so failures in either call are tolerated exactly as
# post-fix.sh tolerates them: a failed --remove-label logs a non-fatal
# ::notice:: (sanitized against :: injection) since it may just mean the
# label wasn't present, and a failed --add-label warns — neither may ever
# make the script exit nonzero, since a re-dispatch miss is not worth
# failing an otherwise-successful fix push over.
# ---------------------------------------------------------------------------
perform_relabel_retrigger() {
  local pr_number="$1" repo="$2"
  local remove_err
  remove_err="$(mktemp)"
  if ! gh pr edit "${pr_number}" --repo "${repo}" \
       --remove-label "ready-for-review" 2>"${remove_err}"; then
    local sanitized_err
    sanitized_err="$(tr '\n' ' ' < "${remove_err}" | sed 's/::/: /g')"
    echo "::notice::Could not remove ready-for-review label from PR #${pr_number} (may not have been present): ${sanitized_err}"
  fi
  rm -f "${remove_err}"
  gh pr edit "${pr_number}" --repo "${repo}" \
    --add-label "ready-for-review" 2>/dev/null || \
    echo "::warning::Failed to re-apply ready-for-review label to PR #${pr_number} — review will not be re-dispatched"
}

run_relabel_test() {
  local test_name="$1" fail_call="$2" expect_warning="$3" expect_notice="${4:-no}"

  # Stub gh: fail whichever call fail_call names, succeed otherwise. Records
  # the exact invocation (not just substring presence) so a bug in argument
  # order/values (e.g. pr_number and repo swapped) fails this test, and
  # emits a poison stderr message on the remove call to verify sanitization.
  local gh_call_log
  gh_call_log="$(mktemp)"
  gh() {
    echo "$*" >> "${gh_call_log}"
    if [[ "$*" == *"--remove-label"* ]]; then
      if [[ "${fail_call}" == "remove" || "${fail_call}" == "both" ]]; then
        echo "HTTP 500::internal error
with a newline" >&2
        return 1
      fi
      return 0
    elif [[ "$*" == *"--add-label"* ]]; then
      [[ "${fail_call}" == "add" || "${fail_call}" == "both" ]] && return 1
      return 0
    fi
    return 0
  }

  local output rc
  output="$(perform_relabel_retrigger "123" "org/repo")"
  rc=$?
  unset -f gh

  if [ "${rc}" -ne 0 ]; then
    echo "FAIL: ${test_name} (exited ${rc} — re-trigger must never hard-fail)"
    FAILURES=$((FAILURES + 1))
    rm -f "${gh_call_log}"
    return
  fi

  local expected_calls actual_calls
  expected_calls=$'pr edit 123 --repo org/repo --remove-label ready-for-review\npr edit 123 --repo org/repo --add-label ready-for-review'
  actual_calls="$(cat "${gh_call_log}")"
  rm -f "${gh_call_log}"
  if [ "${actual_calls}" != "${expected_calls}" ]; then
    echo "FAIL: ${test_name} (unexpected gh invocation)"
    echo "  expected: ${expected_calls}"
    echo "  actual:   ${actual_calls}"
    FAILURES=$((FAILURES + 1))
    return
  fi

  local has_warning="no"
  echo "${output}" | grep -q "::warning::Failed to re-apply" && has_warning="yes"
  if [ "${has_warning}" != "${expect_warning}" ]; then
    echo "FAIL: ${test_name}"
    echo "  expected warning: '${expect_warning}', got: '${has_warning}'"
    echo "  output: ${output}"
    FAILURES=$((FAILURES + 1))
    return
  fi

  local has_notice="no"
  echo "${output}" | grep -q "::notice::Could not remove ready-for-review label" && has_notice="yes"
  if [ "${has_notice}" != "${expect_notice}" ]; then
    echo "FAIL: ${test_name}"
    echo "  expected notice: '${expect_notice}', got: '${has_notice}'"
    echo "  output: ${output}"
    FAILURES=$((FAILURES + 1))
    return
  fi

  # When the notice fires, the injected "HTTP 500::internal error" plus a
  # real newline must be sanitized — no bare "::" beyond the recognized
  # ::notice:: prefix, and no embedded line breaks, since this text is
  # embedded in a GHA workflow command.
  if [ "${has_notice}" = "yes" ]; then
    local notice_line notice_body
    notice_line="$(echo "${output}" | grep "::notice::Could not remove")"
    notice_body="${notice_line#*::notice::}"
    if [[ "${notice_body}" == *"::"* ]]; then
      echo "FAIL: ${test_name} (unsanitized :: sequence leaked into notice)"
      echo "  output: ${output}"
      FAILURES=$((FAILURES + 1))
      return
    fi

    # An unsanitized embedded newline would split the injected stderr across
    # an extra raw output line with no :: prefix. Expect exactly one line
    # for the notice, plus one more if the add-label warning also fired.
    local expected_lines=1
    [ "${expect_warning}" = "yes" ] && expected_lines=2
    local actual_lines
    actual_lines="$(echo "${output}" | wc -l)"
    if [ "${actual_lines}" -ne "${expected_lines}" ]; then
      echo "FAIL: ${test_name} (embedded newline leaked into notice — expected ${expected_lines} output line(s), got ${actual_lines})"
      echo "  output: ${output}"
      FAILURES=$((FAILURES + 1))
      return
    fi
  fi

  echo "PASS: ${test_name}"
}

# --- Label re-trigger test cases ---

# Both calls succeed → no warning, no notice.
run_relabel_test "relabel-both-succeed" "none" "no" "no"

# Remove fails (e.g. label wasn't present — first fix run on a PR whose
# label was never applied, or a transient API error) — non-fatal notice,
# add still runs and succeeds, no warning.
run_relabel_test "relabel-remove-fails-add-succeeds" "remove" "no" "yes"

# Add fails (e.g. API error, label deleted from repo) — warns, does not fail.
run_relabel_test "relabel-add-fails" "add" "yes" "no"

# Both fail — notice for the remove, warning for the add, never a hard failure.
run_relabel_test "relabel-both-fail" "both" "yes" "yes"

# ---------------------------------------------------------------------------
# Structural test — the relabel step's gh calls must run after GH_TOKEN is
# exported in the real post-fix.sh. This is what would have caught the
# confirmed regression where the relabel calls ran two steps before
# `export GH_TOKEN="${PUSH_TOKEN}"`, so they authenticated with whatever
# token the runner happened to have ambient (or none), silently defeating
# the entire fix while post-fix-test.sh's reimplemented logic passed clean.
# ---------------------------------------------------------------------------
run_gh_token_ordering_test() {
  local script_dir post_fix_sh
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  post_fix_sh="${script_dir}/post-fix.sh"

  local remove_line token_export_line
  remove_line="$(grep -n -- '--remove-label "ready-for-review"' "${post_fix_sh}" | head -1 | cut -d: -f1)"
  token_export_line="$(grep -n 'export GH_TOKEN="\${PUSH_TOKEN}"' "${post_fix_sh}" | head -1 | cut -d: -f1)"

  if [ -z "${remove_line}" ] || [ -z "${token_export_line}" ]; then
    echo "FAIL: gh-token-ordering (could not locate relabel call or GH_TOKEN export in post-fix.sh)"
    FAILURES=$((FAILURES + 1))
    return
  fi

  if [ "${remove_line}" -lt "${token_export_line}" ]; then
    echo "FAIL: gh-token-ordering (relabel --remove-label at line ${remove_line} runs before GH_TOKEN export at line ${token_export_line} — gh calls would be unauthenticated)"
    FAILURES=$((FAILURES + 1))
    return
  fi

  echo "PASS: gh-token-ordering"
}

run_gh_token_ordering_test

# --- Summary ---

echo ""
if [ ${FAILURES} -gt 0 ]; then
  echo "${FAILURES} test(s) failed"
  exit 1
fi
echo "All tests passed"

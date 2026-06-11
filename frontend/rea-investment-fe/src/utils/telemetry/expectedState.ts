// Shared resolver for the expected-baseline display state used across the
// O&M and portfolio production charts/widgets.
//
// The backend's V2 expected-baseline calc returns an additive `expected_state`
// alongside the legacy `expected_baseline_available` boolean. This resolver maps
// either signal to a single display descriptor so every chart branches the same
// way:
//   available              -> show expected normally
//   partial                -> show expected (where present) + a "partial" note
//   missing_inputs         -> N/A, weather inputs were missing
//   pre_pto                -> N/A, period predates the PTO date
//   baseline_not_available -> N/A, no active baseline
//
// `expected_state` may be absent on older / non-V2 responses, so we fall back to
// the boolean (present + true -> available, present + false ->
// baseline_not_available). Honest N/A is always preferred over a fabricated 0.

export type ExpectedState = 'available' | 'partial' | 'missing_inputs' | 'pre_pto' | 'baseline_not_available';

export interface ExpectedStateSource {
  expected_state?: ExpectedState | string | null;
  expected_baseline_available?: boolean | null;
}

export interface ExpectedStateDisplay {
  state: ExpectedState;
  // Render the expected series/value at all (true for `available` + `partial`).
  showExpected: boolean;
  // Append a "partial coverage" indicator alongside the expected value.
  isPartial: boolean;
  // Short human term for the state (e.g. a chip / inline label).
  term: string;
  // Longer caption explaining the state ('' for fully `available`).
  reason: string;
}

const KNOWN_STATES: ExpectedState[] = ['available', 'partial', 'missing_inputs', 'pre_pto', 'baseline_not_available'];

const TERMS: Record<ExpectedState, string> = {
  available: 'Available',
  partial: 'Partial',
  missing_inputs: 'Missing inputs',
  pre_pto: 'Pre-PTO',
  baseline_not_available: 'Baseline not available'
};

// Scope-neutral wording so the same captions read correctly for both per-site
// and rolled-up company/portfolio widgets.
const REASONS: Record<ExpectedState, string> = {
  available: '',
  partial:
    'Expected could be computed for only part of this period; the value shown covers the available intervals only.',
  missing_inputs: 'Weather inputs needed to compute expected were unavailable for this period, so expected is N/A.',
  pre_pto: 'This period predates the permission-to-operate date, so no expected is shown yet.',
  baseline_not_available: 'Expected baseline is not available, so expected production is shown as N/A.'
};

export const resolveExpectedState = (source?: ExpectedStateSource | null): ExpectedStateDisplay => {
  const raw = source?.expected_state;
  let state: ExpectedState;

  if (typeof raw === 'string' && (KNOWN_STATES as string[]).includes(raw)) {
    state = raw as ExpectedState;
  } else {
    // Backward-compatible fallback when `expected_state` is absent: the boolean
    // defaults to true (treat unknown as available) so legacy responses behave
    // exactly as before.
    const available = source?.expected_baseline_available ?? true;
    state = available ? 'available' : 'baseline_not_available';
  }

  return {
    state,
    showExpected: state === 'available' || state === 'partial',
    isPartial: state === 'partial',
    term: TERMS[state],
    reason: REASONS[state]
  };
};

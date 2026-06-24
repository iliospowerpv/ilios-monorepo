import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import InventoryReconciliationChip from '../InventoryReconciliationChip';
import type { InventoryReconciliationSummary } from '../../../../types/telemetryV2';

const summary = (overrides: Partial<InventoryReconciliationSummary> = {}): InventoryReconciliationSummary => ({
  status: 'matched',
  status_label: 'Matched',
  status_explanation: 'Documented inventory matches telemetry.',
  has_blocking_mismatch: false,
  weather_dependency_unsatisfied: false,
  open_actionable_mismatch_count: 0,
  informational_mismatch_count: 0,
  ...overrides
});

describe('InventoryReconciliationChip', () => {
  test('renders the backend status_label when a summary is provided', () => {
    render(<InventoryReconciliationChip summary={summary()} />);
    const chip = screen.getByTestId('inventory-reconciliation-chip');
    expect(chip).toHaveAttribute('data-state', 'ready');
    expect(chip).toHaveAttribute('data-status', 'matched');
    expect(screen.getByText('Matched')).toBeInTheDocument();
  });

  test('shows a neutral loading chip while fetching', () => {
    render(<InventoryReconciliationChip loading />);
    const chip = screen.getByTestId('inventory-reconciliation-chip');
    expect(chip).toHaveAttribute('data-state', 'loading');
    expect(screen.getByText('Checking…')).toBeInTheDocument();
  });

  test('never fabricates a match when the summary is absent', () => {
    render(<InventoryReconciliationChip summary={undefined} />);
    const chip = screen.getByTestId('inventory-reconciliation-chip');
    expect(chip).toHaveAttribute('data-state', 'unavailable');
    expect(screen.getByText('Status unavailable')).toBeInTheDocument();
    expect(screen.queryByText('Matched')).not.toBeInTheDocument();
  });

  test('shows Status unavailable on error even without a summary', () => {
    render(<InventoryReconciliationChip error />);
    const chip = screen.getByTestId('inventory-reconciliation-chip');
    expect(chip).toHaveAttribute('data-state', 'unavailable');
  });

  test('renders a blocking indicator when the summary has a blocking mismatch', () => {
    render(
      <InventoryReconciliationChip
        summary={summary({
          status: 'needs_reconciliation',
          status_label: 'Needs reconciliation',
          has_blocking_mismatch: true,
          open_actionable_mismatch_count: 2
        })}
      />
    );
    expect(screen.getByTestId('inventory-reconciliation-blocking-indicator')).toBeInTheDocument();
  });

  test('prefers backend status_label over the local fallback label', () => {
    render(<InventoryReconciliationChip summary={summary({ status_label: 'Custom backend label' })} />);
    expect(screen.getByText('Custom backend label')).toBeInTheDocument();
  });

  describe('deep link (to prop)', () => {
    const RECON_TO = '/project-hub/projects/42/reconciliation';

    test('an available chip is clickable and links to the Reconciliation view', () => {
      render(
        <MemoryRouter>
          <InventoryReconciliationChip summary={summary()} to={RECON_TO} />
        </MemoryRouter>
      );
      const chip = screen.getByTestId('inventory-reconciliation-chip');
      expect(chip).toHaveAttribute('data-clickable', 'true');
      // The link target is exactly the site's Reconciliation route.
      const link = screen.getByTestId('inventory-reconciliation-chip-link');
      expect(link.tagName).toBe('A');
      expect(link).toHaveAttribute('href', RECON_TO);
    });

    test('an unavailable chip is never clickable even when a target is provided', () => {
      render(
        <MemoryRouter>
          <InventoryReconciliationChip summary={undefined} to={RECON_TO} />
        </MemoryRouter>
      );
      const chip = screen.getByTestId('inventory-reconciliation-chip');
      expect(chip).toHaveAttribute('data-state', 'unavailable');
      expect(screen.queryByTestId('inventory-reconciliation-chip-link')).not.toBeInTheDocument();
      // No anchor anywhere — an absent summary must not present an actionable link.
      expect(chip.querySelector('a')).toBeNull();
    });

    test('a loading chip is never clickable even when a target is provided', () => {
      render(
        <MemoryRouter>
          <InventoryReconciliationChip loading to={RECON_TO} />
        </MemoryRouter>
      );
      const chip = screen.getByTestId('inventory-reconciliation-chip');
      expect(chip).toHaveAttribute('data-state', 'loading');
      expect(screen.queryByTestId('inventory-reconciliation-chip-link')).not.toBeInTheDocument();
    });

    test('an available chip without a target stays informational (not a link)', () => {
      render(<InventoryReconciliationChip summary={summary()} />);
      const chip = screen.getByTestId('inventory-reconciliation-chip');
      expect(chip).toHaveAttribute('data-clickable', 'false');
      expect(screen.queryByTestId('inventory-reconciliation-chip-link')).not.toBeInTheDocument();
      expect(chip.querySelector('a')).toBeNull();
    });
  });
});

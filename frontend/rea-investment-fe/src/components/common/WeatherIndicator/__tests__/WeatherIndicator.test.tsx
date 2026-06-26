import React from 'react';
import { render, screen } from '@testing-library/react';

import WeatherIndicator from '../WeatherIndicator';
import type { ObservedCondition } from '../../../../types/telemetryV2';

const baseCondition: ObservedCondition = {
  state: 'sunny',
  label: 'Sunny / clear (observed)',
  light_level: 'strong',
  observed_irradiance_wm2: 900,
  plane_governed: false,
  temperature: null,
  confidence: 'observed_uncalibrated',
  tier: 'A',
  as_of_utc: null,
  as_of_site_local: null,
  data_quality: 'fresh'
};

describe('WeatherIndicator', () => {
  test('renders a state-driven icon with an accessible label from the condition', () => {
    render(<WeatherIndicator condition={baseCondition} />);

    expect(screen.getByTestId('weather-indicator__component')).toBeInTheDocument();
    expect(screen.getByLabelText('Sunny / clear (observed)')).toBeInTheDocument();
  });

  test('renders the honest "unavailable" glyph when the condition is null (never fabricated)', () => {
    render(<WeatherIndicator condition={null} />);

    expect(screen.getByLabelText('Observed weather unavailable')).toBeInTheDocument();
  });

  test('overcast_unknown never says "rain" in its accessible label', () => {
    render(
      <WeatherIndicator
        condition={{
          ...baseCondition,
          state: 'overcast_unknown',
          label: 'Overcast / precipitation (undetermined)'
        }}
      />
    );

    const label = screen.getByLabelText(/precipitation \(undetermined\)/i);
    expect(label).toBeInTheDocument();
    expect(label.getAttribute('aria-label')?.toLowerCase()).not.toContain('rain');
  });

  test('falls back to the legacy imageSrc path when no condition prop is provided', () => {
    render(<WeatherIndicator imageSrc={null} />);

    expect(screen.getByTestId('weather-indicator__component')).toBeInTheDocument();
  });
});

import React from 'react';
import { render, screen } from '@testing-library/react';

import WeatherIndicator from '../WeatherIndicator';

describe('WeatherIndicator', () => {
  test('renders the component', () => {
    render(<WeatherIndicator value="Sunny" />);

    expect(screen.getByTestId('weather-indicator__component')).toBeInTheDocument();
  });
});

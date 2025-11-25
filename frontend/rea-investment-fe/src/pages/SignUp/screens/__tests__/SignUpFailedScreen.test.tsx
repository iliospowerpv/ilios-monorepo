import { render, screen } from '@testing-library/react';
import { SignUpFailedScreen } from '../SignUpFailedScreen';

describe('BlankScreen', () => {
  it('should render component correctly', () => {
    render(
      <SignUpFailedScreen
        email=""
        token=""
        isSubmitPending={false}
        formSubmit={() => Promise.resolve()}
        failureReason="Something went wrong when..."
        errorMessage="Token validation failed"
      />
    );

    const title = screen.getByText('Failure');
    const failureReasonText = screen.getByText('Something went wrong when...');
    const errorText = screen.getByText('Token validation failed');

    expect(title).toBeInTheDocument();
    expect(failureReasonText).toBeInTheDocument();
    expect(errorText).toBeInTheDocument();
  });
});

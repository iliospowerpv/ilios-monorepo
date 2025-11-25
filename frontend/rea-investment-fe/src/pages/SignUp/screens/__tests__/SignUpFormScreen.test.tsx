import { render, screen } from '@testing-library/react';
import { SignUpFormScreen } from '../SignUpFormScreen';

describe('SignUpFormScreen', () => {
  it('should render sign-up form correctly', () => {
    render(
      <SignUpFormScreen
        email="curtis.weaver@example.com"
        token=""
        isSubmitPending={false}
        formSubmit={() => Promise.resolve()}
      />
    );

    const title = screen.getByText('Account Creation');
    const infoText = screen.getByText('Finish profile creation for email:');
    const emailText = screen.getByText('curtis.weaver@example.com');
    const passwordInput = screen.getByLabelText('Password');
    const confirmPasswordInput = screen.getByLabelText('Repeat Password');

    expect(title).toBeInTheDocument();
    expect(infoText).toBeInTheDocument();
    expect(emailText).toBeInTheDocument();
    expect(passwordInput).toBeInTheDocument();
    expect(confirmPasswordInput).toBeInTheDocument();
  });
});

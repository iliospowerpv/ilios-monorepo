import { render, screen } from '@testing-library/react';
import { SignUpSuccesScreen } from '../SignUpSuccesScreen';

jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: jest.fn()
}));

describe('SignUpSuccesScreen', () => {
  it('should render component correctly', () => {
    render(<SignUpSuccesScreen email="" token="" isSubmitPending={false} formSubmit={() => Promise.resolve()} />);

    const title = screen.getByText('Success');
    const infoText = screen.getByText('Your password has been changed.');
    const backToLoginBtn = screen.getByTestId('sign-up_back-btn');

    expect(title).toBeInTheDocument();
    expect(infoText).toBeInTheDocument();
    expect(backToLoginBtn).toBeInTheDocument();
  });
});

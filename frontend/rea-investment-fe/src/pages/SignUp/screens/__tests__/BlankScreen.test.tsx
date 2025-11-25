import { render } from '@testing-library/react';
import { BlankScreen } from '../BlankScreen';

describe('BlankScreen', () => {
  it('should render empty backdrop without issues', () => {
    render(<BlankScreen email="" token="" isSubmitPending={false} formSubmit={() => Promise.resolve()} />);
  });
});

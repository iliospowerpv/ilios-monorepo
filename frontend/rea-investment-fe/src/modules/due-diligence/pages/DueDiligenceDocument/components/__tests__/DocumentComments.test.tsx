import { screen, render } from '@testing-library/react';
import { DocumentComments } from '../DocumentComments';

jest.mock('../NewComment', () => ({
  __esModule: true,
  default: () => <div>NewComment-component-placeholder</div>
}));

jest.mock('../CommentsList', () => ({
  __esModule: true,
  default: () => <div>CommentsList-component-placeholder</div>
}));

describe('DocumentComments component', () => {
  it('should render component correctly', () => {
    render(<DocumentComments documentId={22} />);

    expect(screen.getByText('Comments')).toBeInTheDocument();
    expect(screen.getByText('CommentsList-component-placeholder')).toBeInTheDocument();
    expect(screen.getByText('NewComment-component-placeholder')).toBeInTheDocument();
  });
});

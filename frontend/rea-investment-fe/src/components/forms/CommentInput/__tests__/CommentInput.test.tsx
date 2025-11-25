import { render, screen, act, waitFor } from '@testing-library/react';
import UserEvent from '@testing-library/user-event';
import React from 'react';

import CommentInput, { CommentInputValue } from '../CommentInput';

const CommentInputTestComponent = () => {
  const [value, setValue] = React.useState<CommentInputValue>({ plainValue: '', mentions: [] });

  return (
    <CommentInput
      value={value}
      onChange={setValue}
      suggestions={[{ display: 'Yulian', id: '5' }]}
      placeholder="Add a comment"
    />
  );
};

describe('CommentInput component', () => {
  it('should render and function correctly', async () => {
    // eslint-disable-next-line @typescript-eslint/ban-ts-comment
    // @ts-ignore
    global.ResizeObserver = function () {
      return {
        observe: jest.fn(),
        unobserve: jest.fn(),
        disconnect: jest.fn()
      };
    };

    // eslint-disable-next-line @typescript-eslint/ban-ts-comment
    // @ts-ignore
    global.MutationObserver = function () {
      return {
        observe: jest.fn(),
        disconnect: jest.fn()
      };
    };

    await act(() => {
      render(<CommentInputTestComponent />);
    });

    const commentInputArea = screen.getByPlaceholderText('Add a comment');

    UserEvent.type(commentInputArea, '@Yu');

    await waitFor(() => {
      expect(screen.getByText('lian')).toBeInTheDocument;
    });

    UserEvent.keyboard('{enter}');

    await waitFor(() => {
      expect(commentInputArea).toHaveValue('  @Yulian   ');
    });
  });
});

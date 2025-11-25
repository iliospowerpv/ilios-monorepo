import { render, screen } from '@testing-library/react';
import CommentListItem from '../CommentListItem';

describe('CommentListItem', () => {
  it('should render and function correctly', () => {
    const commentDataMock = {
      text: "let's tag @[Yurii Kostiv](178) and @[Liubov Mykhailova](185) and probably also @[Nat Test System Admin](4) and see what we get",
      date: '2024-08-28T11:26:51.614527',
      first_name: 'Yulian',
      last_name: 'Terletskyi'
    };

    render(
      <CommentListItem
        user={{ first_name: commentDataMock.first_name, last_name: commentDataMock.last_name }}
        text={commentDataMock.text}
        date={commentDataMock.date}
      />
    );

    expect(screen.getByText('@Yurii Kostiv')).toBeInTheDocument();
    expect(screen.getByText('@Nat Test System Admin')).toBeInTheDocument();
  });
});

import React from 'react';
import DOMPurify from 'dompurify';

const mentionTagClassname = 'comment-user-mention';

const useParsedComment = (commentTextValue: string) =>
  React.useMemo(
    () => ({
      parsedComment: DOMPurify.sanitize(
        commentTextValue.replace(/@\[(.+?)\]\(.+?\)/g, `<span class="${mentionTagClassname}">@$1</span>`)
      ),
      mentionTagClassname
    }),
    [commentTextValue]
  );

export default useParsedComment;

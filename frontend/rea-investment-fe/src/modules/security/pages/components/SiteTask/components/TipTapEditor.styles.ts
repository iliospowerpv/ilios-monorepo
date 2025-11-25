import styled from 'styled-components';
import { EditorContent } from '@tiptap/react';

export const StyledEditorContent = styled(EditorContent)`
  border: 1px solid rgba(0, 0, 0, 0.23);
  cursor: text;
  min-height: 130px;
  font-size: 16px;
  line-height: 1.5;
  font-family: Lato, sans-serif;
  font-weight: 400;
  outline: none;
  white-space: pre-wrap;

  p.is-editor-empty:first-child::before {
    color: #adb5bd;
    content: attr(data-placeholder);
    float: left;
    height: 0;
    pointer-events: none;
  }

  .ProseMirror {
    padding: 10px 14px;
    * {
      margin: 0;
    }
  }

  .ProseMirror-focused {
    padding: 10px 14px;
    min-height: 128px;
    outline: none;
    &:focus-visible {
      outline: 2px solid #1d1d1d;
    }

    * {
      margin: 0;
      outline: none;
      &:focus-visible {
        outline: none;
      }
    }
  }
`;

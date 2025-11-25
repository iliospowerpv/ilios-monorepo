import React, { useEffect } from 'react';
import { useEditor } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Link from '@tiptap/extension-link';
import { StyledEditorContent } from './TipTapEditor.styles';
import Placeholder from '@tiptap/extension-placeholder';

interface TipTapProps {
  value: string;
  descriptionText: string | null;
  onChange: (content: string) => void;
  isEditing: boolean;
}

export const Tiptap: React.FC<TipTapProps> = ({ value, descriptionText, onChange, isEditing }) => {
  const editor = useEditor({
    extensions: [
      StarterKit,
      Link.configure({
        openOnClick: true,
        defaultProtocol: 'https'
      }),
      Placeholder.configure({
        placeholder: 'Add description…',
        showOnlyWhenEditable: false
      })
    ],
    content: value,
    editable: isEditing,
    onUpdate: ({ editor }) => {
      onChange(editor.getHTML());
    }
  });

  useEffect(() => {
    if (descriptionText === value && editor) {
      editor.commands.setContent(descriptionText);
    }
  }, [value, descriptionText, editor]);

  return <StyledEditorContent editor={editor} />;
};

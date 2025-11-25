import React, { memo } from 'react';
import FormHelperText from '@mui/material/FormHelperText';
import MenuItem from '@mui/material/MenuItem';
import {
  Mention,
  MentionsInput,
  SuggestionDataItem,
  OnChangeHandlerFunc,
  DataFunc,
  DisplayTransformFunc
} from 'react-mentions';
import * as _ from 'lodash';

import { mentionInputClassName, floatingLabelClassName, CommentInputContainer } from './CommentInput.styles';

type SuggestionRendererFunc = (
  suggestion: SuggestionDataItem,
  search: string,
  highlightedDisplay: React.ReactNode,
  index: number,
  focused: boolean
) => React.ReactNode;

const SuggestionRenderer: SuggestionRendererFunc = (suggestion: SuggestionDataItem, search, highlightedDisplay) => {
  const itemContent = highlightedDisplay;

  if (suggestion.display?.startsWith('>>--hidden--<<')) {
    return (
      <MenuItem
        disabled
        component="div"
        sx={{
          height: '100%',
          width: '100%',
          pointerEvents: 'none',
          cursor: 'default',
          ['&:hover']: { backgroundColor: 'transparent' }
        }}
      >
        No matches found
      </MenuItem>
    );
  }

  return (
    <MenuItem component="div" sx={{ height: '100%', width: '100%', ['&:hover']: { backgroundColor: 'transparent' } }}>
      {itemContent}
    </MenuItem>
  );
};

export interface CommentInputValue {
  plainValue: string;
  mentions: string[];
}

interface CommentInputProps {
  value: CommentInputValue;
  suggestions: SuggestionDataItem[];
  error?: boolean;
  disabled?: boolean;
  isLoading?: boolean;
  helperText?: string;
  placeholder?: string;
  onChange: (value: CommentInputValue) => void;
}

interface CommentInputRef {
  focus: () => void;
}

const CommentInput = React.forwardRef<CommentInputRef, CommentInputProps>((props, ref) => {
  const { value, disabled, isLoading, helperText, placeholder, error, suggestions, onChange } = props;

  const [highlighterScrollbarOffset, setHighlighterScrollbarOffset] = React.useState(0);
  const [focused, setFocused] = React.useState(false);

  const textareaNode = React.useRef<HTMLTextAreaElement | null>(null);

  const handleChange: OnChangeHandlerFunc = (event, newValue, newPlainTextValue, mentions) => {
    const textValue = event.target.value;

    if (textValue.includes('>>--hidden--<<')) {
      const withoutPlaceholderTags = textValue.replace(/@\[>>--hidden--<<\|[^|]*\|>>\]\(null\)/g, '');
      const filteredMentions = mentions.filter(mention => mention.id !== 'null').map(mention => mention.id);
      onChange({ plainValue: withoutPlaceholderTags, mentions: _.uniq(filteredMentions) });
      return;
    }

    onChange({ plainValue: textValue, mentions: _.uniq(mentions.map(mention => mention.id)) });
  };

  const handleTextareaDimensionsChange = React.useCallback(() => {
    if (textareaNode.current) {
      const scrollbarOffset = textareaNode.current.offsetWidth - textareaNode.current.clientWidth;
      setHighlighterScrollbarOffset(scrollbarOffset);
    }
  }, []);

  React.useEffect(() => {
    handleTextareaDimensionsChange();

    if (textareaNode.current) {
      const node = textareaNode.current;
      const resizeObserver = new ResizeObserver(handleTextareaDimensionsChange);
      const mutationObserver = new MutationObserver(handleTextareaDimensionsChange);

      resizeObserver.observe(node);
      mutationObserver.observe(node, { childList: true, subtree: true, characterData: true });

      return () => {
        resizeObserver.unobserve(node);
        resizeObserver.disconnect();
        mutationObserver.disconnect();
      };
    }
  }, [handleTextareaDimensionsChange]);

  const handleFocus = React.useCallback(() => {
    textareaNode.current && textareaNode.current.focus();
    setFocused(true);
  }, []);

  const handleBlur = React.useCallback(() => {
    setFocused(false);
  }, []);

  const displayTransform: DisplayTransformFunc = (url, display) => `\u00A0\u00A0@${display}\u00A0\u00A0`;

  const filterSuggestions: DataFunc = React.useCallback<DataFunc>(
    async (search, callback) => {
      const suggestionsFilterFunc = (suggestion: SuggestionDataItem): boolean => {
        const displayValue = suggestion.display?.toLowerCase() ?? '';
        const query = search.toLowerCase();

        return displayValue.includes(query);
      };

      const filteredSuggestions = suggestions.filter(suggestionsFilterFunc);

      if (filteredSuggestions.length === 0) {
        const query = search.toLowerCase();
        const placeholderEntry: SuggestionDataItem = {
          display: `>>--hidden--<<|${query}|>>`,
          id: 'null'
        };
        return callback([placeholderEntry]);
      }

      return callback(
        filteredSuggestions.map(suggestion => ({ ...suggestion, display: suggestion.display?.replace(/ /g, '\u00A0') }))
      );
    },
    [suggestions]
  );

  React.useImperativeHandle(
    ref,
    () => ({
      focus: () => {
        handleFocus();
      }
    }),
    [handleFocus]
  );

  return (
    <CommentInputContainer scrollbarOffset={highlighterScrollbarOffset} fullWidth error={error}>
      <div className={focused ? 'input-wrapper focused' : 'input-wrapper'} onBlur={handleBlur} onClick={handleFocus}>
        <MentionsInput
          allowSuggestionsAboveCursor
          className={mentionInputClassName}
          inputRef={textareaNode}
          disabled={disabled}
          onFocus={handleFocus}
          onChange={handleChange}
          value={value.plainValue}
          placeholder={placeholder}
        >
          <Mention
            trigger="@"
            appendSpaceOnAdd
            isLoading={isLoading}
            displayTransform={displayTransform}
            data={filterSuggestions}
            renderSuggestion={SuggestionRenderer}
            className={floatingLabelClassName}
          />
        </MentionsInput>
      </div>
      {helperText && <FormHelperText>{helperText}</FormHelperText>}
    </CommentInputContainer>
  );
});

CommentInput.displayName = 'CommentInput';

export default memo(CommentInput);

import { ComponentProps } from 'react';
import { styled } from '@mui/material/styles';
import FormControl from '@mui/material/FormControl';

type FormControlProps = ComponentProps<typeof FormControl>;

interface CommentInputContainerProps extends FormControlProps {
  scrollbarOffset?: number;
}

export const mentionInputClassName = 'mention-input';
export const floatingLabelClassName = 'mention-input-floating-label';

export const CommentInputContainer = styled(FormControl, {
  shouldForwardProp: propName => propName !== 'scrollbarOffset'
})<CommentInputContainerProps>(({ scrollbarOffset, error }) => ({
  ['.input-wrapper']: {
    fontSize: '1rem',
    padding: '1em',
    borderStyle: 'solid',
    borderWidth: '1px',
    borderColor: error ? '#d32f2f' : 'rgba(0, 0, 0, 0.23)',
    cursor: 'text',

    ['&:hover']: {
      borderColor: error ? '#d32f2f' : 'rgba(0, 0, 0, 0.87)'
    },

    ['&.focused']: {
      borderColor: error ? '#d32f2f' : '#1D1D1D',
      borderWidth: '2px',
      padding: 'calc(1em - 1px)'
    },

    [`& .${mentionInputClassName}`]: {
      width: '100%',
      position: 'relative',
      overflowY: 'visible',

      [`& .${mentionInputClassName}__control`]: {
        fontFamily: 'Lato,sans-serif',
        fontWeight: '400',
        fontSize: '1rem',
        lineHeight: '1.5em',
        color: 'rgba(0, 0, 0, 0.87)',
        backgroundColor: 'rgb(255, 255, 255)',

        [`&.${mentionInputClassName}--multiline`]: {
          fontFamily: 'monospace',
          minHeight: '1.5em'
        },

        [`& .${mentionInputClassName}__highlighter`]: {
          color: 'transparent',
          width: '100%',
          border: 'none !important',
          minHeight: '1.5em',
          maxHeight: 'calc(5 * 1.5em)',
          overflow: 'hidden',
          position: 'relative',
          overflowWrap: 'break-word',
          outline: 'none',
          boxSizing: 'border-box',
          textAlign: 'start',
          whiteSpace: 'pre-wrap',
          lineHeight: 'inherit',
          fontFamily: 'inherit',
          letterSpacing: 'inherit',
          padding: 0,
          paddingRight: scrollbarOffset ? `${scrollbarOffset}px` : 0,
          fontFeatureSettings: 'normal',
          fontKerning: 'auto',
          fontOpticalSizing: 'auto',
          fontStretch: '100%',
          fontStyle: 'normal',
          fontVariantAlternates: 'normal',
          fontVariantCaps: 'normal',
          fontVariantEastAsian: 'normal',
          fontVariantLigatures: 'normal',
          fontVariantNumeric: 'normal',
          fontVariantPosition: 'normal',
          fontVariationSettings: 'normal',
          textRendering: 'auto',
          textWrap: 'wrap !important',
          whiteSpaceCollapse: 'preserve !important'
        },

        [`& .${mentionInputClassName}__input`]: {
          animationName: 'mui-auto-fill-cancel',
          animationDuration: '10ms',
          lineHeight: 'inherit',
          top: '0px',
          left: '0px',
          width: '100%',
          bottom: '0px',
          border: 'none',
          minHeight: '1.5em',
          maxHeight: 'calc(5 * 1.5em)',
          whiteSpace: 'pre-wrap',
          overflowWrap: 'break-word',
          margin: '0px',
          resize: 'none',
          outline: 'none',
          display: 'block',
          overflow: 'auto !important',
          position: 'absolute',
          fontSize: 'inherit',
          boxSizing: 'border-box',
          fontFamily: 'inherit',
          letterSpacing: 'inherit',
          backgroundColor: 'transparent',
          padding: 0,

          ['&::placeholder']: {
            color: 'rgba(0, 0, 0, 0.4)'
          }
        }
      },

      [`& .${mentionInputClassName}__suggestions`]: {
        [`& .${mentionInputClassName}__suggestions__list`]: {
          backgroundColor: 'white',
          border: '1px solid rgba(0,0,0,0.15)',
          fontSize: 14
        },

        [`& .${mentionInputClassName}__suggestions__item`]: {
          padding: '5px 15px',
          borderBottom: '1px solid rgba(0,0,0,0.15)',

          ['&:last-child']: {
            borderBottom: 'none'
          },

          ['&:has(.Mui-disabled)']: {
            pointerEvents: 'none',
            cursor: 'default !important'
          }
        },

        [`& .${mentionInputClassName}__suggestions__item--focused`]: {
          backgroundColor: 'rgba(0, 0, 0, 0.04)'
        }
      },

      [`.${floatingLabelClassName}`]: {
        borderRadius: '12px',
        paddingBottom: '3px',
        paddingTop: '1px',
        position: 'relative',
        fontWeight: '400 !important',
        backgroundColor: '#1D1D1D',
        color: '#FFFFFF',
        zIndex: 1,
        pointerEvents: 'none'
      }
    }
  }
}));

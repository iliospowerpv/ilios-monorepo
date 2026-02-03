import { useEffect, useState, useCallback, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';

export type FocusType = 'document' | 'alert' | 'device' | 'task' | 'obligation' | 'budget' | null;

export interface FocusState {
  focusType: FocusType;
  focusId: number | null;
  isHighlighted: boolean;
  notFoundMessage: string | null;
}

export interface UseFocusHighlightResult {
  focusState: FocusState;
  getItemHighlightClass: (itemId: number, itemType: FocusType) => string;
  markItemFound: () => void;
  markItemNotFound: (message?: string) => void;
  scrollToItem: (element: HTMLElement | null) => void;
  clearFocus: () => void;
}

export const HIGHLIGHT_CLASS = 'focus-highlight';
export const HIGHLIGHT_DURATION = 2000;

export function useFocusHighlight(): UseFocusHighlightResult {
  const [searchParams, setSearchParams] = useSearchParams();
  const [isHighlighted, setIsHighlighted] = useState(false);
  const [notFoundMessage, setNotFoundMessage] = useState<string | null>(null);
  const highlightTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const hasProcessedRef = useRef(false);

  const focusType = (searchParams.get('focusType') as FocusType) || null;
  const focusIdParam = searchParams.get('focusId');
  const focusId = focusIdParam ? parseInt(focusIdParam, 10) : null;

  useEffect(() => {
    if (focusType && focusId && !hasProcessedRef.current) {
      setIsHighlighted(true);
      hasProcessedRef.current = true;

      highlightTimeoutRef.current = setTimeout(() => {
        setIsHighlighted(false);
      }, HIGHLIGHT_DURATION);
    }

    return () => {
      if (highlightTimeoutRef.current) {
        clearTimeout(highlightTimeoutRef.current);
      }
    };
  }, [focusType, focusId]);

  const getItemHighlightClass = useCallback(
    (itemId: number, itemType: FocusType): string => {
      if (isHighlighted && focusId === itemId && focusType === itemType) {
        return HIGHLIGHT_CLASS;
      }
      return '';
    },
    [isHighlighted, focusId, focusType]
  );

  const scrollToItem = useCallback((element: HTMLElement | null) => {
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, []);

  const markItemFound = useCallback(() => {
    setNotFoundMessage(null);
  }, []);

  const markItemNotFound = useCallback((message?: string) => {
    setNotFoundMessage(message || 'Focused item not found in current view.');
    setIsHighlighted(false);
  }, []);

  const clearFocus = useCallback(() => {
    setSearchParams(
      params => {
        const newParams = new URLSearchParams(params);
        newParams.delete('focusType');
        newParams.delete('focusId');
        return newParams;
      },
      { replace: true }
    );
    setIsHighlighted(false);
    setNotFoundMessage(null);
    hasProcessedRef.current = false;
  }, [setSearchParams]);

  return {
    focusState: {
      focusType,
      focusId,
      isHighlighted,
      notFoundMessage
    },
    getItemHighlightClass,
    markItemFound,
    markItemNotFound,
    scrollToItem,
    clearFocus
  };
}

export default useFocusHighlight;

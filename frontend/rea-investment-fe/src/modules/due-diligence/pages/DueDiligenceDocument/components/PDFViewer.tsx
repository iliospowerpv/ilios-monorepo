import React, { useCallback, useMemo, useRef } from 'react';
import { Viewer, Worker } from '@react-pdf-viewer/core';
import { pageNavigationPlugin } from '@react-pdf-viewer/page-navigation';
import { searchPlugin, Match } from '@react-pdf-viewer/search';
import { highlightPlugin } from '@react-pdf-viewer/highlight';
import '@react-pdf-viewer/core/lib/styles/index.css';
import '@react-pdf-viewer/page-navigation/lib/styles/index.css';
import '@react-pdf-viewer/search/lib/styles/index.css';
import '@react-pdf-viewer/highlight/lib/styles/index.css';
import Box from '@mui/material/Box';

interface PDFViewerProps {
  fileUrl: string;
  onReady?: () => void;
}

export interface PDFViewerRef {
  jumpToPage: (page: number) => void;
  searchAndHighlight: (text: string) => void;
}

const WorkerWrapper = Worker as React.ComponentType<{ workerUrl: string; children: React.ReactNode }>;
const ViewerWrapper = Viewer as React.ComponentType<{
  fileUrl: string;
  plugins: unknown[];
  onDocumentLoad?: () => void;
}>;

const PDFViewerComponent = React.forwardRef<PDFViewerRef, PDFViewerProps>((props, ref) => {
  const { fileUrl, onReady } = props;

  const pageNavigationPluginInstance = useMemo(() => pageNavigationPlugin(), []);
  const { jumpToPage: navigateToPage } = pageNavigationPluginInstance;

  const searchPluginInstance = useMemo(() => searchPlugin(), []);
  const { highlight, clearHighlights, jumpToMatch } = searchPluginInstance;

  const highlightPluginInstance = useMemo(() => highlightPlugin(), []);

  const navigateToPageRef = useRef(navigateToPage);
  navigateToPageRef.current = navigateToPage;

  const highlightRef = useRef(highlight);
  highlightRef.current = highlight;

  const clearHighlightsRef = useRef(clearHighlights);
  clearHighlightsRef.current = clearHighlights;

  const jumpToMatchRef = useRef(jumpToMatch);
  jumpToMatchRef.current = jumpToMatch;

  const jumpToPage = useCallback((page: number) => {
    navigateToPageRef.current(page - 1);
  }, []);

  const searchAndHighlight = useCallback((text: string) => {
    if (!text || text.trim().length === 0) return;
    clearHighlightsRef.current();
    const searchText = text.length > 50 ? text.substring(0, 50) : text;
    highlightRef
      .current({
        keyword: searchText,
        matchCase: false
      })
      .then((matches: Match[]) => {
        if (matches.length > 0) {
          jumpToMatchRef.current(0);
        }
      });
  }, []);

  React.useImperativeHandle(ref, () => ({
    jumpToPage,
    searchAndHighlight
  }));

  return (
    <Box sx={{ height: '100%', width: '100%', overflow: 'hidden' }}>
      <WorkerWrapper workerUrl="https://unpkg.com/pdfjs-dist@3.11.174/build/pdf.worker.min.js">
        <ViewerWrapper
          fileUrl={fileUrl}
          plugins={[pageNavigationPluginInstance, searchPluginInstance, highlightPluginInstance]}
          onDocumentLoad={() => onReady?.()}
        />
      </WorkerWrapper>
    </Box>
  );
});

PDFViewerComponent.displayName = 'PDFViewer';

export default PDFViewerComponent;

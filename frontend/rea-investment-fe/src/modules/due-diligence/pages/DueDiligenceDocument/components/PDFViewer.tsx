import React, { useEffect, useRef, useCallback } from 'react';
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

const PDFViewerComponent = React.forwardRef<PDFViewerRef, PDFViewerProps>((props, ref) => {
  const { fileUrl, onReady } = props;

  const pageNavigationPluginInstance = pageNavigationPlugin();
  const { jumpToPage: navigateToPage } = pageNavigationPluginInstance;

  const searchPluginInstance = searchPlugin();
  const { highlight, clearHighlights, jumpToMatch } = searchPluginInstance;

  const highlightPluginInstance = highlightPlugin();

  const jumpToPage = useCallback(
    (page: number) => {
      navigateToPage(page - 1);
    },
    [navigateToPage]
  );

  const searchAndHighlight = useCallback(
    (text: string) => {
      if (!text || text.trim().length === 0) return;
      clearHighlights();
      const searchText = text.length > 50 ? text.substring(0, 50) : text;
      highlight({
        keyword: searchText,
        matchCase: false
      }).then((matches: Match[]) => {
        if (matches.length > 0) {
          jumpToMatch(0);
        }
      });
    },
    [highlight, clearHighlights, jumpToMatch]
  );

  React.useImperativeHandle(
    ref,
    () => ({
      jumpToPage,
      searchAndHighlight
    }),
    [jumpToPage, searchAndHighlight]
  );

  return (
    <Box sx={{ height: '100%', width: '100%', overflow: 'hidden' }}>
      <Worker workerUrl="https://unpkg.com/pdfjs-dist@3.11.174/build/pdf.worker.min.js">
        <Viewer
          fileUrl={fileUrl}
          plugins={[pageNavigationPluginInstance, searchPluginInstance, highlightPluginInstance]}
          onDocumentLoad={() => onReady?.()}
        />
      </Worker>
    </Box>
  );
});

PDFViewerComponent.displayName = 'PDFViewer';

export default PDFViewerComponent;

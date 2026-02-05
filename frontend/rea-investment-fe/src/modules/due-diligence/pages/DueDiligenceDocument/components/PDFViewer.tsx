import React, { useEffect, useState, useCallback, useMemo } from 'react';
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
  targetPage?: number;
  targetSearchText?: string;
  navigationTrigger?: number;
  onReady?: () => void;
}

export interface PDFViewerRef {
  jumpToPage: (page: number) => void;
  searchAndHighlight: (text: string) => void;
}

const WorkerWrapper = Worker as React.ComponentType<{
  workerUrl: string;
  children: React.ReactNode;
}>;
const ViewerWrapper = Viewer as React.ComponentType<{
  fileUrl: string;
  plugins: unknown[];
  initialPage?: number;
  onDocumentLoad?: () => void;
}>;

const PDFViewerComponent: React.FC<PDFViewerProps> = ({
  fileUrl,
  targetPage,
  targetSearchText,
  navigationTrigger,
  onReady
}) => {
  const [isDocumentReady, setIsDocumentReady] = useState(false);

  // Memoize plugin instances to ensure they are created once per component mount
  const pageNavigationPluginInstance = useMemo(() => pageNavigationPlugin(), []);
  const searchPluginInstance = useMemo(() => searchPlugin(), []);
  const highlightPluginInstance = useMemo(() => highlightPlugin(), []);

  // Extract methods from memoized plugin instances
  const { jumpToPage: navigateToPage } = pageNavigationPluginInstance;
  const { highlight, clearHighlights, jumpToMatch } = searchPluginInstance;

  const handleDocumentLoad = useCallback(() => {
    setIsDocumentReady(true);
    onReady?.();
  }, [onReady]);

  // Handle page navigation when targetPage changes
  useEffect(() => {
    if (isDocumentReady && targetPage && targetPage > 0) {
      const timer = setTimeout(() => {
        navigateToPage(targetPage - 1); // 0-indexed
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [isDocumentReady, targetPage, navigationTrigger, navigateToPage]);

  // Handle search when targetSearchText changes
  useEffect(() => {
    if (isDocumentReady && targetSearchText && targetSearchText.trim().length > 0) {
      const timer = setTimeout(() => {
        clearHighlights();
        const searchText = targetSearchText.length > 50 ? targetSearchText.substring(0, 50) : targetSearchText;
        highlight({
          keyword: searchText,
          matchCase: false
        }).then((matches: Match[]) => {
          if (matches.length > 0) {
            jumpToMatch(0);
          }
        });
      }, 200);
      return () => clearTimeout(timer);
    }
  }, [isDocumentReady, targetSearchText, navigationTrigger, highlight, clearHighlights, jumpToMatch]);

  const plugins = useMemo(
    () => [pageNavigationPluginInstance, searchPluginInstance, highlightPluginInstance],
    [pageNavigationPluginInstance, searchPluginInstance, highlightPluginInstance]
  );

  return (
    <Box sx={{ height: '100%', width: '100%', overflow: 'hidden' }}>
      <WorkerWrapper workerUrl="https://unpkg.com/pdfjs-dist@3.11.174/build/pdf.worker.min.js">
        <ViewerWrapper fileUrl={fileUrl} plugins={plugins} onDocumentLoad={handleDocumentLoad} />
      </WorkerWrapper>
    </Box>
  );
};

PDFViewerComponent.displayName = 'PDFViewer';

export default PDFViewerComponent;

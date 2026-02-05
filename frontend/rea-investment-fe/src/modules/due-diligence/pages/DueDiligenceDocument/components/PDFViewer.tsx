import React from 'react';
import { Viewer, Worker } from '@react-pdf-viewer/core';
import { pageNavigationPlugin, PageNavigationPlugin } from '@react-pdf-viewer/page-navigation';
import { searchPlugin, SearchPlugin, Match } from '@react-pdf-viewer/search';
import { highlightPlugin, HighlightPlugin } from '@react-pdf-viewer/highlight';
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

class PDFViewerComponent extends React.Component<PDFViewerProps> implements PDFViewerRef {
  private pageNavigationPluginInstance: PageNavigationPlugin;
  private searchPluginInstance: SearchPlugin;
  private highlightPluginInstance: HighlightPlugin;

  constructor(props: PDFViewerProps) {
    super(props);
    this.pageNavigationPluginInstance = pageNavigationPlugin();
    this.searchPluginInstance = searchPlugin();
    this.highlightPluginInstance = highlightPlugin();
  }

  jumpToPage = (page: number): void => {
    const { jumpToPage: navigateToPage } = this.pageNavigationPluginInstance;
    navigateToPage(page - 1);
  };

  searchAndHighlight = (text: string): void => {
    if (!text || text.trim().length === 0) return;
    const { highlight, clearHighlights, jumpToMatch } = this.searchPluginInstance;
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
  };

  handleDocumentLoad = (): void => {
    this.props.onReady?.();
  };

  render(): React.ReactNode {
    const { fileUrl } = this.props;

    return (
      <Box sx={{ height: '100%', width: '100%', overflow: 'hidden' }}>
        <WorkerWrapper workerUrl="https://unpkg.com/pdfjs-dist@3.11.174/build/pdf.worker.min.js">
          <ViewerWrapper
            fileUrl={fileUrl}
            plugins={[this.pageNavigationPluginInstance, this.searchPluginInstance, this.highlightPluginInstance]}
            onDocumentLoad={this.handleDocumentLoad}
          />
        </WorkerWrapper>
      </Box>
    );
  }
}

export default PDFViewerComponent;

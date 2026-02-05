import React, { useEffect, useState, useCallback, useRef } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/esm/Page/AnnotationLayer.css';
import 'react-pdf/dist/esm/Page/TextLayer.css';
import Box from '@mui/material/Box';
import CircularProgress from '@mui/material/CircularProgress';
import Typography from '@mui/material/Typography';
import IconButton from '@mui/material/IconButton';
import TextField from '@mui/material/TextField';
import NavigateBeforeIcon from '@mui/icons-material/NavigateBefore';
import NavigateNextIcon from '@mui/icons-material/NavigateNext';

pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.js`;

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

const PDFViewerComponent: React.FC<PDFViewerProps> = ({
  fileUrl,
  targetPage,
  targetSearchText,
  navigationTrigger,
  onReady
}) => {
  const [numPages, setNumPages] = useState<number>(0);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const lastTriggerRef = useRef<number>(0);

  const onDocumentLoadSuccess = useCallback(
    ({ numPages: pages }: { numPages: number }) => {
      setNumPages(pages);
      setIsLoading(false);
      setError(null);
      onReady?.();
    },
    [onReady]
  );

  const onDocumentLoadError = useCallback((err: Error) => {
    setIsLoading(false);
    setError(err.message || 'Failed to load PDF');
  }, []);

  useEffect(() => {
    if (targetPage && targetPage > 0 && numPages > 0 && navigationTrigger !== lastTriggerRef.current) {
      lastTriggerRef.current = navigationTrigger || 0;
      const page = Math.min(targetPage, numPages);
      setCurrentPage(page);
      setTimeout(() => {
        containerRef.current?.scrollTo({ top: 0, behavior: 'smooth' });
      }, 100);
    }
  }, [targetPage, navigationTrigger, numPages]);

  useEffect(() => {
    if (targetSearchText && targetSearchText.trim().length > 0 && navigationTrigger !== lastTriggerRef.current) {
      lastTriggerRef.current = navigationTrigger || 0;
    }
  }, [targetSearchText, navigationTrigger]);

  const goToPreviousPage = useCallback(() => {
    setCurrentPage(prev => Math.max(1, prev - 1));
  }, []);

  const goToNextPage = useCallback(() => {
    setCurrentPage(prev => Math.min(numPages, prev + 1));
  }, [numPages]);

  const handlePageInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const value = parseInt(e.target.value, 10);
      if (!isNaN(value) && value >= 1 && value <= numPages) {
        setCurrentPage(value);
      }
    },
    [numPages]
  );

  if (error) {
    return (
      <Box
        sx={{
          height: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexDirection: 'column',
          gap: 2
        }}
      >
        <Typography color="error">Error loading PDF: {error}</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ height: '100%', width: '100%', display: 'flex', flexDirection: 'column' }}>
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 1,
          py: 1,
          borderBottom: '1px solid',
          borderColor: 'divider',
          bgcolor: 'background.paper'
        }}
      >
        <IconButton onClick={goToPreviousPage} disabled={currentPage <= 1} size="small">
          <NavigateBeforeIcon />
        </IconButton>
        <TextField
          size="small"
          value={currentPage}
          onChange={handlePageInput}
          sx={{ width: 60 }}
          inputProps={{ style: { textAlign: 'center' } }}
        />
        <Typography variant="body2">/ {numPages}</Typography>
        <IconButton onClick={goToNextPage} disabled={currentPage >= numPages} size="small">
          <NavigateNextIcon />
        </IconButton>
      </Box>
      <Box
        ref={containerRef}
        sx={{
          flex: 1,
          overflow: 'auto',
          display: 'flex',
          justifyContent: 'center',
          bgcolor: 'grey.100'
        }}
      >
        {isLoading && (
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', p: 4 }}>
            <CircularProgress />
          </Box>
        )}
        <Document file={fileUrl} onLoadSuccess={onDocumentLoadSuccess} onLoadError={onDocumentLoadError} loading={null}>
          <Page pageNumber={currentPage} renderTextLayer={true} renderAnnotationLayer={true} loading={null} />
        </Document>
      </Box>
    </Box>
  );
};

PDFViewerComponent.displayName = 'PDFViewer';

export default PDFViewerComponent;

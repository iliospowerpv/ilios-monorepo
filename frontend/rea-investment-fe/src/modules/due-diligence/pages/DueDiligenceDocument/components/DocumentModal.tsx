import React, { useEffect, useState, useCallback, useRef } from 'react';
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import DocViewer, { DocViewerRenderers } from '@cyntler/react-doc-viewer';
import { AxiosError } from 'axios';
import Box from '@mui/material/Box';
import DialogTitle from '@mui/material/DialogTitle';
import IconButton from '@mui/material/IconButton';
import CloseIcon from '@mui/icons-material/Close';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import Grid from '@mui/material/Grid';
import AccordionDetails from '@mui/material/AccordionDetails';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import Backdrop from '@mui/material/Backdrop';
import CircularProgress from '@mui/material/CircularProgress';
import Fade from '@mui/material/Fade';
import { ApiClient, FileItem } from '../../../../../api';
import {
  SubHeader,
  DocumentPreviewContainer,
  TermName,
  AIResponseContainer,
  AccordionStyled,
  AccordionSummaryStyled,
  DialogTitleStyled,
  DialogContentStyled,
  AIText,
  DocunentPreviewModal,
  DocunentPreviewModalContent,
  DocunentPreviewModalViewbox
} from './DocumentModal.styles';
import DocumentTermUserInputField, { DocumentTermUserInputFieldRef } from './DocumentTermUserInputField';
import DocumentPoisonPill from './DocumentPoisonPill';
import { BootstrapTooltip } from '../../../../../components/common/BootstrapTooltip/BootstrapTooltip';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNotify } from '../../../../../contexts/notifications/notifications';
import DocumentModalComments from './DocumentModalComments';
import {
  ParsingStatusBadge,
  ParseErrorMessage,
  TruncationWarning,
  ParsingMetadata
} from '../../../../../components/common/ParsingStatus';
import PDFViewer, { PDFViewerRef } from './PDFViewer';

dayjs.extend(utc);

interface DocumentModal {
  open: boolean;
  fileUrl: string;
  file: FileItem | null;
  documentId: number;
  siteId: number;
  boardId: number;
  onClose: () => void;
  taskId: number;
}

interface Comment {
  id: number;
  entity_id: number;
  text: string;
  created_at: string;
  updated_at: string;
  first_name: string;
  last_name: string;
}

interface FileParsingEvidence {
  page?: number | null;
  snippet?: string | null;
  anchor_text?: string | null;
}

interface CollapsibleDocumentTermRenderer {
  id: number | null;
  termName: string;
  aiValue: string | null;
  userValue: string | null;
  documentId: number;
  siteId: number;
  isPoisonPill: boolean;
  poisonPillDetails: string | null;
  legal_term: string | null;
  comments: Comment[] | null;
  boardId: number;
  fileId: number;
  taskId: number;
  evidence?: FileParsingEvidence | null;
  onViewInDocument?: (page: number, snippet?: string | null, anchorText?: string | null) => void;
}

const CollapsibleDocumentTermRenderer: React.FC<CollapsibleDocumentTermRenderer> = props => {
  const {
    id,
    termName,
    aiValue,
    userValue,
    documentId,
    siteId,
    isPoisonPill,
    poisonPillDetails,
    legal_term,
    comments,
    boardId,
    fileId,
    taskId,
    evidence,
    onViewInDocument
  } = props;
  const userInputFormRef = React.useRef<DocumentTermUserInputFieldRef | null>(null);
  const [expanded, setExpanded] = React.useState<boolean>(true);

  const copyToTextField = (text: string | null) => {
    if (!text) return;
    const textToPopulate = text.length > 2000 ? text.substring(0, 2000) : text;
    userInputFormRef.current?.setValue && userInputFormRef.current?.setValue(textToPopulate);
  };

  const hasEvidence = evidence && evidence.page != null;

  return (
    <AccordionStyled expanded={expanded} onChange={() => setExpanded(prevExpanded => !prevExpanded)}>
      <AccordionSummaryStyled expandIcon={<ExpandMoreIcon />}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, width: '100%' }}>
          <TermName sx={{ flex: 1 }}>{termName}</TermName>
          {hasEvidence && (
            <BootstrapTooltip
              title={
                evidence.snippet
                  ? `"${evidence.snippet.substring(0, 100)}${evidence.snippet.length > 100 ? '...' : ''}"`
                  : `Found on page ${evidence.page}`
              }
              placement="top"
            >
              <Button
                size="small"
                variant="text"
                onClick={e => {
                  e.stopPropagation();
                  if (onViewInDocument && evidence.page) {
                    onViewInDocument(evidence.page, evidence.snippet, evidence.anchor_text);
                  }
                }}
                sx={{
                  minWidth: 'auto',
                  fontSize: '12px',
                  color: 'primary.main',
                  textTransform: 'none',
                  padding: '2px 8px'
                }}
              >
                Page {evidence.page}
              </Button>
            </BootstrapTooltip>
          )}
        </Box>
      </AccordionSummaryStyled>
      <AccordionDetails sx={{ display: 'flex', padding: '8px 0 16px 16px' }}>
        <Box flex="1">
          <AIResponseContainer>
            <Typography variant="h6" fontSize="16px" fontWeight="600" py="8px">
              Legal Terms
            </Typography>
            <AIText bgColor>{legal_term}</AIText>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <Typography variant="h6" fontSize="16px" fontWeight="600" py="8px">
                Value
                <BootstrapTooltip title="Copy" placement="top">
                  <IconButton
                    sx={{
                      position: 'absolute',
                      right: '-30px',
                      marginTop: '25px !important',
                      padding: '8px',
                      margin: 0
                    }}
                    onClick={() => copyToTextField(aiValue)}
                  >
                    <ContentCopyIcon sx={{ fontSize: '20px', color: theme => theme.palette.text.secondary }} />
                  </IconButton>
                </BootstrapTooltip>
              </Typography>
            </Box>
            <AIText>{aiValue}</AIText>
            <DocumentPoisonPill isPoisonPill={isPoisonPill} title={isPoisonPill ? poisonPillDetails : ''} />
          </AIResponseContainer>
          <DocumentTermUserInputField
            ref={userInputFormRef}
            documentId={documentId}
            siteId={siteId}
            termKey={termName}
            text={userValue}
          />
          <DocumentModalComments
            termId={id}
            termKey={termName}
            documentId={documentId}
            siteId={siteId}
            comments={comments}
            boardId={boardId}
            fileId={fileId}
            taskId={taskId}
          />
        </Box>
        <Box sx={{ padding: '4px', width: '36px' }}></Box>
      </AccordionDetails>
    </AccordionStyled>
  );
};

const DocumentModal: React.FC<DocumentModal> = props => {
  const { open, file, fileUrl, onClose, documentId, siteId, boardId, taskId } = props;
  const fileId = file?.id ?? -1;
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentRunId, setCurrentRunId] = useState<number | undefined>();
  const [currentCorrelationId, setCurrentCorrelationId] = useState<string | undefined>();
  const queryClient = useQueryClient();
  const notify = useNotify();

  const {
    data: fileTermKeysData,
    isLoading: isLoadingFileTermKeysData,
    error: fileTermKeysDataLoadingError
  } = useQuery({
    queryFn: () => ApiClient.dueDiligence.getFileParsingResult({ siteId, documentId, fileId }),
    queryKey: ['document-terms', { siteId, documentId, fileId }],
    enabled: open && fileId !== -1,
    retry: 1
  });

  const { mutateAsync: startParsing, isPending: isStartingParse } = useMutation({
    mutationFn: ({ id, forceReprocess }: { id: number; forceReprocess: boolean }) =>
      ApiClient.dueDiligence.documentStartParsing(id, siteId, documentId, forceReprocess),
    onSuccess: response => {
      setCurrentRunId(response.run_id);
      setCurrentCorrelationId(response.correlation_id);
      notify(`Parsing started. This may take a few minutes.`);
      setIsProcessing(true);
    },
    onError: () => {
      notify('Something went wrong, try again later.');
    }
  });

  const { data: documentStatus } = useQuery({
    queryFn: async () => {
      return ApiClient.dueDiligence.documentParsingStatus(fileId, siteId, documentId);
    },
    queryKey: ['document-status', { siteId, documentId, fileId }],
    enabled: open && fileId !== -1,
    refetchInterval: isProcessing ? 5000 : false
  });

  const handleStartParsing = useCallback(
    async (fileIdToProcess: number, forceReprocess = false) => {
      try {
        await startParsing({ id: fileIdToProcess, forceReprocess });
      } catch (e) {
        console.log(e);
      }
    },
    [startParsing]
  );

  const handleReprocess = useCallback(() => {
    if (fileId !== -1) {
      handleStartParsing(fileId, true);
    }
  }, [fileId, handleStartParsing]);

  useEffect(() => {
    if (!documentStatus) return;

    const status = documentStatus.status?.toLowerCase().replace(/\s+/g, '_');

    if (documentStatus.run_id) {
      setCurrentRunId(documentStatus.run_id);
    }
    if (documentStatus.correlation_id) {
      setCurrentCorrelationId(documentStatus.correlation_id);
    }

    if (status === 'processing_failed' || status === 'failed') {
      setIsProcessing(false);
    } else if (status === 'completed' || status === 'succeeded') {
      if (isProcessing) {
        notify('Processing completed');
        queryClient.invalidateQueries({ queryKey: ['document-terms'] });
      }
      setIsProcessing(false);
    } else if (status === 'processing' || status === 'queued') {
      setIsProcessing(true);
    } else {
      setIsProcessing(false);
    }
  }, [documentStatus, isProcessing, notify, queryClient]);

  const parsingStatus = documentStatus?.status?.toLowerCase().replace(/\s+/g, '_') || 'not_started';
  const hasFailed = parsingStatus === 'processing_failed' || parsingStatus === 'failed';
  const hasCompleted = parsingStatus === 'completed' || parsingStatus === 'succeeded';

  React.useEffect(() => {
    if (fileTermKeysDataLoadingError) {
      notify(
        fileTermKeysDataLoadingError instanceof AxiosError
          ? fileTermKeysDataLoadingError.response?.data?.message || fileTermKeysDataLoadingError.message
          : fileTermKeysDataLoadingError.message
      );
    }
  }, [notify, fileTermKeysDataLoadingError]);

  const pdfViewerRef = useRef<PDFViewerRef>(null);

  const getFileType = (filename: string): string | undefined => {
    const ext = filename.split('.').pop()?.toLowerCase();
    if (ext === 'pdf') return 'pdf';
    if (ext === 'docx') return 'docx';
    if (ext === 'doc') return 'doc';
    if (ext === 'png') return 'png';
    if (ext === 'jpg' || ext === 'jpeg') return 'jpg';
    return undefined;
  };

  const isPDF = file && getFileType(file.filename) === 'pdf';

  const handleViewInDocument = useCallback(
    (page: number, snippet?: string | null, anchorText?: string | null) => {
      if (!isPDF) {
        notify('Jump-to-page is available for PDFs only');
        return;
      }
      if (pdfViewerRef.current) {
        pdfViewerRef.current.jumpToPage(page);
        const searchText = anchorText || snippet;
        if (searchText) {
          setTimeout(() => {
            pdfViewerRef.current?.searchAndHighlight(searchText);
          }, 300);
        }
        notify(`Jumped to page ${page}`);
      }
    },
    [isPDF, notify]
  );

  const FileRenderer = React.useMemo(() => {
    if (!file || !fileUrl) return null;

    if (isPDF) {
      return <PDFViewer ref={pdfViewerRef} fileUrl={fileUrl} />;
    }

    return (
      <DocViewer
        pluginRenderers={DocViewerRenderers}
        documents={[{ uri: fileUrl, fileType: getFileType(file.filename) }]}
        style={{ width: '100%', height: '100%' }}
        config={{
          header: {
            disableHeader: true,
            disableFileName: true
          },
          pdfVerticalScrollByDefault: true
        }}
      />
    );
  }, [file, fileUrl, isPDF]);

  if (!file || !fileUrl) return null;

  return (
    <DocunentPreviewModal
      className="DocumentPreviewModal-root"
      onClose={onClose}
      aria-labelledby="customized-dialog-title"
      open={open}
      disableEnforceFocus
      disableAutoFocus
      disableRestoreFocus
    >
      <Fade in={open}>
        <DocunentPreviewModalViewbox className="DocumentPreviewModal-viewbox">
          <DocunentPreviewModalContent className="DocumentPreviewModal-content">
            <DialogTitleStyled id="customized-dialog-title">
              <BootstrapTooltip title={file.filename}>
                <Typography sx={{ marginRight: '20px' }} variant="h6" noWrap>
                  {file.filename}
                </Typography>
              </BootstrapTooltip>
              <Typography variant="body2" sx={{ marginTop: '5px' }}>
                Uploaded by {file.author}, {dayjs.utc(file.created_at).local().format('lll')}
              </Typography>
              <IconButton
                aria-label="close"
                onClick={onClose}
                sx={{
                  position: 'absolute',
                  right: 8,
                  top: 8,
                  color: theme => theme.palette.secondary.main
                }}
              >
                <CloseIcon />
              </IconButton>
            </DialogTitleStyled>
            <DialogContentStyled dividers>
              {!file.filename.endsWith('.pdf') && <SubHeader />}
              {document && (
                <Box height="100%" maxWidth="2000px" marginX="auto" position="relative" padding="70px 16px 0px">
                  <Grid container spacing={2} height="100%">
                    <Grid item sm={6} md={7} height="100%">
                      <DocumentPreviewContainer>
                        <Box
                          sx={{ position: 'absolute', right: '16px', top: '8px', zIndex: 10, display: 'flex', gap: 1 }}
                        >
                          <Button
                            variant="contained"
                            sx={{
                              color: 'white',
                              background: 'linear-gradient(245.75deg, #456CF3 7.17%, #8D4BE9 89.9%)',
                              ['&:hover']: { background: 'linear-gradient(245.75deg, #456CF3 7.17%, #8D4BE9 89.9%)' },
                              '&.Mui-disabled': {
                                color: 'rgba(0, 0, 0, 0.26)',
                                background: 'rgba(0, 0, 0, 0.12)'
                              }
                            }}
                            onClick={() => handleStartParsing(file.id, hasCompleted || hasFailed)}
                            disabled={isProcessing || isStartingParse}
                            startIcon={
                              isProcessing || isStartingParse ? <CircularProgress color="inherit" size={20} /> : null
                            }
                          >
                            {hasCompleted || hasFailed ? 'Reprocess' : 'Parse with AI'}
                          </Button>
                        </Box>
                        {FileRenderer}
                      </DocumentPreviewContainer>
                    </Grid>
                    <Grid item sm={6} md={5} height="100%">
                      <DialogTitle
                        sx={{
                          bgcolor: 'primary.main',
                          color: 'secondary.main',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between'
                        }}
                        id="document-dialog-title"
                      >
                        <span>Document Details</span>
                        {documentStatus && <ParsingStatusBadge status={parsingStatus} />}
                      </DialogTitle>
                      <Box
                        sx={{
                          bgcolor: 'white',
                          padding: '16px',
                          height: 'calc(100% - 64px)',
                          overflowY: 'auto',
                          position: 'relative'
                        }}
                      >
                        {hasFailed && (
                          <ParseErrorMessage errorMessage={documentStatus?.error_message} onRetry={handleReprocess} />
                        )}
                        {hasCompleted && documentStatus?.was_truncated && (
                          <TruncationWarning
                            wasTruncated={documentStatus.was_truncated}
                            truncatedCharCount={documentStatus.truncated_char_count}
                            charCount={documentStatus.char_count}
                          />
                        )}
                        {hasCompleted && (
                          <ParsingMetadata
                            charCount={documentStatus?.char_count}
                            wordCount={documentStatus?.word_count}
                            pageCount={documentStatus?.page_count}
                            correlationId={currentCorrelationId}
                            runId={currentRunId}
                            showDebugInfo={true}
                          />
                        )}
                        {fileTermKeysData &&
                          fileTermKeysData.keys.map(
                            ({
                              id,
                              name,
                              value,
                              ai_value,
                              is_poison_pill,
                              poison_pill_detailed,
                              legal_term,
                              comments,
                              evidence
                            }) => (
                              <CollapsibleDocumentTermRenderer
                                key={name}
                                id={id}
                                termName={name}
                                aiValue={ai_value}
                                userValue={value}
                                documentId={documentId}
                                siteId={siteId}
                                isPoisonPill={is_poison_pill}
                                poisonPillDetails={poison_pill_detailed}
                                legal_term={legal_term}
                                comments={comments}
                                boardId={boardId}
                                fileId={fileId}
                                taskId={taskId}
                                evidence={evidence}
                                onViewInDocument={handleViewInDocument}
                              />
                            )
                          )}
                        <Backdrop
                          sx={{ color: '#1D1D1D', position: 'absolute', bgcolor: 'rgba(250, 250, 250, 0.5)' }}
                          open={isLoadingFileTermKeysData}
                        >
                          <CircularProgress color="inherit" />
                        </Backdrop>
                      </Box>
                    </Grid>
                  </Grid>
                </Box>
              )}
            </DialogContentStyled>
          </DocunentPreviewModalContent>
        </DocunentPreviewModalViewbox>
      </Fade>
    </DocunentPreviewModal>
  );
};

export default DocumentModal;
